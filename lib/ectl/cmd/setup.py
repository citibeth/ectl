from __future__ import print_function
import multiprocessing
import os
import hashlib
import argparse
import llnl.util.tty as tty
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
import ectl.setup

description = 'Setup a ModelE run.'

def setup_parser(subparser):
#    subparser.add_argument(
#        'rundeck', nargs=1, help='Rundeck file use in setup.')
    subparser.add_argument('--ectl', action='store', dest='ectl',
        help='Root of ectl tree: ectl/runs, ectl/builds, ectl/pkgs')
    subparser.add_argument(
        'run', help='Directory of run to setup')
    subparser.add_argument('--rundeck', '-rd', action='store', dest='rundeck',
        help='Rundeck to use in setup')
    subparser.add_argument('--src', '-s', action='store', dest='src',
        help='Top-level directory of ModelE source')
    subparser.add_argument('--pkgbuild', action='store_true', dest='pkgbuild', default=False,
        help='Name package dir after build dir.')
    subparser.add_argument('--rebuild', action='store_true', dest='rebuild', default=False,
        help='Rebuild the package, even if it seems to be fine.')
    subparser.add_argument('--no-unpack', action='store_false', dest='unpack', default=True,
        help="Don't unpack the build system from pyar.")
    subparser.add_argument('--jobs', '-j', action='store', dest='jobs',
        help='Number of cores to use when building.')
    subparser.add_argument('--python', action='store', dest='python', default='python3',
        help='Name of Python command to use running build/setup scripts')
    subparser.add_argument('--pythonpath', action='store', dest='pythonpath', default=None,
        help='PYTHONPATH to use when running Python')


def setup(parser, args, unknown_args):
    args.run = os.path.abspath(args.run)
    ectl.setup.setup(
        args.run, rundeck=args.rundeck, src=args.src,
        jobs=None if args.jobs is None else int(args.jobs),
        pkgbuild=args.pkgbuild, rebuild=args.rebuild, unpack=args.unpack,
        python=args.python, pythonpath=args.pythonpath, extra_cmake_args=unknown_args)
