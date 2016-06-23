import ectl.rundir

description = 'Creates a flat rundeck file (eg: make rundeck)'

def setup_parser(subparser):
    subparser.add_argument(
        'run', help='Directory of run to give execution command')

    subparser.add_argument('-b', '--build',
        action='store_true', dest='build',
        help="Location of build tree")
    subparser.add_argument('-p', '--pkg',
        action='store_true', dest='pkg',
        help="Location of installed pkg tree")


def location(parser, args, unknown_args):
    if len(unknown_args) > 0:
        raise ValueError('Unkown arguments: %s' % unknown_args)

    # ------ Parse Arguments
    #run = os.path.abspath(args.run)
    old = ectl.rundir.FollowLinks(args.run)

    if args.pkg:
        print(old.pkg)
    elif args.build:
        print(old.build)
