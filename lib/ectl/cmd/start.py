import ectl
import ectl.launch

description = 'Starts a run'

setup_parser = ectl.launch.setup_parser

def start(parser, args, unknown_args):
    if len(unknown_args) > 0:
        raise ValueError('Unkown arguments: %s' % unknown_args)

    ectl.launch.run(args, cmd='start')
