import os
# import hashlib
# import argparse
# import llnl.util.tty as tty
# import ectl
# import ectl.cmd
# from ectl import pathutil,rundir,xhash,srcdir
# import ectl.config
# import ectl.rundeck
# from ectl.rundeck import legacy
# import subprocess
# import base64
# import re
# from ectl import iso8601
# import datetime
import sys
from spack.util import executable

def setup_parser(subparser):
    subparser.add_argument(
        'run', help='Directory of run to setup')

def merge(parser, args, unknown_args):
    args.run = os.path.abspath(args.run)
    if len(unknown_args) > 0:
        raise ValueError('Unkown arguments: %s' % unknown_args)

    rundeck_dir = os.path.join(args.run, 'rundeck')
    rundeck_R = os.path.join(rundeck_dir, 'rundeck.R')


    git = executable.which('git')
    os.chdir(rundeck_dir)
    git('add', rundeck_R, echo=sys.stdout)
    git('commit', '-m', 'Merged changes after hand edit', echo=sys.stdout)

