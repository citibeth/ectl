from __future__ import print_function
import multiprocessing
import os
import hashlib
import argparse
import llnl.util.tty as tty
import ectl.util
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


def setup(run, rundeck=None, src=None, pkgbuild=False, rebuild=False, jobs=None):

    # Move parameters to different name to maintain SSA coding style below.
    args_run = run
    args_rundeck = rundeck
    args_src = src
    args_pkgbuild = pkgbuild
    args_rebuild = rebuild
    args_jobs = jobs

    args_run = os.path.abspath(args_run)


    # ---------------
    # Get ectl directories
    config = ectl.config.Config(run=run)
    print('-------- Ectl Config:')
    print('    ectl:   %s' % config.ectl)
    print('    runs:   %s' % config.runs)
    print('    builds: %s' % config.builds)
    print('    pkgs:   %s' % config.pkgs)

    # Get src, build and pkg directories the last time setup was run.
    # (None if they don't exist)
    old = rundir.FollowLinks(run)
    status = rundir.Status(run)

    print('\nRun: %s' % run)
    print('-------- Old Setup:')
    print('    rundeck: %s' % old.rundeck)
#    print('    run:     %s' % old.run)
    print('    src:     %s' % old.src)
    print('    build:   %s' % old.build)
    print('    pkg:     %s' % old.pkg)
    print('    status:  %d' % status.status)

    # ----- Determine the rundeck
    new_rundeck = os.path.abspath(args_rundeck) if args_rundeck is not None else None
    print('args_rundeck', args_rundeck)
    print('new_rundeck', new_rundeck)

    rundeck = new_rundeck or old.rundeck
    if rundeck is None:
        raise ValueError('No rundeck specified!')
    if (status.status > launchers.INITIAL) and (old.rundeck is not None) and (rundeck != old.rundeck):
        raise ValueError('Cannot change rundeck (to %s)' % (rundeck))
#        tty.warn('Rundeck changing from %s to %s' % (old.rundeck, rundeck))

    # -------- Determine the src
    new_src = args_src or pathutil.modele_root(rundeck)
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
    rundeck_dir = os.path.join(args_run, 'rundeck')
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
        with ectl.util.working_dir(rundeck_dir):
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

        with ectl.util.working_dir(rundeck_dir):
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
                print('    ectl merge {0}'.format(args_run))
                print('    ectl setup {0}'.format(args_run))


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
    pkgbuild = args_pkgbuild or old.pkgbuild
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
    set_link(rundeck, os.path.join(args_run, 'upstream.R'))
    set_link(rundeck_R, os.path.join(args_run, 'rundeck.R'))
    set_link(src, os.path.join(args_run, 'src'))
    set_link(build, os.path.join(args_run, 'build'))
    set_link(pkg, os.path.join(args_run, 'pkg'))


    # ------ Re-build only if our pkg is not good
    if args_rebuild or pkgbuild or (not good_pkg_dir(pkg)) or (old.pkg is None):

        try:

            # Unpack CMake build files if a modele-control.pyar file exists
            # If any of these files needs to change, we expect the user to
            # edit the pyar file.
            with ectl.util.working_dir(src):
                if os.path.exists(MODELE_CONTROL_PYAR):
                    print('Adding files from modele-control.pyar')
                    with open(MODELE_CONTROL_PYAR) as fin:
                        pyar.unpack_archive(fin, '.')

                if args_jobs is None:
                    # number of jobs spack has to build with.
                    jobs = multiprocessing.cpu_count()
                else:
                    jobs = args_jobs

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
            if False:
                # Remove files from modele-control.pyar
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
    rundir.make_rundir(rd, args_run)
