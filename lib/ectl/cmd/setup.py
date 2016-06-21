import multiprocessing
import os
import hashlib
import argparse
import llnl.util.tty as tty
import ectl
import ectl.cmd
from ectl import pathutil,rundir,xhash,srcdir
import ectl.config
import ectl.rundeck
from ectl.rundeck import legacy
import subprocess
import base64
import re
from ectl import iso8601
import datetime
import sys

description = 'Setup a ModelE run.'

def setup_parser(subparser):
#    subparser.add_argument(
#        'rundeck', nargs=1, help='Rundeck file use in setup.')
    subparser.add_argument('--ectl', action='store', dest='ectl',
        help='Root of ectl tree: ectl/runs, ectl/builds, ectl/pkgs')
    subparser.add_argument(
        'run', help='Directory of run to setup')
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
    """Like doing ln -s src dst"""
    if os.path.islink(dst):
        if os.path.abspath(os.path.realpath(dst)) == os.path.abspath(src):
            return
        os.remove(dst)
    src_rel = os.path.relpath(src, start=os.path.split(dst)[0])
    os.symlink(src_rel, dst)

def setup(parser, args, unknown_args):
    args.run = os.path.abspath(args.run)
    if len(unknown_args) > 0:
        raise ValueError('Unkown arguments: %s' % unknown_args)


    # Parse out timespan
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
    # Get ectl directories
    config = ectl.config.Config(rundeck=args.rundeck, run=args.run)
    print('-------- Ectl Config:')
    print('    ectl:   %s' % config.ectl)
    print('    runs:   %s' % config.runs)
    print('    builds: %s' % config.builds)
    print('    pkgs:   %s' % config.pkgs)

    # Get src, build and pkg directories the last time setup was run.
    # (None if they don't exist)
    old = rundir.FollowLinks(args.run)
    status = rundir.status(args.run)

    print('\nRun: %s' % args.run)
    print('-------- Old Setup:')
    print('    rundeck: %s' % old.rundeck)
#    print('    run:     %s' % old.run)
    print('    src:     %s' % old.src)
    print('    build:   %s' % old.build)
    print('    pkg:     %s' % old.pkg)
    print('    status:  %d' % status)

    # ----- Determine the rundeck
    new_rundeck = os.path.abspath(args.rundeck) if args.rundeck is not None else None
    rundeck = new_rundeck or old.rundeck
    if rundeck is None:
        raise ValueError('No rundeck specified!')
    if (status > rundir.INITIAL) and (old.rundeck is not None) and (rundeck != old.rundeck):
        raise ValueError('Cannot change rundeck (to %s)' % (rundeck))
#        tty.warn('Rundeck changing from %s to %s' % (old.rundeck, rundeck))

    # -------- Determine the src
    new_src = args.src or pathutil.modele_root(rundeck)
    src = new_src or old.src
    if src is None:
        raise ValueError('No source directory specified!')
    if (status > rundir.INITIAL) and (old.src is not None) and (src != old.src):
        raise ValueError('Cannot change src (to %s)' % src)

    if not os.path.isdir(src):
        raise ValueError('src %s does not exist!' % src)


    # ------ Read the rundeck and determine hashes

    # Load the system-provided rundeck
    rd = ectl.rundeck.load(rundeck, modele_root=src)

    # (Read most updated version of the rundeck...)
    try:
        # flat.R, as originally written from rundeck.R (not edited)
        rdf0 = ectl.rundeck.load(os.path.join(args.run, 'flat0.R'), template_path=[])
        # flat.R, possibly edited
        rdf = ectl.rundeck.load(os.path.join(args.run, 'flat.R'), template_path=[])

        # Merge anything changes in flat.R into the newly-read main rundeck.
        print('----- Merging rundecks')
        processed_keys = set()
        for key,param in rdf.params.items():
            processed_keys.add(key)
            try:
                param0 = rdf0.params[key]
                # Key in rdf0 and rdf
                # See if it's changed...
                if (param0.value != param.value) and (key in rd.params):
                    print('    {}: {} -> {}'.format(key, rd.params[key].value, param.value))
                    rd.set(key, param.value, line=param.line)
            except KeyError:
                # Key in rdf but not rdf0
                # Set in rundeck as well
                    print('    {}: {}'.format(key, param.value))
                    rd.set(key, param.value, line=param.line)

        # Mention keys that were in rdf0 and now on longer in rdf
        for key0,param0 in rdf0.params.items():
            if key0 in processed_keys:
                continue
            del rd.params[key0]
            print('    {}: (REMOVED)'.format(key0))

    except IOError as e:
        print(e)
        print('    Cannot read flat.R or flat0.R; not merging rundecks.')
        pass


    # Create flat0.R (original rundeck) if the file doesn't yet exist.
    fname = os.path.join(args.run, 'flat0.R')
    if not os.path.exists(fname):
        with open(fname, 'w') as out:
            for line in rd.legacy.lines:
                out.write(line)

    # ------ Determine build; cannot change
    build_hash = buildhash(rd, src)
    build = os.path.join(config.builds, build_hash)
    if (status > rundir.INITIAL) and (old.build is not None) and (build != old.build):
        raise ValueError('Cannot change build to %s', build)

    # ------ Determine pkg
    pkg_hash = pkghash(rd, src)
    pkg = os.path.join(config.pkgs, pkg_hash)

    print('-------- New Setup:')
    print('    rundeck: %s' % rundeck)
    print('    src:     %s' % src)
    print('    build:   %s' % build)
    print('    pkg:     %s' % pkg)

    # ------ Re-build only if our pkg is not good
    if not good_pkg_dir(pkg):
        # number of jobs spack will to build with.
        jobs = multiprocessing.cpu_count()

        # Create the build dir if it doesn't already exist
        if not os.path.isdir(build):
            os.makedirs(build)
        os.chdir(build)
        subprocess.check_call([os.path.join(src, 'spconfig.py'),
            '-DRUN=%s' % rundeck,
            '-DCMAKE_INSTALL_PREFIX=%s' % pkg,
            src])
        subprocess.check_call(['make', 'install', '-j%d' % jobs])

    # ---- Create args.run
    if not os.path.isdir(args.run):
        os.makedirs(args.run)

    # ------------------ Download input files
    
    rd.resolve(file_path=ectl.rundeck.default_file_path, download=True,
        download_dir=ectl.rundeck.default_file_path[0])

    # ---- Create data file symlinks and I file
    if start_ts is not None:
        rd.set(('INPUTZ', 'START_TIME'), datetime.datetime(*start_ts))
    if cold_end_ts is not None:
        rd.set(('INPUTZ_cold', 'END_TIME'), datetime.datetime(*cold_end_ts))
    if end_ts is not None:
        rd.set(('INPUTZ', 'END_TIME'), datetime.datetime(*end_ts))
    rundir.make_rundir(rd, args.run)

    # Write flat.R, the rundeck we are setting up
    with open(os.path.join(args.run, 'flat.R'), 'w') as out:
        rd.write(out)

    # ---- Copy in original rundeck...
#    rundeck_leafname = os.path.split(rundeck)[1]
#    with open(os.path.join(args.run, 'flat.R'), 'w') as fout:
#        fout.write(''.join(rd.raw_rundeck))
#    flat0_fname = os.path.join(args.run, 'flat0.R')
#    if not os.path.exists(flat0_fname):
#        with open(flat0_fname, 'w') as fout:
#            fout.write(''.join(rd.raw_rundeck))

    # ------------- Set directory symlinks
    set_link(rundeck, os.path.join(args.run, 'rundeck.R'))
    set_link(src, os.path.join(args.run, 'src'))
    set_link(build, os.path.join(args.run, 'build'))
    set_link(pkg, os.path.join(args.run, 'pkg'))
