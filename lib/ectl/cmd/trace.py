import argparse
import os
import subprocess
import sys
import glob

description = 'Get a backtrace for a run'

def setup_parser(subparser):
    subparser.add_argument('run', nargs='?', default='.',
        help='Directory of run to give execution command')

    subparser.add_argument('-n', dest='logno', default='',
        help='Number of log directory to trace')


def trace(parser, args, unknown_args):
    if len(unknown_args) > 0:
        raise ValueError('Unkown arguments: %s' % unknown_args)

    run = os.path.abspath(args.run)

    if len(args.logno) == 0:
        logleaf = 'log'
    else:
        logleaf = 'log%02d' % int(args.logno)
    logdir = os.path.join(run, logleaf)

    # OpenMPI v3
    # logfiles = glob.glob(os.path.join(logdir, 'log', '1', 'rank.*', 'stdout'))

    digitsRE = re.compile(r'\d+')
    # Use the symlinks, which should be the same for all MPI versions
    logfiles = [x for x in os.listdir(logdir) if digitsRE.match(x) is not None]
    cmd = ['etr'] + sorted(logfiles)

    print('cmd', cmd)
    subprocess.run(cmd)
