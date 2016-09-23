import ectl
import ectl.launch
import re
import os
import subprocess

description = 'Shows output from a currently-running ModelE'


def setup_parser(subparser):
    subparser.add_argument('run', nargs='?', default='.',
        help='Directory of run to give execution command')

    subparser.add_argument('--rank', '-r', default=None,
        help='MPI rank to show (by default, show minimum rank')

qRE = re.compile(r'q\.(\d)+\.(\d)+')

def tail(parser, args, unknown_args):
    if len(unknown_args) > 0:
        raise ValueError('Unkown arguments: %s' % unknown_args)

    args_rank = int(args.rank) if args.rank is not None else None

    # Find the log file to tail
    log = os.path.join(args.run, 'log')
    min_rank = 10000000
    min_fname = None
    for fname in os.listdir(log):
        match = qRE.match(fname)
        if match is None:
            continue
        rank = int(match.group(2))
        if args_rank is not None:
            if rank == args_rank:
                min_fname = fname
                break
        elif rank < min_rank:
            min_rank = rank
            min_fname = fname

    # Test we have something
    if min_fname is None:
        sys.stderr.write('No log files found matching rank={0}'.format(args.rank))
        return

    # Tail it!
    cmd = ['tail', '-f', os.path.join(log, min_fname)]
    subprocess.call(cmd)
