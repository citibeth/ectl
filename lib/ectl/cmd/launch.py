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

description = 'Creates a flat rundeck file (eg: make rundeck)'

def setup_parser(subparser):
    subparser.add_argument(
        'rundir', help='Directory of run to give execution command')
    subparser.add_argument('--restart', action='store_true', dest='restart', default=False,
        help="Restart the run, even if it's already started")
    subparser.add_argument('-o', action='store', dest='output_fname', default='PRT',
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


def fg_launcher(cmd, fout, args):
    if args.np is not None:
        np = int(args.np)
    else:
        np = detect_ncores()

    cmd = ['mpirun', '-np', str(np)] + cmd
    fout.write('fg_launcher cmd = %s\n' % ' '.join(cmd))
    fout.flush()
    subprocess.call(cmd, stdout=fout, stderr=fout)
    fout.flush()

def serial_launcher(cmd, fout, args):
    fout.write('serial_launcher cmd = %s\n' % ' '.join(cmd))
    fout.flush()
    subprocess.call(cmd,stdout=fout, stderr=fout)
    fout.flush()

#sbatch --qos=debug -A s1001 -n %np -t %t 


def launch(parser, args, unknown_args):

    # ------ Parse Arguments
    run_dir = pathutil.search_file(args.rundir, [os.path.join(ectl.root, 'runs')])
    modelexe = os.path.join(run_dir, 'pkg', 'bin', 'modelexe')

    module = sys.modules[__name__]
    launcher_fn = getattr(module, args.launcher + '_launcher')


    # -------- Construct the main command line
    cmd = [os.path.join(ectl.root_exe, 'bin', 'ectl'), 'run'] + unknown_args + [modelexe]
    if args.restart or rundir.status(run_dir) == rundir.INITIAL:
        cmd.append('-cold-restart')
    cmd.append('-i')
    cmd.append('I')

    # ------- Open output file
    os.chdir(run_dir)
    if args.output_fname == '-':
        fout = sys.stdout
    else:
        #rename_file(args.output_fname)
        fout = open(args.output_fname, 'w')

    # ------- Run it!
    launcher_fn(cmd, fout, args)


