import ectl.rundir
import os
import subprocess
import sys

description = 'Creates a flat rundeck file (eg: make rundeck)'

def setup_parser(subparser):
    subparser.add_argument(
        'run', help='ModelE run directory')

    subparser.add_argument('-v', '--verbose',
        action='store_true', dest='verbose',
        help="Output diagnostics to stderr")


def env(parser, args, unknown_args):

    # Add to environment
    old = ectl.rundir.FollowLinks(args.run)
    newenv = dict()
    if old.run is not None:
        newenv['ECTL_RUN'] = old.run
    if old.rundeck is not None:
        newenv['ECTL_RUNDECK'] = old.rundeck
    if old.src is not None:
        newenv['ECTL_SRC'] = old.src
    if old.build is not None:
        newenv['ECTL_BUILD'] = old.build
    if old.pkg is not None:
        newenv['ECTL_PKG'] = old.pkg

    if args.verbose:
        for k,v in newenv.items():
            sys.stderr.write("%s='%s'\n" % (k,v))

    totalenv = os.environ.copy()
    totalenv.update(newenv)

    # Run user's command with new environment
    cmd = unknown_args
    if len(cmd) > 0:
        subprocess.Popen(cmd, env=totalenv).wait()
