from __future__ import print_function
import multiprocessing
import os
import hashlib
import argparse
import llnl.util.tty as tty
import ectl.util
import ectl
import ectl.cmd
from ectl import pathutil,rundir,xhash,srcdir,launchers
import ectl.config
import ectl.rundeck
from ectl.rundeck import legacy
import subprocess
import base64
import re
import datetime
import sys
from spack.util import executable
from giss import pyar

def setup_parser(subparser):
    subparser.add_argument('--src', '-s', action='store', dest='src',
        required=True,
        help='Top-level directory of ModelE source')

    subparser.add_argument('--force', '-f', action='store_true', dest='force',
        default=False,
        help="Keep going even if files don't exist")

def rmbuild(parser, args, unknown_args):
    with ectl.util.working_dir(args.src):
        with open('modele-control.pyar', 'r') as fin:
            for fname in pyar.list_archive(fin):
                print('Removing %s' % fname)
                try:
                    os.remove(fname)
                except OSError as err:
                    if args.force:
                        print('   (failed)')
                    else:
                        raise

