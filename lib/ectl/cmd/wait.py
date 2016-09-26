import ectl.wait

description = 'Waits until one or more runs have terminated.'

def setup_parser(subparser):
    subparser.add_argument('runs', nargs='*',
        help='Directory of run to give execution command')
    subparser.add_argument('-r', '--recursive', action='store_true', dest='recursive', default=False,
        help='Recursively descend directories')

    subparser.add_argument('-v', '--verbose', action='store_true', dest='verbose', default=False,
        help='Print more output')

def wait(parser, args, unknown_args):
    if len(unknown_args) > 0:
        raise ValueError('Unkown arguments: %s' % unknown_args)

    ectl.wait.wait(args.runs, recursive=args.recursive, verbose=args.verbose)
