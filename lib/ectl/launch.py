from __future__ import print_function
import copy
import os
import subprocess
import re
from ectl import pathutil,rundeck,rundir,xhash,launchers
import sys
import ectl
import ectl.util
import shutil
from ectl import iso8601
import datetime
import netCDF4
import collections

def setup_parser(subparser):
    subparser.add_argument('run', nargs='?', default='.',
        help='Directory of run to give execution command')
    subparser.add_argument('--timespan', '-ts', action='store', dest='timespan',
        help='[iso8601],[iso8601],[iso8601] (start,end) Timespan to run it for')
    subparser.add_argument('--force', '-f', action='store_true', dest='force',
        default=False,
        help='Overwrite run without asking (on start)')
    subparser.add_argument('-l', '--launcher', action='store', dest='launcher',
        help='How to run the program: mpi, slurm, slurm-debug')

    # -------- Arguments for SOME launchers
    subparser.add_argument('-np', '--ntasks', '-n', action='store', dest='np',
        help='Number of MPI jobs')
    subparser.add_argument('-t', '--time', action='store', dest='time',
        help='Length of wall clock time to run (see sbatch): [mm|hh:mm:ss]')


    subparser.add_argument('--resume', '-r', action='store_true', dest='resume', default=False,
        help='Resume a run; do not look at rundeck.R, just resume same as last I file.')
# --------------------------------------------------------------------
def parse_date(str):
    if len(str) == 0:
        return None
    return iso8601.parse_date(str)


# ---------------------------------------------------
def rsf_type(rsf):
    """Determines whether a restart file is a .rsf or fort.X.nc file."""

    with netCDF4.Dataset(rsf, 'r') as nc:
        if 'last_itime' not in nc.variables:
            raise ValueError('File {} does not seem to be a checkpoint or restart file'.format(rsf))
        if 'aij' in nc.variables:
            return START_CHECKPOINT
        else:
            return START_RSF

# ---------------------------------------------------
# ------------------------------------------------------
def rd_set_ts(rd, cold_start, start_ts, end_ts):
    """Modifies the rundeck with start and end times."""

    if (not cold_start) and (start_ts is not None):
        raise ValueError('Cannot set a start timestamp in the middle of a run!')
    if start_ts is not None:
        rd.set(('INPUTZ', 'START_TIME'), datetime.datetime(*start_ts))
    if end_ts is not None:
        rd.set(('INPUTZ', 'END_TIME'), datetime.datetime(*end_ts))


def time_to_seconds(stime):
    """Converts the --time argument [mm|hh:mm:ss] to seconds (int)"""
    stimes = stime.split(':')
    if len(stimes) == 1:
        return int(stimes[0])*60
    if len(stimes) == 3:
        return int(stimes[0])*3600 + int(stimes[1])*60 + int(stimes[2])
    raise ValueError('Illegal time (should be [mm|hh:mm:ss]): {}'.format(stime))

def run(args, cmd):
    """Top-level that parses command line arguments

    cmd: 'start', 'run'
        User-level command calling this
    rsf:
        Name of restart file"""

    # Parse out timespan
    start_ts = None
    end_ts = None
    if args.timespan is not None:
        tss = [parse_date(sdate.strip()) for sdate in args.timespan.split(',')]
        if len(tss) == 1:
            start_ts = tss[0]
        elif len(tss) == 2:
            start_ts = tss[0]
            end_ts = tss[1]
        else:
            raise ValueError('Invalid timespan %s' % args.timespan)

    # ------ Parse Arguments

    # Launcher to use
    kwargs = dict()
    if hasattr(args, 'restart_file'):
        kwargs['restart_file'] = args.restart_file

    if args.resume:
        ectl.launch.launch(args.run, launcher=args.launcher,
            ntasks=args.np, time=args.time,
            keep_I=True, add_keepalive=False)
    else:
        launch(args.run, launcher=args.launcher, force=args.force,
            ntasks=args.np, time=args.time,
            rundeck_modifys=[lambda rd, cold_start: rd_set_ts(rd, cold_start, start_ts, end_ts)],
            cold_start=(cmd == 'start'), **kwargs)


# These are set to match corresponding ISTART values in ModelE
# See MODELE.f
START_COLD = 2        # Restart a run, no restart/checkpoint files
START_CHECKPOINT = 14  # Restart from a fort.X.nc file
START_RSF = 9         # Restart from an .rsf (AIC) file

LATEST = object()    # Token
COLD = object()

def launch(run, launcher=None, force=False, ntasks=None, time=None, rundeck_modifys=list(),
    cold_start=False, keep_I=False, restart_file=None, restart_date=None,
    synchronous=False, add_keepalive=True):
    """API call to start a ModelE execution.

    run: str
        Run directory to launch.
    launcher: str
        Name of launcher to use (default: $ETL_LAUNCHER env var)
    force: bool
        On restart, overwrite stopped runs without asking user?
    ntasks: int
        Number of MPI nodes to run
    time: str
        Length of time to run (SLURM format specifier for now)
    rundeck_modifys: [fn(rd, cold_start)]  #, str cmd, rundir.Status status)]
        These modifications are applied to in-memory rundeck when writing
        the I file.
    cmd: 'start' or 'run'
        Helps modele-control determine user behavior
    cold_start: bool
        Direction from the user that a cold start is desired.
    keep_I: bool
        When auto-restarting using the keepalive feature, take the rundeck
        parameters from the last I file
    restart_file:
        Restart or checkpoint file to start from.
    synchronous:
        Block until ModelE is done running.  Usually good only for small tests.
    """

    if restart_file is not None and restart_date is not None:
        raise ValueError('Cannot simultaneously set restart_file and restart_date.')
    if launcher is None:
        launcher = os.environ.get('ECTL_LAUNCHER', None)
    if launcher is None:
        raise ValueError('No launcher specified.  Please use --launcher command line option, or set the ECTL_LAUNCHER environment variable.  Valid values are mpi, slurm and slurm-debug.')

    # Obtain restart_file from restart_date
    if restart_date is not None:
        raise NotImplementedError('Obtain restart_file from restart_date')

    # Check arguments
    if restart_file is not None:
        if not os.path.exists(restart_file):
            raise ValueError('Specified restart file does not exist: %s' % restart_file)
        if cold_start:
            raise ValueError('Cannot specify a cold start and rsf file together.')

    paths = rundir.FollowLinks(run)
    status = rundir.Status(paths.run)
    if (status.status == launchers.NONE):
        raise ValueError('Run does not exist, cannot run: {0}\n'.format(run))
    if (status.status == launchers.RUNNING):
        raise ValueError('Run is already running: {0}\n'.format(run))

    # --------- Determine start type (start_type) and restart file (rsf)

    # Determine status of fort files, and their max
    forts = rundir.forts_status(paths.run)

    # Don't put up with any corrupt fort files!
    ncorrupt = sum([x.status==rundir.RSF_CORRUPT for x in forts])
    if ncorrupt > 0:
        print('Corrupt fort.X.nc files detected, cannot launch ModelE:')
        for fort in [x for x in forts if x.status==rundir.RSF_CORRUPT]:
            print('   {}'.format(fort.rsf))
        raise ValueError('Corrupt fort.X.nc file(s) detected.')


    good_forts = [x for x in forts if x.status==rundir.RSF_GOOD]
    missing_forts = [x for x in forts if x.status==rundir.RSF_MISSING]
    ngood = len(good_forts)
    nmissing = len(missing_forts)


    kdisk_preferred0 = None    # First fort.X.nc file to write, if both already exist
    if cold_start:
        # User requested a cold start
        # Always write fort.1.nc first on cold start; be predictable
        start_type = START_COLD
        kdisk=1
        rsf = None
    elif restart_file is None:
        # User requested a warm start but did not give a rsf file.

        if ngood == 0:
            # No fort files anywhere, do a cold start.
            start_type = START_COLD
            kdisk=1
            rsf = None
        else:
            # Print out existing fort files
            print('Choosing from fort files:')
            for f in good_forts:
                print('  {}: itime={}'.format(f.rsf, f.itime))

            # Find most recent fort file
            max_fort = max(good_forts, key=lambda x : x.itime)
            rsf = max_fort.rsf
            start_type = START_CHECKPOINT

            # The first checkpoint file should be the one we started from.    
            # See note in MODELE.f:
            # ! Keep KDISK after reading from the later restart file, so that
            # ! the same file is overwritten first; in case of trouble,
            # ! the earlier restart file will still be available
            other_fort = forts[1-(max_fort.kdisk-1)]
            if other_fort.status == rundir.RSF_MISSING:
                kdisk = other_fort.kdisk
            else:
                kdisk = max_fort.kdisk
    else:
        # User specified a restart_file.

        # See what kind it is
        rsf = os.path.abspath(restart_file)
        start_type = rsf_type(rsf)

        # Decide on which checkpoint file to write first in the run.
        if ngood == len(forts):
            # We have to overwrite a file; write to the oldest
            min_fort = min(good_forts, key=lambda x : x.itime)
        else:
            # At least one fort file does not exist; write to that slot.
            min_fort = min(missing_forts, key=lambda x : x.kdisk)
        print('good_forts', good_forts)
        kdisk = min_fort.kdisk

    # Make sure the rsf file exists and seems OK
    # Print status
    if start_type == START_COLD:
        if (status.status >= launchers.STOPPED) and (not force):
            if not ectl.util.query_yes_no('Run is STOPPED; do you wish to overwrite and restart?', default='no'):
                sys.exit(-1)

        print('***** Cold Start')
        print('First checkpoint file will be fort.{}.nc'.format(kdisk))
    else:
        print('***** Warm Start')
        with netCDF4.Dataset(rsf, 'r') as nc:
            itime = nc.variables['itime'][:]
            print('Restarting from {} (itime={}).'.format(rsf, itime))
        print('First checkpoint file will be fort.{}.nc'.format(kdisk))

    # ---------------------------------

    modelexe = os.path.join(paths.run, 'pkg', 'bin', 'modelexe')
    _launcher = rundir.new_launcher(paths.run, launcher)

    # -------- Determine log file(s)
    # Get non-symlinked log direcotry
    log_dir = pathutil.make_vdir(os.path.join(paths.run, 'log'))

    # ------- Load the rundeck and rewrite the I file (and symlinks)
    try:
        if keep_I:
            print('****** Reading old I file')
            rd = rundeck.load_I(os.path.join(paths.run, 'I'))
            pnames = sorted([repr(x) for x,_ in rd.params.items()])
        else:
            print('****** Reading rundeck.R')
            rd = rundeck.load(os.path.join(paths.run, 'rundeck', 'rundeck.R'), modele_root=paths.src)
            rd.resolve(file_path=ectl.rundeck.default_file_path, download=True,
                download_dir=ectl.rundeck.default_file_path[0])

            # Copy stuff from INPUTZ_cold to INPUTZ if this is a cold start.
            # This eliminates the need for the '-cold-restart' flag to modelexe
            # It replaces the following lines in MODELE.f:
            #          READ (iu_IFILE,NML=INPUTZ,ERR=900)
            #          if (coldRestart) READ (iu_IFILE,NML=INPUTZ_cold,ERR=900)
            for pname,param in list(rd.params.items()):
                if not isinstance(pname, tuple):
                    continue
                if pname[0] == 'INPUTZ_cold':
                    if start_type == START_COLD:
                        new_pname = ('INPUTZ', pname[1])
                        param.pname = new_pname
                        rd.params[new_pname] = param
                    del rd.params[pname]

        # Set ISTART and restart file in I file
        rd.set(('INPUTZ', 'ISTART'), str(start_type))
        if start_type == START_RSF:
            rd.set('aic', rsf, type=rundeck.FILE)
        elif start_type == START_CHECKPOINT:
            rd.set('fort.4.nc', rsf, type=rundeck.FILE)

        rd.set('kdisk', str(kdisk))

        # Make additional modifications to the rundeck
        for rd_modify in rundeck_modifys:
            rd_modify(rd, start_type == START_COLD)
        
        rundir.make_rundir(rd, paths.run, idir=log_dir)

    except IOError:
        print('Warning: Cannot load rundeck.R.  NOT rewriting I file')

    # -------- Construct the main command line
    mpi_cmd = ['mpirun', '-timestamp-output']
    mpi_cmd.append('-output-filename')
    mpi_cmd.append(os.path.join(log_dir, 'q'))

    # ------- Delete timestamp.txt
    try:
        os.remove(os.path.join(paths.run, 'timestep.txt'))
    except:
        pass


    # ------ Add modele to the command
    modele_cmd = [modelexe, '-i', 'I']
    if time is not None:
        time_s = time_to_seconds(time)
        time_margin_s = 3*60
        net_time_s = max(120, time_s - time_margin_s)
        modele_cmd = modele_cmd + ['--time', str(net_time_s)]

    # ------- Run it!
    _launcher(mpi_cmd, modele_cmd, np=ntasks, time=time, synchronous=synchronous)
    if not synchronous:
        _launcher.wait()
        print_status(paths.run)

    # ------- Add to keepalive
    if add_keepalive:
        ectl.keepalive.add(paths.run)

# --------------------------------------------------------------------
def print_status(run,status=None):
    """run:
        Run directory
    status:
        rundir.Status(run)"""
    if status is None:
        status = rundir.Status(run)

    if (status.status == launchers.NONE):
        sys.stderr.write('Error: No valid run in directory %s\n' % run)
        sys.exit(-1)

    # Top-line status
    print('============================ {0}'.format(os.path.split(run)[1]))
    print('status:  {0}'.format(status.sstatus))

    # Run configuration
    paths = rundir.FollowLinks(run)
    paths.dump()

    # Launch.txt
    if status.launch_list is not None:
        for key,val in status.launch_list:
            print('{0} = {1}'.format(key, val))

    # Do launcher-specific stuff to look at the actual processes running.
    launcher = status.new_launcher()
    if launcher is not None:
        launcher.ps(status.launch_txt, sys.stdout)
