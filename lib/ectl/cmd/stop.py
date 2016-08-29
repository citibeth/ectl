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

description = 'Stop (pause) a run.  May be re-started later.'

def setup_parser(subparser):
    subparser.add_argument('run', nargs='?', default='.',
        help='Directory of run to give execution command')

    subparser.add_argument('--force', '-f', action='store_true', dest='force', default=False,
        help='Kill the run immediately (rather than just telling it to stop).  Use only if needed.')

def stop(parser, args, unknown_args):
    if len(unknown_args) > 0:
        raise ValueError('Unkown arguments: %s' % unknown_args)

    run = os.path.abspath(args.run)

    status = ectl.rundir.Status(run)
    if (status.status == launchers.NONE):
        sys.stderr.write('Error: No valid run in directory %s\n' % run)
        sys.exit(-1)

    # Ask politely to stop
    with open(os.path.join(run, 'flagGoStop'), 'w') as fout:
        fout.write('__STOP__\n')
    sys.stderr.write('Asked to stop run: %s\n' % run)


    # Use system to stop it.
    if args.force:
        launcher = status.new_launcher()
        launcher.kill(status.launch_txt)

    # Show what happened...
    status = ectl.rundir.Status(run)
    launcher = status.new_launcher()
    launcher.ps(status.launch_txt, sys.stdout)
