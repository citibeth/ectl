import ectl
import ectl.rundeck

import re
import sys
import os
import string
import tempfile
import filecmp
import shutil
from ectl import pathutil, launchers
import ectl.config
import copy
import subprocess
import signal
import StringIO
import time

# TODO: Be careful not to leave around zero-length files when downloading

# =====================================================================
# http://stackoverflow.com/questions/12902008/python-how-to-find-out-whether-hyperthreading-is-enabled
cpusRE = re.compile(r'CPU\(s\):\s*(.*)')
threadsRE = re.compile(r'Thread\(s\) per core:\s*(.*)')
def detect_ncores():
    buf = StringIO.StringIO()
    p = subprocess.Popen('lscpu', stdout=subprocess.PIPE)
    output = p.stdout.read()
    p.wait()
    for line in output.split('\n'):
        match = cpusRE.match(line)
        if match is not None:
            cpus = int(match.group(1))
        else:
            match = threadsRE.match(line)
            if match is not None:
                threads = int(match.group(1))
    return cpus // threads

def detect_mpi(pkg):
    """Detects the MPI library being used, given the pkg directory.
    This will be done by running `ldd modelexe`"""
    return 'openmpi'

# --------------------------------------------------------------------

# --------------------------------------------------------------------
slurmRE = re.compile('slurm(-(.+))?')
def new_launcher(run, slauncher):
    """Launcher factory."""

    # Different kinds of Slurm profiles
    match = slurmRE.match(slauncher)
    if match is not None:
        profile = None
        if match.group(2) is not None:
            profile = match.group(2)
        launcher = launchers.SlurmLauncher(run, profile=profile)

    elif slauncher == 'mpi':
        launcher = launchers.MPILauncher(run)

    else:
        raise ValueError('Unrecognized launcher: {}'.format(slauncher))

    return launcher
#    launcher = getattr(sys.modules[__name__], 'Launcher_' + args.launcher)()

# =====================================================================


# --------------------------------------
class FollowLinks(object):
    """Reads links from an existing run directory.  If the links don't
    exist, or if the entire directory doesn't exist, sets to None."""

    def __init__(self, run):
        self.run = os.path.abspath(run)
        self.rundeck = pathutil.follow_link(
            os.path.join(run, 'upstream.R'), must_exist=True)
        self.src = pathutil.follow_link(
            os.path.join(run, 'src'), must_exist=True)
        self.build = pathutil.follow_link(
            os.path.join(run, 'build'))
        self.pkg = pathutil.follow_link(
            os.path.join(run, 'pkg'))

        # Determine if pkgbuild was set before
        self.pkgbuild = \
            (self.pkg is not None) and \
            (os.path.split(self.pkg)[1].find('-') >= 0)

    def dump(self, out=sys.stdout, prefix=''):
        out.write('%srun:     %s\n' % (prefix, self.run))
        out.write('%srundeck: %s\n' % (prefix, self.rundeck))
        out.write('%ssrc:     %s\n' % (prefix, self.src))
        out.write('%sbuild:   %s\n' % (prefix, self.build))
        out.write('%spkg:     %s\n' % (prefix, self.pkg))


def write_I(preamble, sections, fname):
    with open(fname, 'w') as out:
        out.write(preamble[0].raw)    # First line of preamble
        out.write('\n')

        out.write('&&PARAMETERS\n')
        out.write('\n'.join(sections.parameters))
        out.write('\n')
        out.write('\n'.join(sections.data_lines))
        out.write('\n&&END_PARAMETERS\n')

        out.write('\n&INPUTZ\n')
        out.write('\n'.join(sections.inputz))
        out.write('\n/\n\n')

        out.write('&INPUTZ_cold\n')
        out.write('\n'.join(sections.inputz_cold))
        out.write('\n/\n')


def make_rundir(rd, rundir):
    ret = True

    sections = ectl.rundeck.ParamSections(rd)

    # ------- Make the rundir
    try:
        os.makedirs(rundir)
    except OSError:
        pass
    try:
        os.remove(os.path.join(rundir, 'I'))
    except OSError:
        pass

    # -------- Remove old symlinks
    for label, fname in sections.data_files:
        try:
            os.remove(os.path.join(rundir, label))
        except OSError:
            pass

    # -------- Link data files
    for label, fname in sections.data_files:
        os.symlink(fname, os.path.join(rundir, label))

    # Write them out to the I file
    write_I(rd.preamble, sections, os.path.join(rundir, 'I'))


def read_launch_txt(run):
    """Reads the `key=value` entries of launch.txt into a dict."""
    launch_txt = os.path.join(run, 'launch.txt')
    launch_list = list()
    if not os.path.exists(launch_txt):
        return None

    # Read launch_list
    with open(launch_txt, 'r') as fin:
        for line in fin:
            equals = line.index('=')
            key = line[:equals].strip()
            val = line[equals+1:].strip()
            launch_list.append((key, val))
    return launch_list


accRE = re.compile('(.*?)\.acc(.*?)\.nc')
class Status(object):
    """Gets current status of a run."""
    def __init__(self, run_dir):
        """Determines whether a run directory is:
            NONE: Run has not been set up yet
            INITIAL: Run not yet begun
            QUEUED: Queued in a batch system but not yet running
            RUNNING: A process is actively running it
            STOPPED: In the middle of a run, but nothing running
            FINISHED: No more runs possible (rsf vs fort.1.nc?)."""

        self.run = run_dir
        self.launch_list = read_launch_txt(self.run)
        self.launch_txt = None if self.launch_list is None else dict(self.launch_list)
        self.status = self._get_status()

    @property
    def sstatus(self):
        return launchers._status_str[self.status]

    def new_launcher(self):
        if self.launch_txt is None:
            return None
        if 'launcher' not in self.launch_txt:
            return None

        launcher = new_launcher(self.run, self.launch_txt['launcher'])
        launcher.status = self
        return launcher

    def _get_status(self):
        # Make sure the run has been set up.
        if not os.path.exists(self.run):
            return launchers.NONE
        if not os.path.exists(os.path.join(self.run, 'I')):
            return launchers.NONE

        try:
            files = set(os.listdir(self.run))
        except:
            return launchers.INITIAL    # The dir doesn't even exist!

        status = None

        launcher = self.new_launcher()
        if launcher is not None:
            status = launcher.get_status(self.launch_txt)
            if status is not None:
                return status

        # First, check for any netCDF files.  If there are NO such files,
        # then we've never run.
        has_nc = False

        fort_files = ('fort.1.nc' in files) or ('fort.2.nc' in files)

        if fort_files:
            return launchers.STOPPED

        acc_files = False
        for file in files:
            if accRE.match(file) != None:
                acc_files = True
                break

        if acc_files:
            return launchers.FINISHED

        return launchers.INITIAL
# ---------------------------------------------------
def walk_rundirs(top, doruns):
    status = ectl.rundir.Status(top)
    if status.status == launchers.NONE:
        for sub in os.listdir(top):
            subdir = os.path.join(top, sub)
            if os.path.isdir(subdir):
                walk_rundirs(subdir, doruns)
    else:
        doruns.append((top,status))

def all_rundirs(runs, recursive=False):
    """Used for `ectl ps` and `ectl purge`"""

    if len(runs) == 0:
        runs = [os.path.abspath('.')]
    else:
        runs = [os.path.abspath(run) for run in runs]

    if (not recursive) and (len(runs) == 1):
        # Auto-recurse if a single given dir is not a run dir
        status = ectl.rundir.Status(runs[0])
        if status.status ==  launchers.NONE:
            recursive = True

    # ------- Get list of runs to do
    if recursive:
        doruns = list()
        for top_run in runs:
            walk_rundirs(top_run, doruns)
    else:
        doruns = [(run, ectl.rundir.Status(run)) for run in runs]

    return  doruns
