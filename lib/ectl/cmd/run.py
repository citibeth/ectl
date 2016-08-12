import ectl
import ectl.launch

description = 'Continues (or restarts) a run.'

def setup_parser(subparser):
    ectl.launch.setup_parser(subparser)

#    subparser.add_argument('--restart', action='store_true', dest='restart', default=False,
#        help="Restart the run, even if it's already started")

def run(parser, args, unknown_args):
    if len(unknown_args) > 0:
        raise ValueError('Unkown arguments: %s' % unknown_args)

    ectl.launch.run(args, cmd='run')
