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


def rd_set_ts(rd, cold_start, start_ts, end_ts):
    """Modifies the rundeck with start and end times."""

    if (not cold_start) and (start_ts is not None):
        raise ValueError('Cannot set a start timestamp in the middle of a run!')
    if start_ts is not None:
        rd.set(('INPUTZ', 'START_TIME'), datetime.datetime(*start_ts))
    if end_ts is not None:
        rd.set(('INPUTZ', 'END_TIME'), datetime.datetime(*end_ts))


def run(args, cmd, rsf=None):
    """Top-level that parses command line arguments

    cmd: 'start', 'run', 'restart'
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
    launch(args.run, launcher=args.launcher, force=args.force,
        ntasks=args.np, time=args.time,
        rundeck_modifys=[lambda rd, cold_start: rd_set_ts(rd, cold_start, start_ts, end_ts)],
        cold_start=(cmd == 'start'))


def launch(run, launcher=None, force=False, ntasks=None, time=None, rundeck_modifys=list(), cold_start=False, rsf=None, synchronous=False):
    """API call to start a ModelE execution.

    Warm/Cold Restart is determined as follows:
        if rsf is not None:
            if not exists(rsf): ERROR: Specified restart file doesn't exist.
            if cold_start: ERROR: Cannot specify cold-start and restart file.
            WARM START
        elif cold_start or (status.status == launchers.INITIAL):
            COLD START
        else:
            WARM START

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
    rsf:
        Restart or checkpoint file to start from.
    synchronous:
        Block until ModelE is done running.  Usually good only for small tests.
    """

    if launcher is None:
        launcher = os.environ.get('ECTL_LAUNCHER', None)
    if launcher is None:
        raise ValueError('No launcher specified.  Please use --launcher command line option, or set the ECTL_LAUNCHER environment variable.  Valid values are mpi, slurm and slurm-debug.')


    # Check arguments
    if rsf is not None:
        if not os.path.exists(rsf):
            raise ValueError('Specified restart file does not exist: %s' % rsf)
        if cold_start:
            raise ValueError('Cannot specify a colde start and rsf file together.')

    paths = rundir.FollowLinks(run)
    status = rundir.Status(paths.run)
    if (status.status == launchers.NONE):
        raise ValueError('Run does not exist, cannot run: {0}\n'.format(run))
    if (status.status == launchers.RUNNING):
        raise ValueError('Run is already running: {0}\n'.format(run))

    # Force cold start if there's nothing to warm start from.
    # This is routine, when running for the first time.
    _cold_start = cold_start or (status.status == launchers.INITIAL)

    if _cold_start:    # Start a new run
        if (status.status >= launchers.STOPPED) and (not force):
            if not ectl.util.query_yes_no('Run is STOPPED; do you wish to overwrite and restart?', default='no'):
                sys.exit(-1)

    else:    # Continue a previous run
        if status.status == launchers.FINISHED:
            sys.stderr.write('Run is finished, cannot continue: {0}\n'.format(run))
            sys.exit(-1)

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
        if _cold_start:
            for pname,param in list(rd.params.items()):
                if not isinstance(pname, tuple):
                    continue
                if pname[0] == 'INPUTZ_cold':
                    new_pname = ('INPUTZ', pname[1])
                    param.pname = new_pname
                    rd.params[new_pname] = param
                    del rd.params[pname]

            # This is probably redundant.
            rd.set(('INPUTZ', 'ISTART'), str(2))

        # Do additional modifications to the rundeck
        for rd_modify in rundeck_modifys:
            rd_modify(rd, _cold_start)
        
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
#    if _cold_start:
#        modele_cmd.append('-cold-restart')
    modele_cmd.append('-i')
    modele_cmd.append('I')

    # ------- Run it!
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
