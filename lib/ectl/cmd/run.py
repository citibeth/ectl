import multiprocessing
import os
import hashlib
import argparse
import llnl.util.tty as tty
import ectl
import ectl.cmd
from ectl import pathutil,rundeck,rundir,xhash
from ectl.rundeck import legacy
import re
from ectl import iso8601
import StringIO
import subprocess
import sys
import shutil
from ectl import iso8601
import datetime

description = 'Creates a flat rundeck file (eg: make rundeck)'

def setup_parser(subparser):
    subparser.add_argument(
        'run', help='Directory of run to give execution command')
    subparser.add_argument('--restart', action='store_true', dest='restart', default=False,
        help="Restart the run, even if it's already started")
    subparser.add_argument('--end', '-e', action='store', dest='end',
        help='[iso8601] Time to stop the run')
    subparser.add_argument('-o', action='store', dest='log_dir',
        help="Name of file for output (relative to rundir); '-' means STDOUT")
    subparser.add_argument('-l', '--launcher', action='store', dest='launcher', default='fg',
        choices=['fg', 'serial', 'slurm', 'slurm-debug'],
        help='How to run the program')

    # -------- Arguments for SOME launchers
    subparser.add_argument('-np', action='store', dest='np',
        help='Number of MPI jobs (launcher=fg,slurm)')

    subparser.add_argument('-t', action='store', dest='slurm_t',
        help='Slurm time allocation length')


# http://stackoverflow.com/questions/12902008/python-how-to-find-out-whether-hyperthreading-is-enabled
cpusRE = re.compile(r'CPU\(s\):\s*(.*)')
threadsRE = re.compile(r'Thread\(s\) per core:\s*(.*)')
def detect_ncores():
    buf = StringIO.StringIO()
    p = subprocess.Popen('lscpu', stdout=subprocess.PIPE)
    output = p.stdout.read()
    p.wait()
    for line in output.split('\n'):
        match = cpusRE.match(line)
        if match is not None:
            cpus = int(match.group(1))
        else:
            match = threadsRE.match(line)
            if match is not None:
                threads = int(match.group(1))
    return cpus // threads


def fg_launcher(mpi_cmd, modele_cmd, np=None):
    # --------- determine number of processors to use
    np = int(np) if np is not None else detect_ncores()
    mpi_cmd.extend(['-np', str(np)])
    cmd = mpi_cmd + modele_cmd

    print(' '.join(cmd))
    subprocess.call(mpi_cmd + modele_cmd)

def serial_launcher(cmd, fout, args):
    fout.write('serial_launcher cmd = %s\n' % ' '.join(cmd))
    fout.flush()
    subprocess.call(cmd,stdout=fout, stderr=fout)
    fout.flush()

#sbatch --qos=debug -A s1001 -n %np -t %t 


def run(parser, args, unknown_args):
    if len(unknown_args) > 0:
        raise ValueError('Unkown arguments: %s' % unknown_args)

    # ------ Parse Arguments
    paths = rundir.FollowLinks(args.run)
    cold_restart = args.restart or (rundir.status(paths.run) == rundir.INITIAL)
    modelexe = os.path.join(paths.run, 'pkg', 'bin', 'modelexe')

    module = sys.modules[__name__]
    launcher_fn = getattr(module, args.launcher + '_launcher')

    if args.log_dir is not None:
        if args.log_dir == '-':
            log_dir = args.log_dir
        else:
            log_dir = os.path.abspath(ags.log_dir)
    else:
        log_dir = os.path.join(paths.run, 'log')

    # ------- Load the rundeck and rewrite the I file
    try:
        rundeck_R = os.path.join(paths.run, 'rundeck', 'rundeck.R')
        rd = rundeck.load(rundeck_R, modele_root=paths.src)
        rd.resolve(file_path=ectl.rundeck.default_file_path, download=True,
            download_dir=ectl.rundeck.default_file_path[0])

        # Send end date
        if args.end is not None:
            end = datetime.datetime(*iso8601.parse_date(args.end))
            rd.set(('INPUTZ_cold' if cold_restart else 'INPUTZ', 'END_TIME'), end)

        sections = rundeck.ParamSections(rd)
        rundir.make_rundir(rd, paths.run)

    except IOError:
        print 'Warning: Cannot load flat.R.  NOT rewriting I file'
    


    # -------- Construct the main command line
    mpi_cmd = ['mpirun', '-timestamp-output']

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

    # ------- Open output file
    os.chdir(paths.run)

    # ------- Run it!
    launcher_fn(mpi_cmd, modele_cmd, np=args.np)


