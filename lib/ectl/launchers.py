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
from six import StringIO
import time
import ectl.util

NONE=0
INITIAL=1
QUEUED=2
RUNNING=3
STOPPED=4
FINISHED=5
_status_str = ['NONE', 'INITIAL', 'QUEUED', 'RUNNING', 'STOPPED', 'FINISHED']

class ExitReason(object):
    UNKNOWN=0
    FINISHED_TIME=1
    USER_STOPPED=2
    MAX_WTIME=3
    SIGNAL_15=4
    _strs = ['UNKNOWN', 'FINISHED_TIME', 'USER_STOPPED', 'MAX_WTIME', 'SIGNAL_15']
    @staticmethod
    def str(ix):
        return ExitReason._strs[ix]


# --------------------------------------------------------
# http://stackoverflow.com/questions/12902008/python-how-to-find-out-whether-hyperthreading-is-enabled
cpusRE = re.compile(r'CPU\(s\):\s*(.*)')
threadsRE = re.compile(r'Thread\(s\) per core:\s*(.*)')
def detect_ncores():
    buf = StringIO()
    p = subprocess.Popen('lscpu', stdout=subprocess.PIPE)
    output = p.stdout.read()
    p.wait()
    for line in output.split(b'\n'):
        line = line.decode()
        match = cpusRE.match(line)
        if match is not None:
            cpus = int(match.group(1))
        else:
            match = threadsRE.match(line)
            if match is not None:
                threads = int(match.group(1))
    return cpus // threads
# --------------------------------------------------------
notFoundRE = re.compile(r'.*?=>\s+not found.*')
def check_ldd(exe_fname):
    """Using ldd, checks that a binary can load."""

    errors = list()

    # Find all libraries that won't load
    cmd = ['ldd', exe_fname]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    nstderr = 0
    for line in proc.stderr:
        line = line.decode()    # Convert bytes --> str
        sys.stderr.write(line)
        nstderr += 1

    if nstderr > 0:
        sys.stderr.write('Problems loading: {0}\n'.format(exe_fname))
        raise EnvironmentError('Cannot load ELF binary, does it exist?')


    for line in proc.stdout:
        line = line.decode()    # Convert bytes --> str
        match = notFoundRE.match(line)
        if match is not None:
            errors.append(line)

    # Print errors, if found
    if len(errors) > 0:
        sys.stderr.write('Problems loading: {0}\n'.format(exe_fname))
        for line in errors:
            sys.stderr.write(line)
        raise EnvironmentError('Cannot load ELF binary.  Have you loaded required environment modules?'.format(exe_fname))

    return
# --------------------------------------------------------------------
# Translation from Slurm states to ectl states
slurm_state_translation = {
    'RUNNING' : RUNNING,
    'PENDING' : QUEUED,
    'CANCELLED' : STOPPED,    # User cancelled, we don't care
    'FAILED' : STOPPED,    # Non-zero exit code, we don't care
    'COMPLETED' : STOPPED
}

scontrolRE=re.compile('([^\s=]+)=([^\s]+)')
def parse_scontrol(scontrol_txt):
    """Parses output of scontrol into {key : value} dict"""
    ret = dict()
    for match in scontrolRE.finditer(scontrol_txt):
        ret[match.group(1)] = match.group(2)
    return ret
# --------------------------------------------------------------------
# Convenient Slurm commands:
# https://rc.fas.harvard.edu/resources/documentation/convenient-slurm-commands/

legal_profiles = {None, 'debug'}

submittedRE = re.compile(r'Submitted batch job\s+(\d+)\s*')
invalidJobRE = re.compile(r'.*?Invalid job id specified.*')
class SlurmLauncher(object):

    def __init__(self, run, profile=None, np=None):
        self.run = os.path.abspath(run)
        if profile not in legal_profiles:
            raise ValueError('Illegal profile for SlurmLauncher: {0}'.format(profile))
        self.profile = profile
        self.np = np

    def __call__(self, mpi_cmd, modele_cmd, time=None, synchronous=False):
        if synchronous:
            raise ValueError('SlurmLauncher does not currently support synchronous=True')

        if self.np is None:
            raise ValueError('Must specify number of MPI tasks when using Slurm')

        if time is None:
            raise ValueError('Must specify length of time to run when using Slurm')


        mpi_cmd = copy.copy(mpi_cmd)
        with ectl.util.working_dir(self.run):

            # --------- Write out our launch

            check_ldd(modele_cmd[0])

            # See: http://stackoverflow.com/questions/29661527/how-to-spawn-detached-background-process-on-linux-in-either-bash-or-python

            cmd_str = ' '.join(mpi_cmd + modele_cmd)
            sbatch_cmd = ['sbatch',
                '--constraint=hasw',    # See below:  Differences in debug QoS? ISSUE=58192
                '--job-name={0}'.format(self.run), 
                '--account=s1001',
                '--ntasks={0}'.format(str(self.np)),
                '--time={0}'.format(time)]    # 1 minute

            if self.profile == 'debug':
                sbatch_cmd.append('--qos=debug')

            proc = subprocess.Popen(sbatch_cmd,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            batch_script = '\n'.join([
                '#!/bin/sh',
                '#',
                '',
                cmd_str])
            (sout, serr) = proc.communicate(batch_script.encode())
            if len(serr) > 0:
                print(' '.join(sbatch_cmd))
                print('------------------------------------------')
                print(batch_script)
                print('------------------------------------------')
                sys.stdout.flush()
                raise IOError(serr.decode())

            match = submittedRE.match(sout.decode())
            sjobid = match.group(1)

            # Write the launch file
            with open(os.path.join(self.run, 'launch.txt'), 'w') as out:
                if self.profile is None:
                    slauncher = 'slurm'
                else:
                    slauncher = 'slurm-{0}'.format(self.profile)
                out.write('launcher={0}\n'.format(slauncher))
                out.write('jobid={0}\n'.format(sjobid))
                out.write('mpi_cmd={0}\n'.format(' '.join(mpi_cmd)))
                out.write('modele_cmd={0}\n'.format(' '.join(modele_cmd)))
                out.write('cwd={0}\n'.format(os.getcwd()))

    def get_status(self, launch_txt):
        cmd = ['scontrol', 'show', 'jobid', '-dd', launch_txt['jobid']]
        (scontrol_txt, scontrol_err) = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
        # Invalid Job ID: This job is long gone...
        if invalidJobRE.match(scontrol_err.decode()) is not None:
            return None
        scontrol_dict = parse_scontrol(scontrol_txt.decode())

        JobState = scontrol_dict['JobState']    
        return slurm_state_translation.get(JobState, None)

    def wait(self, n=5):
        """Waits till we think we're really running"""
        # Once slurm received our job, we really are running
        # (or at least queued)

    def kill(self, launch_txt):
        cmd = ['scancel', launch_txt['jobid']]
        subprocess.call(cmd)

    def ps(self, launch_txt, out):
        cmd = ['scontrol', 'show', 'jobid', '-dd', launch_txt['jobid']]
        subprocess.call(cmd, stdout=out, stderr=out)



# ------------------------------------------------------------------

psRE = re.compile(r'[^\s]+\s+([0-9]+)\s+.*')
class MPILauncher(object):
    def __init__(self, run, np=None):
        self.run = os.path.abspath(run)
        self.np = int(np) if np is not None else detect_ncores()

    def __call__(self, mpi_cmd, modele_cmd, time=None, synchronous=False):
        """time:
            Max time to run (ignored)
        synchronous: bool
            Block until task completes"""
        mpi_cmd = copy.copy(mpi_cmd)
        with ectl.util.working_dir(self.run):

            # --------- determine number of processors to use
            mpi_cmd.extend(['-np', str(self.np)])

            # --------- Write out our launch
            modele_pid = os.path.join(self.run, 'modele.pid')
            try:
                os.remove(modele_pid)
            except:
                pass
            mpi_cmd.extend(['--report-pid', modele_pid])
            with open(os.path.join(self.run, 'launch.txt'), 'w') as out:
                out.write('launcher=mpi\n')
                out.write('pidfile={0}\n'.format(modele_pid))
                out.write('mpi_cmd={0}\n'.format(' '.join(mpi_cmd)))
                out.write('modele_cmd={0}\n'.format(' '.join(modele_cmd)))
                out.write('cwd={0}\n'.format(os.getcwd()))

            check_ldd(modele_cmd[0])
            print(' '.join(mpi_cmd + modele_cmd))

            # See: http://stackoverflow.com/questions/29661527/how-to-spawn-detached-background-process-on-linux-in-either-bash-or-python
            # See also: http://stackoverflow.com/questions/37118991/subprocess-gets-killed-even-with-nohup
            # (But this had the problem that os.kill() wasn't giving good
            # info on whether the process was complete)
            #
            # This works so easily because mpirun writes out its own PID
            # file.  If mpirun did not, then we'd need to do more complex
            # daemonization stuff.  For example:
            #      https://github.com/thesharp/daemonize
            cmd = ([] if synchronous else ['nohup'])  + mpi_cmd + modele_cmd
            proc = subprocess.Popen(cmd) #, preexec_fn=os.setpgrp)
            if synchronous:
                proc.wait()

    def get_status(self, launch_txt):
        try:
            with open(launch_txt['pidfile'], 'r') as fin:
                pid = int(next(fin))
                try:
                    os.kill(pid, 0)
                    return RUNNING
                except OSError:
                    return None    # Status is not running...
        except IOError:    # Cannot read modele.pid
            return STOPPED

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

    def kill(self, launch_txt):
        """Kills running jobs."""

        # For now, we only know how to stop mpirun jobs
        pid = self._top_pid()
        try:
            os.kill(pid, signal.SIGKILL) # SIGKILL=9
            sys.stderr.write('Process %d successfully killed\n' % pid)
        except OSError:
            sys.stderr.write('Process %d seems to be already dead\n' % pid)

    def ps(self, launch_txt, out):
        """Shows processes currently running."""
        try:
            top_pid = self._top_pid()
        except IOError:
            out.write('<No Running Processes>\n')
            return

        try:
            sub_pids = re.split(b'\s+', subprocess.check_output(['pgrep', '-P', str(top_pid)]))

            pids = set([top_pid] + [int(x) for x in sub_pids if len(x) > 0])

            cmd = ['ps', 'aux']
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            out.write(str(next(proc.stdout)))
            for line in proc.stdout:
                line = line.decode()    # Convert bytes --> str
                match = psRE.match(line)
                if match is not None:
                    pid = int(match.group(1))
                    if pid in pids:
                        out.write(line)
#                print(match.group(1))
#                print(line)
#            out.write('sub-pids: {0}\n'.format(pids))
        except subprocess.CalledProcessError:
            out.write('<No Running Processes>\n')




# =========================================================================
# Email chain with NCCS (discover) Support, over problems with MPI_Init:
#      Returned value Error (-1) instead of ORTE_SUCCESS
# 
# Subject: Differences in debug QoS? ISSUE=58192
# 
# Elizabeth 2016-04-25
# --------------------
# 
# I have a program that... when I run it on the debug QoS (42 cores, 1h
# requested time), it works.  But when I run it on the main QoS (42
# cores, 10h requested time), it starts but fails immediately when
# trying to initialize MPI.  This is with exactly the same binaries in
# the same location on the filesystem.  The only difference is I add
# --qos=debug to the sbatch command.
# 
# 
# Nick 2016-04-26
# ---------------
# 
# I used the module combination other/comp/gcc-5.3-sp3 and
# other/mpi/openmpi/1.10.1-gcc-5.3-sp3 to run a helloWorld application
# successfully, both on Haswell and Sandybridge type of nodes.  The ldd
# command shows that your program depends on lot of packages, these
# packages and your program should compiled in sp3 environment (not on
# dali node) and then run in sp3 environment.  Also, you could specify
# the job to run on Haswell nodes by specifying --constraint=hasw.
# Running the program in debug qos or other qos should not make
# difference.
# 
# Elizabeth 2016-04-27
# --------------------
# 
# As for this issue... I'm logging into discover-sp3, and doing my build
# there.  But I'm not specifying '--constraint=hasw' when I run.  I have
# noticed that SOMETIMES my jobs DO work when not running debug.  My
# best guess is that for whatever reason, my binary does not work on
# Sandy Bridge nodes.  So I will try adding '--constraint=hasw' and see
# if that can work.
# 
# When I run with --constraint=debug, does that normally provide a Haswell node?
# 
# Nick 2016-04-27
# ---------------
# 
# If you don't specify --constraint=hasw with your jobs, there is a
# chance that your job can land on older sandybridge nodes with SP3.  My
# best guess is that you are running into an issue with code compiled on
# haswell nodes not running correctly on the sandybridge nodes which
# while having SP3 have an older version of the IB cards (mlx4 in
# sandybridge vs mlx5 in haswell).
# 
# There is no --constraint=debug.  "debug" is a QoS and can be specified
# via --qos=debug.  It makes no determination on the node type, it is simply
# a way to get priority access to up to 532 cores (19 haswell nodes or 33
# sandybridge nodes) for up to 1 hour for debugging jobs.  You could in theory
# build on sandybridge nodes and see if you can get that same binary to
# run on the haswell nodes, but the underlying issue is still the difference
# in hardware I believe.
# 
# In theory it is possible to produce binaries that should run on both
# haswell and sandybridge, but in practice I have found that openmpi
# tends to produce binaries that will only work on one or the other
# node type (again, I am not an application programmer, just one of the
# admins so I am not entirely sure how this can be fixed).
# 
# =========================================================================
