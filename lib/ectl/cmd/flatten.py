import multiprocessing
import os
import hashlib
import argparse
import llnl.util.tty as tty
import ectl
import ectl.cmd
from ectl import pathutil,rundeck,rundir,xhash
from ectl.rundeck import legacy
import subprocess

description = 'Creates a flat rundeck file (eg: make rundeck)'

def setup_parser(subparser):
    subparser.add_argument(
        'in_rundeck', nargs=1, help='Input rundeck')
    subparser.add_argument(
        'out_rundeck', nargs=1, help='Output rundeck')

def flatten(parser, args, unknown_args):
    if len(unkown_args) > 0:
        raise ValueError('Unkown arguments: %s' % unknown_args)

    in_rundeck = args.in_rundeck[0]
    out_rundeck = args.out_rundeck[0]

    if os.path.exists(out_rundeck):
        raise Exception('Output rundeck %s already exists' % out_rundeck)

    modele_root = pathutil.modele_root(in_rundeck)
    template_path = [os.path.join(modele_root, 'templates')]

    with open(out_rundeck, 'w') as fout:
        for lineno,line in legacy.preprocessor(in_rundeck, template_path):
            fout.write(line)
