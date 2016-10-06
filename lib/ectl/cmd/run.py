import ectl
import ectl.launch

description = 'Continues (or restarts) a run.'

def setup_parser(subparser):
    ectl.launch.setup_parser(subparser)

    subparser.add_argument('--restart-file', '-rsf', dest='restart_file', default=None,
        help="File to use for restart (fort.X.nc or .rsf file)")

    subparser.add_argument('--restart-date', '-rsd', dest='restart_date', default=None,
        help="Find rsf file at or before given date")

def run(parser, args, unknown_args):
    if len(unknown_args) > 0:
        raise ValueError('Unkown arguments: %s' % unknown_args)

    ectl.launch.run(args, 'run')
