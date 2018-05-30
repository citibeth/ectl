import os
from spack.util import executable
import ectl.util

def setup_parser(subparser):
    subparser.add_argument(
        'run', help='Directory of run to setup')

def merge(parser, args, unknown_args):
    args.run = os.path.abspath(args.run)
    if len(unknown_args) > 0:
        raise ValueError('Unkown arguments: %s' % unknown_args)

    do_merge(args.run)

def do_merge(run):
    """run:
        Run directory
    """
    git = executable.which('git')

    with ectl.util.working_dir(os.path.join(run, 'config')):
        git('add', 'rundeck.R')
        git('commit', 'rundeck.R', '-m', 'Fixed conflicts')
        git('commit')
