from __future__ import print_function
import multiprocessing
import os
import hashlib
import argparse
import llnl.util.tty as tty
import ectl
import ectl.cmd
from ectl import pathutil,rundir,xhash,srcdir,launchers
import ectl.config
import ectl.rundeck
from ectl.rundeck import legacy
import subprocess
import base64
import re
import datetime
import sys
from spack.util import executable
import pyar

MODELE_CONTROL_PYAR = 'modele-control.pyar'
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
    subparser.add_argument('--src', '-s', action='store', dest='src',
        help='Top-level directory of ModelE source')
    subparser.add_argument('--pkgbuild', action='store_true', dest='pkgbuild', default=False,
        help='Name package dir after build dir.')
    subparser.add_argument('--rebuild', action='store_true', dest='rebuild', default=False,
        help='Rebuild the package, even if it seems to be fine.')

    subparser.add_argument('--jobs', '-j', action='store', dest='jobs',
        help='Number of cores to use when building.')

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


    # ---------------
    # Get ectl directories
    config = ectl.config.Config(run=args.run)
    print('-------- Ectl Config:')
    print('    ectl:   %s' % config.ectl)
    print('    runs:   %s' % config.runs)
    print('    builds: %s' % config.builds)
    print('    pkgs:   %s' % config.pkgs)

    # Get src, build and pkg directories the last time setup was run.
    # (None if they don't exist)
    old = rundir.FollowLinks(args.run)
    status = rundir.Status(args.run)

    print('\nRun: %s' % args.run)
    print('-------- Old Setup:')
    print('    rundeck: %s' % old.rundeck)
#    print('    run:     %s' % old.run)
    print('    src:     %s' % old.src)
    print('    build:   %s' % old.build)
    print('    pkg:     %s' % old.pkg)
    print('    status:  %d' % status.status)

    # ----- Determine the rundeck
    new_rundeck = os.path.abspath(args.rundeck) if args.rundeck is not None else None
    rundeck = new_rundeck or old.rundeck
    if rundeck is None:
        raise ValueError('No rundeck specified!')
    if (status.status > launchers.INITIAL) and (old.rundeck is not None) and (rundeck != old.rundeck):
        raise ValueError('Cannot change rundeck (to %s)' % (rundeck))
#        tty.warn('Rundeck changing from %s to %s' % (old.rundeck, rundeck))

    # -------- Determine the src
    new_src = args.src or pathutil.modele_root(rundeck)
    src = new_src or old.src
    if src is None:
        raise ValueError('No source directory specified!')
    if (status.status > launchers.INITIAL) and (old.src is not None) and (src != old.src):
        raise ValueError('Cannot change src (to %s)' % src)

    if not os.path.isdir(src):
        raise ValueError('src %s does not exist!' % src)

    # ===========================================
    # Construct/merge the rundeck
    git = executable.which('git')

    # ----- Create the rundeck repo (if it doesn't already exist)
    print('========= BEGIN Rundeck Management')
    rundeck_dir = os.path.join(args.run, 'rundeck')
    rundeck_R = os.path.join(rundeck_dir, 'rundeck.R')

    # The ModelE directory associated with our rundeck
    # If the rundeck is outside a ModelE directory, use
    # src instead.
    rundeck_src = pathutil.modele_root(rundeck) or src

    template_path = [os.path.join(rundeck_src, 'templates')]
    if not os.path.exists(rundeck_dir):
        # Create a new rundeck.R
        try:
            os.makedirs(rundeck_dir)
        except OSError:
            pass
        os.chdir(rundeck_dir)

        git('init', echo=sys.stdout)
        git('checkout', '-b', 'upstream', echo=sys.stdout)

        # Copy the rundeck from original location (templates?)
        print('$ <generating {0}>'.format(rundeck_R))
        with open(rundeck_R, 'w') as fout:
            for line in legacy.preprocessor(rundeck, template_path):
                fout.write(line.raw)

        git('add', 'rundeck.R', echo=sys.stdout)
        git('commit', '-a', '-m', 'Initial commit from {0}'.format(rundeck), echo=sys.stdout)

        # Put it on the user branch (where we normally will reside)
        git('checkout', '-b', 'user', echo=sys.stdout)

    else:
        # Update/merge the rundeck
        # If there are unresolved conflicts, this will raise an exception

        os.chdir(rundeck_dir)
        try:
            # Check in changes from user
            git('checkout', 'user', echo=sys.stdout)    # Exception on the first command
            git('commit', '-a', '-m', 'Changes from user', echo=sys.stdout, fail_on_error=False)

            # Check in changes from upstream
            git('checkout', 'upstream', echo=sys.stdout)
            # Copy the rundeck from original location (templates?)
            with open(rundeck_R, 'w') as fout:
                for line in legacy.preprocessor(rundeck, template_path):
                    fout.write(line.raw)
            git('commit', '-a', '-m', 'Changes from upstream', echo=sys.stdout, fail_on_error=False)

            # Merge upstream changes into user
            git('checkout', 'user', echo=sys.stdout)
            git('merge', 'upstream', '-m', 'Merged changes', echo=sys.stdout)    # Will raise if merge needs help
        except:
            print('Error merging rundeck; do you have unresolved conflicts?')

            if 'EDITOR' in os.environ:
                EDITOR = os.environ['EDITOR'].split(' ')
                print('EDITOR', EDITOR)
                editor = executable.which(EDITOR[0])
                args = EDITOR[1:] + [rundeck_R]
                editor(*args, echo=sys.stdout)
            else:
                print('You need to edit the file to resolve conflicts:')
                print(rundeck_R)
            print('When you are done resolving conflicts, do:')
            print('    ectl merge {0}'.format(args.run))
            print('    ectl setup {0}'.format(args.run))


            sys.exit(1)
    print('========= END Rundeck Management')

    rd = ectl.rundeck.load(rundeck_R, modele_root=src)
    # =====================================

    # ------ Determine build; cannot change
    build_hash = buildhash(rd, src)
    build = os.path.join(config.builds, build_hash)
    if (status.status > launchers.INITIAL) and (old.build is not None) and (build != old.build):
        raise ValueError('Cannot change build to %s', build)

    # ------ Determine pkg
    pkgbuild = args.pkgbuild or old.pkgbuild
    if pkgbuild:
        pkg = os.path.join(config.pkgs, 'pkg-' + os.path.split(build)[1])
    else:
        pkg_hash = pkghash(rd, src)
        pkg = os.path.join(config.pkgs, pkg_hash)

    print('-------- New Setup:')
    print('    rundeck: %s' % rundeck)
    print('    src:     %s' % src)
    print('    build:   %s' % build)
    print('    pkg:     %s' % pkg)

    # ------------- Set directory symlinks
    set_link(rundeck, os.path.join(args.run, 'upstream.R'))
    set_link(rundeck_R, os.path.join(args.run, 'rundeck.R'))
    set_link(src, os.path.join(args.run, 'src'))
    set_link(build, os.path.join(args.run, 'build'))
    set_link(pkg, os.path.join(args.run, 'pkg'))


    # ------ Re-build only if our pkg is not good
    if args.rebuild or pkgbuild or (not good_pkg_dir(pkg)) or (old.pkg is None):

        try:

            # Unpack CMake build files if a modele-control.pyar file exists
            # If any of these files needs to change, we expect the user to
            # edit the pyar file.
            os.chdir(src)
            if os.path.exists(MODELE_CONTROL_PYAR):
                print('Adding files from modele-control.pyar')
                with open(MODELE_CONTROL_PYAR) as fin:
                    pyar.unpack_archive(fin, '.')

            if args.jobs is None:
                # number of jobs spack has to build with.
                jobs = multiprocessing.cpu_count()
            else:
                jobs = int(args.jobs)

            # Create the build dir if it doesn't already exist
            if not os.path.isdir(build):
                os.makedirs(build)
            os.chdir(build)

            # Read the shebang out of setup.py to get around 80-char limit
            spconfig_py = os.path.join(src, 'spconfig.py')
            cmd = []
            with open(spconfig_py, 'r') as fin:
                line = next(fin)
                if line[0:2] == '#!':
                    python = line[2:].strip()

                    # Make sure this looks like python, not something else
                    if python.index('python') != 0:
                        cmd.append(python)

            try:
                cmd += [spconfig_py,
                    '-DRUN=%s' % rundeck,
                    '-DCMAKE_INSTALL_PREFIX=%s' % pkg,
                    src]

                subprocess.check_call(cmd)
            except OSError as err:
                sys.stderr.write(' '.join(cmd) + '\n')
                sys.stderr.write('%s\n' % err)
                raise ValueError('Problem running %s.  Have you run spack setup on your source directory?' % os.path.join(src, 'spconfig.py'))
            subprocess.check_call(['make', 'install', '-j%d' % jobs])
        finally:
            # Remove files from modele-control.pyar
            os.chdir(src)
            if os.path.exists(MODELE_CONTROL_PYAR):
                print('Removing files from modele-control.pyar')
                with open(MODELE_CONTROL_PYAR) as fin:
                    for fname in pyar.list_archive(fin):
                        # print('Removing %s' % fname)
                        try:
                            os.remove(fname)
                        except OSError:
                            pass


    # ------------------ Download input files
    
    rd.resolve(file_path=ectl.rundeck.default_file_path, download=True,
        download_dir=ectl.rundeck.default_file_path[0])

    # ---- Create data file symlinks and I file
    # (Just so the user can see what it will be; this is
    # re-done in launch.py)
    rundir.make_rundir(rd, args.run)
