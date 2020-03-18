from __future__ import print_function
import ectl.cdlparams


description = 'Clones an existing run into a new run directory.'

def setup_parser(subparser):
    subparser.add_argument('input',
        help='Name of .cdl file (or directory of .cdl files)')
    subparser.add_argument('--output', '-o',
        help='Name of output file (or output directory)')


def ncgen(parser, args, unknown_args):
    if len(unknown_args) > 0:
        raise ValueError('Unkown arguments: %s' % unknown_args)

    ectl.cdlparams.resolve_cdl(args.input, args.output, keep_partial=True)
