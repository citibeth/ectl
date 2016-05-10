import multiprocessing
import os
import hashlib
import argparse
import llnl.util.tty as tty
import ectl
import ectl.cmd
from ectl import pathutil,rundeck,rundir,xhash,srcdir
import subprocess
import base64
import re
from ectl import iso8601
import datetime

description = 'Setup a ModelE run.'

def setup_parser(subparser):
#    subparser.add_argument(
#        'rundeck', nargs=1, help='Rundeck file use in setup.')
    subparser.add_argument(
        'rundir', help='Directory of run to setup (inside ectl)')
    subparser.add_argument('--rundeck', '-rd', action='store', dest='rundeck',
        help='Rundeck to use in setup')
    subparser.add_argument('--timespan', '-ts', action='store', dest='timespan',
        help='[iso8601],[iso8601],[iso8601] (start, cold-end, end) Timespan to run it for')
    subparser.add_argument('--src', '-s', action='store', dest='src',
        help='Top-level directory of ModelE source')


def parse_date(str):
    if len(str) == 0:
        return None
    return iso8601.parse_date(str)

def follow_link(linkname, must_exist=False):
    if not os.path.exists(linkname):
        return None
    fname = os.path.realpath(linkname)
    if must_exist and not os.path.exists(fname):
        return None
    return fname

def buildhash(rd, src_dir):
    hash = hashlib.md5()
    xhash.update(rd, hash)
    xhash.update(src_dir, hash)    # Source directory
    return hash.hexdigest()
#    return base64.b32encode(hash.digest()).lower()

def pkghash(rd, src_dir):
    hash = hashlib.md5()
    xhash.update(rd, hash)
    srcdir.update_hash(src_dir, hash)
    return hash.hexdigest()
#    return base64.b32encode(hash.digest()).lower()

def good_pkg_dir(pkg_dir):
    """Determines that a pkg_dir has all binaries needed to run."""
    for file in ('lib/libmodele.so', 'bin/modelexe'):
        if not os.path.isfile(os.path.join(pkg_dir, file)):
            return False
    return True


def set_link(src, dst):
    """Links src to dst, but only if it's not ALREADY linked that way."""
    print('src=',src)
    print('dst=',dst)
    if os.path.islink(dst):
        if os.path.realpath(dst) == src:
            return
        os.remove(dst)
    os.symlink(src, dst)

def setup(parser, args, unknown_args):
    if len(unknown_args) > 0:
        raise ValueError('Unkown arguments: %s' % unknown_args)

    run_dir = rundir.resolve_fname(args.rundir)

    start_ts = None
    cold_end_ts = None
    end_ts = None
    if args.timespan is not None:
        tss = [parse_date(sdate.strip()) for sdate in args.timespan.split(',')]
        if len(tss) == 1:
            start_ts = tss[0]
        elif len(tss) == 2:
            start_ts = tss[0]
            cold_end_ts = tss[1]
            end_ts = tss[1]
        elif len(tss) == 3:
            start_ts = tss[0]
            cold_end_ts = tss[1]
            end_ts = tss[2]
        else:
            raise ValueError('Invalid timespan %s' % args.timespan)

    # ---------------

    # Get src, build and pkg directories the last time setup was run.
    # (None if they don't exist)
    old_run_deck = follow_link(os.path.join(run_dir, 'rundeck.R'), must_exist=True)
    old_src_dir = follow_link(os.path.join(run_dir, 'src'), must_exist=True)
    old_build_dir = follow_link(os.path.join(run_dir, 'build'))
    old_pkg_dir = follow_link(os.path.join(run_dir, 'pkg'))
    status = rundir.status(run_dir)

    print('-------- Old Configuration:')
    print('run_deck:   %s' % old_run_deck)
    print('src_dir:    %s' % old_src_dir)
    print('build_dir:  %s' % old_build_dir)
    print('pkg_dir:    %s' % old_pkg_dir)
    print('run status: %d' % status)

    old_rd = None
    if (old_run_deck is not None) and (old_src_dir is not None):
        old_rd = rundeck.load(old_run_deck, modele_root=old_src_dir)
#        old_build_hash = buildhash(old_rd, old_src_dir)
#        old_pkg_hash = pkghash(old_rd, old_src_dir)

    # ----- Determine the run_deck
    new_run_deck = os.path.abspath(args.rundeck)
    run_deck = new_run_deck or old_run_deck
    if run_deck is None:
        raise ValueError('No rundeck specified!')
    if (status > rundir.INITIAL) and (old_run_deck is not None) and (run_deck != old_run_deck):
        tty.warn('Rundeck changing from %s to %s', old_run_deck, run_deck)

    # -------- Determine the src_dir
    new_src_dir = args.src or pathutil.modele_root(run_deck)
    src_dir = new_src_dir or old_src_dir
    if src_dir is None:
        raise ValueError('No source directory specified!')
    if (status > rundir.INITIAL) and (old_src_dir is not None) and (src_dir != old_src_dir):
        raise ValueError('Cannot change src_dir to %s', src_dir)

    if not os.path.isdir(src_dir):
        raise ValueError('src_dir %s does not exist!' % src_dir)


    # ------ Read the rundeck and determine hashes
    rd = rundeck.load(run_deck, modele_root=src_dir)

    # ------ Determine build_dir; cannot change
    build_hash = buildhash(rd, src_dir)
    build_dir = os.path.join(ectl.root, 'builds', build_hash)
    if (status > rundir.INITIAL) and (old_build_dir is not None) and (build_dir != old_build_dir):
        raise ValueError('Cannot change build_dir to %s', build_dir)

    # ------ Determine pkg_dir
    pkg_hash = pkghash(rd, src_dir)
    pkg_dir = os.path.join(ectl.root, 'pkgs', pkg_hash)

    # ------ Re-build only if our pkg_dir is not good
    if not good_pkg_dir(pkg_dir):
        # number of jobs spack will to build with.
        jobs = multiprocessing.cpu_count()

        # Create the build dir if it doesn't already exist
        if not os.path.isdir(build_dir):
            os.makedirs(build_dir)
        os.chdir(build_dir)
        subprocess.check_call([os.path.join(src_dir, 'spconfig.py'),
            '-DRUN=%s' % run_deck,
            '-DCMAKE_INSTALL_PREFIX=%s' % pkg_dir,
            src_dir])
        subprocess.check_call(['make', 'install', '-j%d' % jobs])

    # ---- Create run_dir
    if not os.path.isdir(run_dir):
        os.makedirs(run_dir)

    # ------------------ Download input files
    rd.resolve(file_path=rundeck.default_file_path, download=True,
        download_dir=rundeck.default_file_path[0])

    # ---- Create data file symlinks and I file
    print('sss', start_ts, end_ts)
    if start_ts is not None:
        rd.set(('INPUTZ', 'START_TIME'), datetime.datetime(*start_ts))
    if cold_end_ts is not None:
        rd.set(('INPUTZ_cold', 'END_TIME'), datetime.datetime(*cold_end_ts))
    if end_ts is not None:
        rd.set(('INPUTZ', 'END_TIME'), datetime.datetime(*end_ts))
    rundir.make_rundir(rd, run_dir)

    # ---- Copy in original rundeck...
    rundeck_leafname = os.path.split(run_deck)[1]
    with open(os.path.join(run_dir, 'flat.R'), 'w') as fout:
        fout.write(''.join(rd.raw_rundeck))

    # ------------- Set directory symlinks
    set_link(run_deck, os.path.join(run_dir, 'rundeck.R'))
    set_link(src_dir, os.path.join(run_dir, 'src'))
    set_link(build_dir, os.path.join(run_dir, 'build'))
    set_link(pkg_dir, os.path.join(run_dir, 'pkg'))
