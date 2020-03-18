from __future__ import print_function
import multiprocessing
import os
import hashlib
import argparse
import llnl.util.tty as tty
import ectl
import ectl.setup
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
import signal
import subprocess

description = 'Clones an existing run into a new run directory.'

def setup_parser(subparser):
    subparser.add_argument('src',
        help='Name of run directory to copy')
    subparser.add_argument('dest',
        help='Name of destination')



def cp(parser, args, unknown_args):
    if len(unknown_args) > 0:
        raise ValueError('Unkown arguments: %s' % unknown_args)

    paths = rundir.FollowLinks(args.src)

    # Create destination
    os.makedirs(args.dest)

    # Copy rundeck and related config files
    shutil.copytree(os.path.join(args.src, 'config'), os.path.join(args.dest, 'config'))

    # Copy symlinks
    ectl.setup.set_link(paths.rundeck, os.path.join(args.dest, 'upstream.R'))
    ectl.setup.set_link(paths.src, os.path.join(args.dest, 'src'))
    os.symlink('config/rundeck.R', os.path.join(args.dest, 'rundeck.R'))
