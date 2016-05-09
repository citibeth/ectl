import multiprocessing
import os
import hashlib
import argparse
import llnl.util.tty as tty
import ectl
import ectl.cmd
from ectl import pathutil,rundeck,rundir,xhash
from ectl.rundeck import legacy
import re
from ectl import iso8601
import sys
import subprocess
import select

description = 'Creates a flat rundeck file (eg: make rundeck)'

def setup_parser(subparser):
    subparser.add_argument('-f', '--filter', action='store', dest='filter', default='none',
        choices=['ompi', 'none'],
        help='Filter for model output')

def ompi_filter(cmd):
    rank = int(os.environ['OMPI_COMM_WORLD_RANK'])

    out_prefix = '[o%d]' % rank
    err_prefix = '[e%d]' % rank

    p = subprocess.Popen(cmd,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    exit_me = False
    while True:
        reads = [p.stdout.fileno(), p.stderr.fileno()]
        ret = select.select(reads, [], [])

        input_detected = False
        for fd in ret[0]:
            if fd == p.stdout.fileno():
                read = p.stdout.readline().decode()
                if len(read) > 0:
                    input_detected = True
                    sys.stdout.write(out_prefix)
                    sys.stdout.write(read)
            if fd == p.stderr.fileno():
                read = p.stderr.readline().decode()
                if len(read) > 0:
                    input_detected = True
                    sys.stdout.write(err_prefix)
                    sys.stdout.write(read)

        if exit_me and not input_detected:
            break

        if p.poll() != None:
            exit_me = True


def none_filter(cmd):
    print('none_filter cmd = %s' % ' '.join(cmd))
    subprocess.call(cmd, stdout=sys.stdout, stderr=sys.stdout)
    sys.stdout.flush()

def run(parser, args, unknown_args):
    # ------ Parse Arguments
    module = sys.modules[__name__]
    filter_fn = getattr(module, args.filter + '_filter')

    # ------- Run it!
    filter_fn(unknown_args)
