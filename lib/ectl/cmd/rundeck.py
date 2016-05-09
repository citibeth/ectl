import multiprocessing
import os
import hashlib
import argparse
import llnl.util.tty as tty
import ectl
import ectl.cmd
from ectl import pathutil,rundeck,rundir,xhash
import subprocess

description = 'Setup a ModelE run.'

def setup_parser(subparser):
    subparser.add_argument(
        'rundeck', nargs=1, help='Rundeck file use in setup.')
    subparser.add_argument(
        'rundir', nargs=1, help='Directory of run to setup (inside ectl)')

def setup(parser, args):
    if len(args.rundeck) != 1:
        tty.die('setup requires one rundeck, %d given.' % len(args.rundeck))

    run_dir = os.path.join(ectl.root, 'runs', args.rundir[0])

    # We can fancify rundeck resolution later.
    # For now, you must specify full path.
    rundeck_fname = args.rundeck[0]
    print('Loading rundeck %s' % rundeck_fname)
    modele_root = pathutil.modele_root(rundeck_fname)
    rd = rundeck.load(rundeck_fname, modele_root=modele_root)

    hash = hashlib.md5()
    xhash.update(rd, hash)
    xhash.update(modele_root, hash)    # Source directory
    build_hash = hash.hexdigest()

    # -------------------- Build the source code
    # number of jobs spack will to build with.
    jobs = multiprocessing.cpu_count()

    stage_dir = os.path.join(ectl.root, 'builds', build_hash)
    # Create the build dir if it doesn't already exist
    if not os.path.isdir(stage_dir):
        os.makedirs(stage_dir)
    os.chdir(stage_dir)
    subprocess.check_call([os.path.join(modele_root, 'spconfig.py'),
        '-DRUN=%s' % rundeck_fname,
        '-DCMAKE_INSTALL_PREFIX=%s' % run_dir,
        modele_root])
    subprocess.check_call(['make', '-j%d' % jobs])


    # ------------------ Setup run_dir

    # ---- Create run directory
    if not os.path.isdir(run_dir):
        os.makedirs(run_dir)

    # ---- Symlink modelexe into it
    run_modelexe = os.path.join(run_dir, 'modelexe')
    if os.path.islink(run_modelexe):
        os.remove(run_modelexe)
    os.symlink(os.path.join(stage_dir, 'build', 'model', 'modelexe'), run_modelexe)

    # ---- Create data file symlinks and I file
    rundir.make_rundir(rd, run_dir)

    # ---- Copy in original rundeck...
    # (TODO)

