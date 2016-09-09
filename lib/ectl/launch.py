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
        help='[iso8601],[iso8601],[iso8601] (start, cold-end, end) Timespan to run it for')
#    subparser.add_argument('--end', '-e', action='store', dest='end',
#        help='[iso8601] Time to stop the run')
#    subparser.add_argument('-o', action='store', dest='log_dir',
#        help="Name of file for output (relative to rundir); '-' means STDOUT")
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

def run(args, cmd, verify_restart=False, rsf=None):
    """cmd: 'start', 'run', 'restart'
        User-level command calling this
    verify_restart:
        If True, then ask user if we're starting a run over.
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
    slauncher = args.launcher
    if slauncher is None:
        slauncher = os.environ.get('ECTL_LAUNCHER', None)
    if slauncher is None:
        raise ValueError('No launcher specified.  Please use --launcher command line option, or set the ECTL_LAUNCHER environment variable.  Valid values are mpi, slurm and slurm-debug.')


    paths = rundir.FollowLinks(args.run)
    status = rundir.Status(paths.run)
    if (status.status == launchers.NONE):
        sys.stderr.write('Run does not exist, cannot run: {0}\n'.format(args.run))
        sys.exit(-1)
    if (status.status == launchers.RUNNING):
        sys.stderr.write('Run is already running: {0}\n'.format(args.run))
        sys.exit(-1)

    cold_restart = (cmd == 'start') or (status.status == launchers.INITIAL)

    if cold_restart:    # Start a new run
        if status.status >= launchers.STOPPED:
            if not ectl.util.query_yes_no('Run is STOPPED; do you wish to overwrite and restart?', default='no'):
                sys.exit(-1)

    else:    # Continue a previous run
        if start_ts is not None:
            raise ValueError('Cannot set a start timestamp in the middle of a run!')

        if status.status == launchers.FINISHED:
            sys.stderr.write('Run is finished, cannot continue: {0}\n'.format(args.run))
            sys.exit(-1)

    modelexe = os.path.join(paths.run, 'pkg', 'bin', 'modelexe')
    launcher = rundir.new_launcher(paths.run, slauncher)
    log_dir = os.path.join(paths.run, 'log')

    # ------- Load the rundeck and rewrite the I file (and symlinks)
    try:
        rd = rundeck.load(os.path.join(paths.run, 'rundeck', 'rundeck.R'), modele_root=paths.src)
        rd.resolve(file_path=ectl.rundeck.default_file_path, download=True,
            download_dir=ectl.rundeck.default_file_path[0])

        # Set timespan for run end date
        if start_ts is not None:
            rd.set(('INPUTZ', 'START_TIME'), datetime.datetime(*start_ts))
        if end_ts is not None:
            rd.set(('INPUTZ_cold' if cold_restart else 'INPUTZ', 'END_TIME'), datetime.datetime(*end_ts))


        sections = rundeck.ParamSections(rd)
        rundir.make_rundir(rd, paths.run)

    except IOError:
        print 'Warning: Cannot load rundeck.R.  NOT rewriting I file'

    # -------- Construct the main command line
    mpi_cmd = ['mpirun', '-timestamp-output']

    # ------- Delete timestamp.txt
    try:
        os.remove(os.path.join(paths.run, 'timestep.txt'))
    except:
        pass

    # -------- Determine log file(s)
    if log_dir != '-':
        try:
            shutil.rmtree(log_dir)
        except:
            pass
        os.mkdir(log_dir)

        log_main = os.path.join(paths.run,'log0')
        try:
            os.remove(log_main)
        except:
            pass
        os.symlink(os.path.join(log_dir, 'l.1.0'), log_main)
        mpi_cmd.append('-output-filename')
        mpi_cmd.append(os.path.join(log_dir, 'q'))

    # ------ Add modele to the command
    modele_cmd = [modelexe]
    if cold_restart:
        modele_cmd.append('-cold-restart')
    modele_cmd.append('-i')
    modele_cmd.append('I')

    # ------- Run it!
    launcher(mpi_cmd, modele_cmd, np=args.np, time=args.time)
    launcher.wait()
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
