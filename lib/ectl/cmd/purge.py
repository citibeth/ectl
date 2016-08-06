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

description = 'Removes unused pkg and build directories.'

def setup_parser(subparser):
    pass

def follow_link(linkname, must_exist=False):
    if not os.path.exists(linkname):
        return None
    fname = os.path.realpath(linkname)
    if must_exist and not os.path.exists(fname):
        return None
    return fname

def purge(parser, args, unknown_args):
    if len(unknown_args) > 0:
        raise ValueError('Unkown arguments: %s' % unknown_args)

    # ------- Find used packages and builds
    used_pkgs = set()
    used_builds = set()
    runs_dir = os.path.join(ectl.root, 'runs')
    for run in os.listdir(runs_dir):
        run_dir = os.path.join(runs_dir, run)

        pkg_dir = follow_link(os.path.join(run_dir, 'pkg'), must_exist=True)
        if pkg_dir is not None:
            used_pkgs.add(os.path.split(pkg_dir)[1])

        build_dir = follow_link(os.path.join(run_dir, 'build'), must_exist=True)
        if build_dir is not None:
            used_builds.add(os.path.split(build_dir)[1])

    # ------- Remove unused...
    pkgs_dir = os.path.join(ectl.root, 'pkgs')
    for pkg in os.listdir(pkgs_dir):
        if pkg not in used_pkgs:
            print('Removing package: %s' % pkg)
            shutil.rmtree(os.path.join(pkgs_dir, pkg))

    builds_dir = os.path.join(ectl.root, 'builds')
    for build in os.listdir(builds_dir):
        if build not in used_builds:
            print('Removing build: %s' % build)
            shutil.rmtree(os.path.join(builds_dir, build))
