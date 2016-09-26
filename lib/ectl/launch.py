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

def setup_parser(subparser):
    subparser.add_argument('run', nargs='?', default='.',
        help='Directory of run to give execution command')
    subparser.add_argument('--timespan', '-ts', action='store', dest='timespan',
        help='[iso8601],[iso8601],[iso8601] (start,end) Timespan to run it for')
    subparser.add_argument('--force', '-f', action='store_true', dest='force',
        default=False,
        help='Overwrite run without asking (on start)')
    subparser.add_argument('-l', '--launcher', action='store', dest='launcher',
        help='How to run the program')

    # -------- Arguments for SOME launchers
    subparser.add_argument('-np', '--ntasks', '-n', action='store', dest='np',
        help='Number of MPI jobs')
    subparser.add_argument('-t', '--time', action='store', dest='time',
        help='Length of wall clock time to run (see sbatch): [mm|hh:mm:ss]')
# --------------------------------------------------------------------
def parse_date(str):
    if len(str) == 0:
        return None
    return iso8601.parse_date(str)

def remake_dir(dir):
    """Creates a directory, renaming the old one to <dir>.v???"""
    if os.path.exists(dir):
        print('EXISTS')
        # Move to a '.vXX' name
        root,leaf = os.path.split(dir)
        dirRE = re.compile(leaf + r'\.v(\d+)')
        max_v = 0
        for fname in os.listdir(root):
            match = dirRE.match(fname)
            if match is not None:
                v = int(match.group(1))
                if v > max_v:
                    max_v = v
        next_fname = os.path.join(root, '%s.%02d' % (leaf, max_v+1))
        print('next_fname', next_fname)
        os.rename(dir, next_fname)

    os.mkdir(dir)


def make_vdir(dir):
    """Creates a directory named <dir>XX, and symlinks <dir> to it."""

    # Find the next 'vXXX' name to use
    root,leaf = os.path.split(dir)
    dirRE = re.compile(leaf + r'(\d+)')
    max_v = 0
    for fname in os.listdir(root):
        match = dirRE.match(fname)
        if match is not None:
            v = int(match.group(1))
            max_v = max(max_v, v)
    next_fname = '%s%02d' % (leaf, max_v+1)
    os.mkdir(os.path.join(root, next_fname))

    # Create symlink log -> log.vXXX
    try:
        #shutil.rmtree(dir)
        os.remove(dir)
    except OSError:
        pass
    os.symlink(next_fname, dir)


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
def latest_rsf(rsfs, raise_missing=False):
    """Finds the checkpoint (fort.X.nc) file with the later timestamp.
    raise_missing:
        If set, raise an exception on a missing file."""

    max_itime = -1
    max_rsf = None
    for rsf in rsfs:
        print('rsf=', rsf)

        try:
            nc = netCDF4.Dataset(rsf, 'r')
        except:
            # File failed to open
            if raise_missing:
                raise
            else:
                continue

        # File is now open
        try:
            itime = nc.variables['itime'][:]
            if itime > max_itime:
                max_itime = itime
                max_rsf = rsf
        finally:
            nc.close()

    return max_rsf
# ------------------------------------------------------
def rd_set_ts(rd, cold_start, start_ts, end_ts):
    """Modifies the rundeck with start and end times."""

    if (not cold_start) and (start_ts is not None):
        raise ValueError('Cannot set a start timestamp in the middle of a run!')
    if start_ts is not None:
        rd.set(('INPUTZ', 'START_TIME'), datetime.datetime(*start_ts))
    if end_ts is not None:
        rd.set(('INPUTZ', 'END_TIME'), datetime.datetime(*end_ts))


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

    launch(args.run, launcher=args.launcher, force=args.force,
        ntasks=args.np, time=args.time,
        rundeck_modifys=[lambda rd, cold_start: rd_set_ts(rd, cold_start, start_ts, end_ts)],
        cold_start=(cmd == 'start'), **kwargs)


# These are set to match corresponding ISTART values in ModelE
# See MODELE.f
START_COLD = 2        # Restart a run, no restart/checkpoint files
START_CHECKPOINT = 14  # Restart from a fort.1.nc or fort.2.nc file
START_RSF = 9         # Restart from an .rsf (AIC) file

LATEST = object()    # Token
COLD = object()

def launch(run, launcher=None, force=False, ntasks=None, time=None, rundeck_modifys=list(),
    cold_start=False, restart_file=None,
    synchronous=False):
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
    restart_file:
        Restart or checkpoint file to start from.
    synchronous:
        Block until ModelE is done running.  Usually good only for small tests.
    """

    if launcher is None:
        launcher = os.environ.get('ECTL_LAUNCHER', None)
    if launcher is None:
        raise ValueError('No launcher specified.  Please use --launcher command line option, or set the ECTL_LAUNCHER environment variable.  Valid values are mpi, slurm and slurm-debug.')


    # Check arguments
    if restart_file is not None:
        if not os.path.exists(restart_file):
            raise ValueError('Specified restart file does not exist: %s' % restart_file)
        if cold_start:
            raise ValueError('Cannot specify a colde start and rsf file together.')

    paths = rundir.FollowLinks(run)
    status = rundir.Status(paths.run)
    if (status.status == launchers.NONE):
        raise ValueError('Run does not exist, cannot run: {0}\n'.format(run))
    if (status.status == launchers.RUNNING):
        raise ValueError('Run is already running: {0}\n'.format(run))

    # --------- Determine start type (start_type) and restart file (rsf)
    if cold_start and (restart_file is not None):
        raise ValueError('Cannot use restart file file on a cold start.')

    kdisk = None    # First fort.X.nc file to write
    if cold_start:
        start_type = START_COLD
        rsf = None
    elif restart_file is None:
        # Not specified a cold start, but no rsf given;
        # Use fort.1.nc or fort.2.nc
        rsf = latest_rsf(
            [os.path.join(paths.run, x)
             for x in ('fort.1.nc', 'fort.2.nc')])

        if rsf is None:    # No fort files exist
            start_type = START_COLD
        else:
            start_type = START_CHECKPOINT

            # First checkpoint file should be the one we did NOT start from
            leaf = os.path.split(rsf)
            if leaf == 'fort.1.nc':
                kdisk = 2
            else:
                kdisk = 1
    else:
        # User specified a restart_file; see what kind it is
        rsf = os.path.abspath(restart_file)
        start_type = rsf_type(rsf)

    # Make sure the rsf file exists and seems OK
    if rsf is not None:
        with netCDF4.Dataset(rsf, 'r') as nc:
            itime = nc.variables['itime'][:]
            print('Restarting from {} (itime={}).'.format(rsf, itime))

    if start_type == START_COLD:
        if (status.status >= launchers.STOPPED) and (not force):
            if not ectl.util.query_yes_no('Run is STOPPED; do you wish to overwrite and restart?', default='no'):
                sys.exit(-1)
    # ---------------------------------

    modelexe = os.path.join(paths.run, 'pkg', 'bin', 'modelexe')
    _launcher = rundir.new_launcher(paths.run, launcher)
    log_dir = os.path.join(paths.run, 'log')

    # ------- Load the rundeck and rewrite the I file (and symlinks)
    try:
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
            rd.set('AIC', rsf, type=rundeck.FILE)
        elif start_type == START_CHECKPOINT:
            rd.set('CHECKPOINT', rsf, type=rundeck.FILE)

        if kdisk is not None:
            rd.set('KDISK', str(kdisk))

        # Make additional modifications to the rundeck
        for rd_modify in rundeck_modifys:
            rd_modify(rd, start_type == START_COLD)
        
        rundir.make_rundir(rd, paths.run)

    except IOError:
        print('Warning: Cannot load rundeck.R.  NOT rewriting I file')

    # -------- Construct the main command line
    mpi_cmd = ['mpirun', '-timestamp-output']

    # ------- Delete timestamp.txt
    try:
        os.remove(os.path.join(paths.run, 'timestep.txt'))
    except:
        pass

    # -------- Determine log file(s)
    if log_dir != '-':
        make_vdir(log_dir)
        mpi_cmd.append('-output-filename')
        mpi_cmd.append(os.path.join(log_dir, 'q'))

    # ------ Add modele to the command
    modele_cmd = [modelexe]
#    if start_type == START_COLD:
#        modele_cmd.append('-cold-restart')
    modele_cmd.append('-i')
    modele_cmd.append('I')

    # ------- Run it!
    sys.exit(0)
    _launcher(mpi_cmd, modele_cmd, np=ntasks, time=time, synchronous=synchronous)
    if not synchronous:
        _launcher.wait()
        print_status(paths.run)

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
