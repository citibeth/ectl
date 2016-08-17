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
import datetime
import sys
from spack.util import executable

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
    if (status.status > rundir.INITIAL) and (old.rundeck is not None) and (rundeck != old.rundeck):
        raise ValueError('Cannot change rundeck (to %s)' % (rundeck))
#        tty.warn('Rundeck changing from %s to %s' % (old.rundeck, rundeck))

    # -------- Determine the src
    new_src = args.src or pathutil.modele_root(rundeck)
    src = new_src or old.src
    if src is None:
        raise ValueError('No source directory specified!')
    if (status.status > rundir.INITIAL) and (old.src is not None) and (src != old.src):
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
        print('$ <generating {}>'.format(rundeck_R))
        with open(rundeck_R, 'w') as fout:
            for line in legacy.preprocessor(rundeck, ectl.rundeck.default_template_path):
                fout.write(line.raw)

        git('add', 'rundeck.R', echo=sys.stdout)
        git('commit', '-a', '-m', 'Initial commit from {}'.format(rundeck), echo=sys.stdout)

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
                for line in legacy.preprocessor(rundeck, ectl.rundeck.default_template_path):
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
            print('    ectl merge {}'.format(args.run))
            print('    ectl setup {}'.format(args.run))


            sys.exit(1)
    print('========= END Rundeck Management')

    rd = ectl.rundeck.load(rundeck_R, modele_root=src)
    # =====================================

    # ------ Determine build; cannot change
    build_hash = buildhash(rd, src)
    build = os.path.join(config.builds, build_hash)
    if (status.status > rundir.INITIAL) and (old.build is not None) and (build != old.build):
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
        if args.jobs is None:
            # number of jobs spack has to build with.
            jobs = multiprocessing.cpu_count()
        else:
            jobs = int(args.jobs)

        # Create the build dir if it doesn't already exist
        if not os.path.isdir(build):
            os.makedirs(build)
        os.chdir(build)
        subprocess.check_call([os.path.join(src, 'spconfig.py'),
            '-DRUN=%s' % rundeck,
            '-DCMAKE_INSTALL_PREFIX=%s' % pkg,
            src])
        subprocess.check_call(['make', 'install', '-j%d' % jobs])

    # ------------------ Download input files
    
    rd.resolve(file_path=ectl.rundeck.default_file_path, download=True,
        download_dir=ectl.rundeck.default_file_path[0])

    # ---- Create data file symlinks and I file
    # (Just so the user can see what it will be; this is
    # re-done in launch.py)
    rundir.make_rundir(rd, args.run)
