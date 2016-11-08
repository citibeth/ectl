import ectl
import ectl.launch
import re
import os
import subprocess

description = 'Shows output from a currently-running ModelE'


def setup_parser(subparser):
    subparser.add_argument('run', nargs='?', default='.',
        help='Directory of run to give execution command')

    subparser.add_argument('--rank', '-r', default='0',
        help='MPI rank to show (by default, show rank=0')

    subparser.add_argument('--follow', '-f', action='store_true', default=False,
        help='Do tail -f')

    subparser.add_argument('--lines', '-n', default='30',
        help='Number of lines to show')


qRE = re.compile(r'q\.(\d)+\.(\d)+')

def tail(parser, args, unknown_args):
    if len(unknown_args) > 0:
        raise ValueError('Unkown arguments: %s' % unknown_args)


    # Find the log file to tail
    logdir = ectl.rundir.latest_logdir(args.run)
    logfile = ectl.logdir.logfiles_dict(logdir)[int(args.rank)]

    # Tail it!
    cmd = ['tail']
    if args.follow:
        cmd.append('-f')
    cmd.append('-n')
    cmd.append(args.lines)
    cmd.append(logfile)

    lines = int(args.lines)
    use_pager = (not args.follow) and lines > 40
    if use_pager:
        # http://stackoverflow.com/questions/4846891/python-piping-output-between-two-subprocesses
        cmd_p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        less_p = subprocess.Popen(['less'], stdin=cmd_p.stdout)
        cmd_p.stdout.close()
        less_p.communicate()
    else:
        subprocess.call(cmd)
