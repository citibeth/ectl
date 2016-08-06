import ectl
import ectl.rundeck

import re
import sys
import os
import string
import tempfile
import filecmp
import shutil
from ectl import pathutil
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
psRE = re.compile(r'[^\s]+\s+([0-9]+)\s+.*')
class MPILauncher(object):
    def __init__(self, run):
        self.run = os.path.abspath(run)

    def __call__(self, mpi_cmd, modele_cmd, np=None, time=None):
        """time:
            Max time to run (ignored)"""
        mpi_cmd = copy.copy(mpi_cmd)
        os.chdir(self.run)

        # --------- determine number of processors to use
        np = int(np) if np is not None else detect_ncores()
        mpi_cmd.extend(['-np', str(np)])

        # --------- Write out our launch
        modele_pid = os.path.join(self.run, 'modele.pid')
        try:
            os.remove(modele_pid)
        except:
            pass
        mpi_cmd.extend(['--report-pid', modele_pid])
        with open(os.path.join(self.run, 'launch.txt'), 'w') as out:
            out.write('launcher=mpi\n')
            out.write('pidfile={}\n'.format(modele_pid))
            out.write('mpi_cmd={}\n'.format(' '.join(mpi_cmd)))
            out.write('modele_cmd={}\n'.format(' '.join(modele_cmd)))
            out.write('cwd={}\n'.format(os.getcwd()))

        print(' '.join(mpi_cmd + modele_cmd))

        # See: http://stackoverflow.com/questions/29661527/how-to-spawn-detached-background-process-on-linux-in-either-bash-or-python

        # This works so easily because mpirun writes out its own PID
        # file.  If mpirun did not, then we'd need to do more complex
        # daemonization stuff.  For example:
        #      https://github.com/thesharp/daemonize
        cmd = ['nohup'] + mpi_cmd + modele_cmd
        subprocess.Popen(cmd)

    def wait(self, n=5):
        """Waits till we think we're really running"""
        modele_pid = os.path.join(self.run, 'modele.pid')
        for i in range(0,n):
            if os.path.exists(modele_pid):
                return
            time.sleep(1)
        

    def _top_pid(self):
        """Returns PID of the top-level process (the mpirun)"""
        with open(os.path.join(self.status.run, 'modele.pid'), 'r') as fin:
            return int(next(fin))

    def kill(self):
        """Kills running jobs."""

        # For now, we only know how to stop mpirun jobs
        pid = self._top_pid()
        try:
            os.kill(pid, signal.SIGKILL) # SIGKILL=9
            sys.stderr.write('Process %d successfully killed\n' % pid)
        except OSError:
            sys.stderr.write('Process %d seems to be already dead\n' % pid)

    def ps(self, out):
        """Shows processes currently running."""
        top_pid = self._top_pid()
        try:
            sub_pids = re.split('\s+', subprocess.check_output(['pgrep', '-P', str(top_pid)]))

            pids = set([top_pid] + [int(x) for x in sub_pids if len(x) > 0])

            cmd = ['ps', 'aux']
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            out.write(next(proc.stdout))
            for line in proc.stdout:
                match = psRE.match(line)
                if match is not None:
                    pid = int(match.group(1))
                    if pid in pids:
                        out.write(line)
#                print(match.group(1))
#                print(line)
#            out.write('sub-pids: {}\n'.format(pids))
        except subprocess.CalledProcessError:
            out.write('<No Running Processes>\n')


# --------------------------------------------------------------------
def new_launcher(run, slauncher):
    """Launcher factory."""

    # Different kinds of Slurm profiles
    if slauncher.find('slurm') == 0:
        # Starts with 'slurm'...
        if slauncher[5] == '-':
            profile = slauncher[6:]
        else:
            profile = None
        launcher = SlurmLauncher(profile=profile)

    elif slauncher == 'mpi':
        launcher = MPILauncher(run)

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

NONE=0
INITIAL=1
RUNNING=2
STOPPED=3
FINISHED=4
_status_str = ['NONE', 'INITIAL', 'RUNNING', 'STOPPED', 'FINISHED']

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
            RUNNING: A process is actively running it
            STOPPED: In the middle of a run, but nothing running
            FINISHED: No more runs possible (rsf vs fort.1.nc?)."""

        self.run = run_dir
        self.launch_list = read_launch_txt(self.run)
        self.launch = None if self.launch_list is None else dict(self.launch_list)
        self.status = self._get_status()

    @property
    def sstatus(self):
        return _status_str[self.status]

    def new_launcher(self):
        if self.launch is None:
            return None

        launcher = new_launcher(self.run, self.launch['launcher'])
        launcher.status = self
        return launcher

    def _get_status(self):
        # Make sure the run has been set up.
        if not os.path.exists(self.run):
            return NONE
        if not os.path.exists(os.path.join(self.run, 'I')):
            return NONE

        try:
            files = set(os.listdir(self.run))
        except:
            return INITIAL    # The dir doesn't even exist!

        if self.launch is not None:
            # See if we're still running
            if self.launch['launcher'] == 'mpi':
                with open(self.launch['pidfile'], 'r') as fin:
                    pid = int(next(fin))
                    try:
                        os.kill(pid, 0)
                        return RUNNING
                    except OSError:
                        pass

        # First, check for any netCDF files.  If there are NO such files,
        # then we've never run.
        has_nc = False

        fort_files = ('fort.1.nc' in files) or ('fort.2.nc' in files)

        if fort_files:
            return STOPPED

        acc_files = False
        for file in files:
            if accRE.match(file) != None:
                acc_files = True
                break

        if acc_files:
            return FINISHED

        return INITIAL
