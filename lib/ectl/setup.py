from __future__ import print_function
import multiprocessing
import os
import hashlib
import argparse
import llnl.util.tty as tty
import ectl.util
import ectl
import ectl.cmd
import ectl.cdlparams
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
from giss import pyar, ioutil
import importlib
import netCDF4

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
    print('set_link', src, dst)
    if os.path.islink(dst):
        if os.path.abspath(os.path.realpath(dst)) == os.path.abspath(src):
            return
        os.remove(dst)
    src_rel = os.path.relpath(src, start=os.path.split(dst)[0])
    os.symlink(src_rel, dst)

cmakeRE = re.compile('(.*?)=(.*)')
def read_cmake_cache(fname):
    vars = {}
    try:
        with open(fname, 'r') as fin:
            for line in fin:
                line = line.partition('#')[0].rstrip()
                line = line.partition('//')[0].rstrip()
                match = cmakeRE.match(line)
                if match is not None:
                    vars[match.group(1)] = match.group(2)
    except:
        pass

    return vars

def setup(run, rundeck=None, src=None, pkgbuild=False, rebuild=False, jobs=None, unpack=True, python='python3', pythonpath=None):

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
    config_dir = os.path.join(args_run, 'config')
    rundeck_R = os.path.join(config_dir, 'rundeck.R')

    # The ModelE directory associated with our rundeck
    # If the rundeck is outside a ModelE directory, use
    # src instead.
    rundeck_src = pathutil.modele_root(rundeck) or src

    template_path = [os.path.join(rundeck_src, 'templates')]

    if not os.path.exists(config_dir):
        # Create a new rundeck.R
        try:
            os.makedirs(config_dir)
        except OSError:
            pass
        with ectl.util.working_dir(config_dir):
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

        with ectl.util.working_dir(config_dir):
            try:
                # ----- Check in changes from user
                git('checkout', 'user', echo=sys.stdout)    # Exception on the first command

                # Add all .cdl files
                cdls = [x for x in os.listdir('.') if x.endswith('.cdl')]
                if len(cdls) > 0:
                    git('add', *cdls)

                # Check in changes from user
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
            # Do not overwrite existing build files
            with ectl.util.working_dir(src):
                # if MODELE_CONTROL_PYAR does not exist, this might be an older branch
                # that had the build files already unpack.  Proceed under that assumption...
                if unpack and os.path.exists(MODELE_CONTROL_PYAR):
                    print('Adding files from modele-control.pyar')
                    print('      ', os.path.realpath(MODELE_CONTROL_PYAR))
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


                # Only run CMake if no Makefile.  (If Makefile is out
                # of date, CMake will automatically re-run with 'make'
                # command)
                cmake = read_cmake_cache(os.path.join(pkg, 'CMakeCache.txt'))
                run_cmake = ('CMAKE_INSTALL_PREFIX:PATH' not in cmake) \
                    or (cmake['CMAKE_INSTALL_PREFIX:PATH'] != pkg) \
                    or (not os.path.exists('Makefile')) \
                    or args_rebuild
                if run_cmake:
                    print('============ CMake')

                    # Read the shebang out of setup.py to get around 80-char limit
                    modele_setup_py = os.path.join(src, 'modele-setup.py')
                    env = dict(os.environ)
                    cmd = [python]   # From args
                    if pythonpath is not None:
                        env['PYTHONPATH'] = pythonpath

                    try:
                        cmd += [modele_setup_py,
                            '-DRUNDECK=%s' % rundeck_R,
                            '-DRUN=%s' % rundeck_R,    # Compatibility with old builds
                            '-DCMAKE_INSTALL_PREFIX=%s' % pkg,
                            src]
                        print('setup calling', cmd)
                        subprocess.check_call(cmd, env=env)
                    except OSError as err:
                        sys.stderr.write(' '.join(cmd) + '\n')
                        sys.stderr.write('%s\n' % err)
                        raise ValueError('Problem running %s.  Have you run spack setup on your source directory?' % os.path.join(src, 'modele-setup.py'))

                # Now that we have a makefile, run make!
                print('============ Make')
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
    download_dir = os.environ['MODELE_ORIGIN_DIR']
    good = ectl.cdlparams.resolve_cdls_in_dir(os.path.join(args_run, 'config'), download_dir=download_dir)

    rd.params.files.resolve(
        file_path=ectl.paths.default_file,
        download_dir=download_dir)

    if not good:
        raise Exception('Problem resolving one or more input filesnames')

    # ---- Create data file symlinks and I file
    # (Just so the user can see what it will be; this is
    # re-done in launch.py)
    rundir.make_rundir(rd, args_run)

    # ---- Run setup scripts...
    for fname in os.listdir(os.path.join(args_run, 'config')):
        if not fname.endswith('.nc'):
            continue

        # Obtain list of setup functions we need to call
        setup_fns = list()
        with netCDF4.Dataset(os.path.join(args_run, 'config', fname), 'r') as nc:
            setups = nc.variables['setups']
            for attr in setups.ncattrs():
                path = getattr(setups, attr).split('.')
                module = importlib.import_module('.'.join(path[:-1]))
                setup_fns.append(getattr(module, path[-1]))

        with ioutil.pushd(args_run):
            for setup_fn in setup_fns:
                setup_fn(args_run, rd)
