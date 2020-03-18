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
import sys
import shutil
from ectl import iso8601
import datetime
import ectl.rundir
import ectl.keepalive
import signal
import subprocess
import ectl.config
import time

description = 'Restarts runs that have exhausted their wall time'

def setup_parser(subparser):
    subparser.add_argument('dir', nargs='?', default='.',
        help='Directory inside the Ectl root')

    subparser.add_argument('-l', '--launcher', action='store', dest='launcher',
        help='How to run the program: mpi, slurm, slurm-debug')

    # -------- Arguments for SOME launchers
    subparser.add_argument('-np', '--ntasks', '-n', action='store', dest='np',
        help='Number of MPI jobs')
    subparser.add_argument('-t', '--time', action='store', dest='time',
        help='Length of wall clock time to run (see sbatch): [mm|hh:mm:ss]')
    subparser.add_argument('--every', action='store', dest='every', default=None,
        help='Number of minutes between keepalive polls')

def keepalive(parser, args, unknown_args):
    if len(unknown_args) > 0:
        raise ValueError('Unkown arguments: %s' % unknown_args)

    # Find the root of the ectl tree
    ectl_conf = pathutil.search_up(os.path.abspath(args.dir),
        lambda path: pathutil.has_file(path, 'ectl.conf'))
    while True:
        config = ectl.config.Config(os.path.split(ectl_conf)[0])

        lock = None
        try:
            # Make sure lockfile exists...
            lockfile = config.keepalive + '.lock'
            if not os.path.exists(lockfile):
                with open(lockfile, 'w'):
                    pass

            runs = ectl.keepalive.load(config.keepalive)
            runs = ectl.keepalive.check(args, runs)
            ectl.keepalive.save(runs, config.keepalive)
        finally:
            if lock is not None:
                lock.release_write()

        # Do repeatedly if we're told to...
        if args.every is None:
            break

        time.sleep(int(args.every)*60)
