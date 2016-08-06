from __future__ import print_function
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
import ectl.rundir
import signal

description = 'Reports on the status of a run.'

def setup_parser(subparser):
    subparser.add_argument('runs', nargs='*',
        help='Directory of run to give execution command')
    subparser.add_argument('-r', '--recursive', action='store_true', dest='recursive', default=False,
        help='Recursively descend directories')


def walk_rundirs(top, doruns):
    status = ectl.rundir.Status(top)
    if status.status == ectl.rundir.NONE:
        for sub in os.listdir(top):
            subdir = os.path.join(top, sub)
            if os.path.isdir(subdir):
                walk_rundirs(subdir, doruns)
    else:
        doruns.append((top,status))


def ps(parser, args, unknown_args):
    if len(unknown_args) > 0:
        raise ValueError('Unkown arguments: %s' % unknown_args)

    if len(args.runs) == 0:
        runs = [os.path.abspath('.')]
    else:
        runs = [os.path.abspath(run) for run in args.runs]

    recursive = args.recursive
    if (not recursive) and (len(runs) == 1):
        # Auto-recurse if a single given dir is not a run dir
        status = ectl.rundir.Status(runs[0])
        if status.status == ectl.rundir.NONE:
            recursive = True

    # ------- Get list of runs to do
    if recursive:
        doruns = list()
        for top_run in runs:
            walk_rundirs(top_run, doruns)
    else:
        doruns = [(run, ectl.rundir.Status(run)) for run in runs]

    print(doruns)

    for run,status in doruns:
        if (status.status == ectl.rundir.NONE):
            sys.stderr.write('Error: No valid run in directory %s\n' % run)
            sys.exit(-1)

        # Top-line status
        print('============================ {}'.format(os.path.split(run)[1]))
        print('status:  {}'.format(status.sstatus))

        # Run configuration
        paths = rundir.FollowLinks(run)
        paths.dump()

        # Launch.txt
        if status.launch_list is not None:
            for key,val in status.launch_list:
                print('{} = {}'.format(key, val))

        # Do launcher-specific stuff to look at the actual processes running.
        launcher = status.new_launcher()
        if launcher is not None:
            launcher.ps(sys.stdout)

