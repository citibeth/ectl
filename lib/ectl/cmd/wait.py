from __future__ import print_function
import multiprocessing
import os
import hashlib
import argparse
import llnl.util.tty as tty
import ectl
import ectl.cmd
from ectl import pathutil,rundeck,rundir,xhash,launchers
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
import time

description = 'Waits until one or more runs have terminated.'

def setup_parser(subparser):
    subparser.add_argument('runs', nargs='*',
        help='Directory of run to give execution command')
    subparser.add_argument('-r', '--recursive', action='store_true', dest='recursive', default=False,
        help='Recursively descend directories')

def wait(parser, args, unknown_args):
    if len(unknown_args) > 0:
        raise ValueError('Unkown arguments: %s' % unknown_args)


    recursive = args.recursive
    doruns = rundir.all_rundirs(args.runs, recursive=args.recursive)

    # Construct set of currently-running runs
    running = set()
    for run,status in doruns:
        if status.status != launchers.RUNNING:
            print('{0}: {1}'.format(status.run, status.sstatus))
        else:
            running.add(status)

    if len(running) == 0:
        return

    print('Waiting...')

    # Wait for them to all die
    while len(running) > 0:
        time.sleep(1)

        # Determine what is no longer running
        to_remove = set()
        for status in running:
            if status.refresh_status() != launchers.RUNNING:
                print('{0}: {1}'.format(status.run, status.sstatus))
                to_remove.add(status)

        # Remove those items from the running set
        for status in to_remove:
            running.remove(status)
