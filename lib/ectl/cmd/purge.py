from __future__ import print_function
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
import shutil
import datetime
import re

description = 'Inactivate unused pkg and build directories.  Delete pkg and build directories that were inactivated at least 2 weeks ago.'

def setup_parser(subparser):
    subparser.add_argument('run', nargs='?', default='.',
        help='Directory of run that will lead to an ectl config')
    subparser.add_argument('--ectl', action='store', dest='ectl',
        help='Root of ectl tree: ectl/runs, ectl/builds, ectl/pkgs')
    subparser.add_argument('--force', '-f', action='store_true', dest='force',
        help='Delete all unused builds and packages immediately')


def follow_link(linkname, must_exist=False):
    if not os.path.exists(linkname):
        return None
    fname = os.path.realpath(linkname)
    if must_exist and not os.path.exists(fname):
        return None
    return fname

def inactivate_unused(pkgs_dir, used_pkgs):
    today = datetime.date.today()
    stoday = '%04d%02d%02d' % (today.year, today.month, today.day)
    count = 0

    for pkg in os.listdir(pkgs_dir):
        if pkg[:2] == 'rm':
            continue
        if pkg in used_pkgs:
            continue

        old_name = os.path.join(pkgs_dir, pkg)
        if not os.path.isdir(old_name):
            continue

        version = 0
        while True:
            new_leaf = 'rm-{0}-{1}-{2}'.format(stoday, version, pkg)
            new_name = os.path.join(pkgs_dir, new_leaf)
            if not os.path.exists(new_name):
                break
            version += 1
        os.rename(old_name, new_name)
        count += 1
    return count

rmRE = re.compile(r'rm-(\d\d\d\d)(\d\d)(\d\d)-\d+-(.*)')
def delete_inactive(pkgs_dir, cutoff):
    count = 0
    for pkg in os.listdir(pkgs_dir):
        match = rmRE.match(pkg)
        if match is not None:
            inactive_date = datetime.date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            if inactive_date < cutoff:
                fname = os.path.join(pkgs_dir, pkg)
                shutil.rmtree(fname)
                count += 1
    return count

def purge(parser, args, unknown_args):
    if len(unknown_args) > 0:
        raise ValueError('Unkown arguments: %s' % unknown_args)

    config = ectl.config.Config(run=args.run)
    print('-------- Ectl Config:')
    print('    ectl:   %s' % config.ectl)
    print('    runs:   %s' % config.runs)
    print('    builds: %s' % config.builds)
    print('    pkgs:   %s' % config.pkgs)

    # Get all the runs in this 
    runs = rundir.all_rundirs([config.runs], recursive=True)
    #print('\n'.join(dir for dir,status in runs))

    # ------- Find used packages and builds
    used_pkgs = set()
    used_builds = set()

    for run_dir,_ in runs:
        pkg_dir = follow_link(os.path.join(run_dir, 'pkg'), must_exist=True)
        if pkg_dir is not None:
            used_pkgs.add(os.path.split(pkg_dir)[1])

        build_dir = follow_link(os.path.join(run_dir, 'build'), must_exist=True)
        if build_dir is not None:
            used_builds.add(os.path.split(build_dir)[1])


#    print('used_pkgs', used_pkgs)
#    print('used_builds', used_builds)

    today = datetime.date.today()
    if args.force:
        cutoff = today + datetime.timedelta(days=1)
    else:
        cutoff = today - datetime.timedelta(days=14)

    scutoff = '{:0>4d}-{:0>2d}-{:0>2d}'.format(cutoff.year, cutoff.month, cutoff.day)

    # ------- Inactivate unused and delete older inactivated packages...
    pkgs_dir = os.path.join(config.ectl, 'ectl', 'pkgs')
    n = inactivate_unused(pkgs_dir, used_pkgs)
    print('Renamed {0} packages, {1} remain active'.format(n, len(used_pkgs)))
    n = delete_inactive(pkgs_dir, cutoff)
    print('Deleted {0} packages inactivated before {1}'.format(n, scutoff))

    builds_dir = os.path.join(config.ectl, 'ectl', 'builds')
    n = inactivate_unused(builds_dir, used_builds)
    print('Renamed {0} builds, {1} remain active'.format(n, len(used_builds)))
    n = delete_inactive(builds_dir, cutoff)
    print('Deleted {0} builds inactivated before {1}'.format(n, scutoff))


