import argparse
import os
import subprocess
import sys

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


    logfiles = []
    for leaf in os.listdir(logdir):
        if leaf[:2] == 'q.':
            logfiles.append(os.path.join(logdir, leaf))
    cmd = ['etr'] + sorted(logfiles)

    print('cmd', cmd)
    subprocess.run(cmd)
