import re
import os
import subprocess
import math
import spack.util.executable
from giss import ioutil

class MPIVendor(object):
    """Superclass for MPI vendors"""
    def __init__(self, vendor, version):
        self.vendor = vendor
        self.version = version

    def write_vendor(self, log_dir):
        """Writes MPI vendor information to the output directory."""
        with open(os.path.join(log_dir, 'MPI.txt'), 'w') as out:
            out.write('{}@{}\n'.format(
                self.vendor,
                '.'.join(str(x) for x in self.version)))

    def logfiles(self, logdir):
        """Returns just names of logfiles, without keys"""
        return [logfile for key,logfile in self.keys_and_logfiles(logdir)]
# ------------------------------------------------------------
def get_rank_format(np):
    """Susses out the number of digits used by MPI to create rank numbers,
    based on the total number of processors"""
    if np == 1:
        ndigits = 1
    else:
        ndigits = int(math.log10(np))+1
    return '{:0%dd}' % ndigits

class OpenMPI1(MPIVendor):
    """OpenMPI Version 1"""

    def cmd(self, log_dir):
        """Creates the basic mpirun command line"""
        mpirun = str(spack.util.executable.which('mpirun'))

        return [mpirun, '-timestamp-output', '-output-filename', os.path.join(log_dir, 'q')]

    def make_symlinks(self, log_dir, np):
        """Symlink logfiles"""
        fmt = get_rank_format(np)
        for i in range(0,np):
            real = ('q.1.' + fmt).format(i)
            link = os.path.join(log_dir, fmt.format(i))
            os.symlink(real, link)

    def keys_and_logfiles(self, logdir):
        """Lists the logfiles (and not other stuff) in a log directory
        returns: [(key, fname)]
            key: tuple(process group ID, rank)
            fname: Full filename (including logdir)
        """
        all = ioutil.list_dir(logdir, r'q\.(\d+).(\d+)',
            lambda match: (int(match.group(1)), int(match.group(2))) )
        return all

# ------------------------------------------------------------
class OpenMPI3(MPIVendor):
    """OpenMPI Version 3"""

    def cmd(self, log_dir):
        """Creates the basic mpirun command line"""
        mpirun = str(spack.util.executable.which('mpirun'))

        return [mpirun, '-timestamp-output', '-merge-stderr-to-stdout',
            '-output-filename', os.path.join(log_dir, 'log')]

    def make_symlinks(self, log_dir, np):
        """Symlink logfiles"""
        fmt = get_rank_format(np)
        rank_fmt = 'rank.' + fmt
        for i in range(0,np):
            real = os.path.join('log', '1', rank_fmt.format(i), 'stdout')
            link = os.path.join(log_dir, fmt.format(i))
            os.symlink(real, link)

    def keys_and_logfiles(self, logdir):
        """Lists the logfiles (and not other stuff) in a log directory
        returns: [(key, fname)]
            key: tuple(process group ID, rank)
            fname: Full filename (including logdir)
        """
        # Assume everything is in process group 1 here.
        all = ioutil.list_dir(os.path.join(logdir, 'log', '1'), r'rank\.(\d+)',
            lambda match: (1, int(match.group(1))) )
        return all

# ------------------------------------------------------------
class IntelMPI(MPIVendor):
    def cmd(self, log_dir):
        """Creates the basic mpirun command line"""
        # $ mpirun -outfile-pattern --help
        # -outfile-pattern: Send stdout to this file
        #
        #    Regular expressions can include:
        #        %r: Process rank
        #        %g: Process group ID
        #        %p: Proxy ID
        #        %h: Hostname
        return [str(spack.util.executable.which('mpirun')),
            '-outfile-pattern', os.path.join(log_dir, '%r'),
            '-errfile-pattern', os.path.join(log_dir, 'err%r')]

    def make_symlinks(self, log_dir, np):
        """Symlink logfiles"""
        print('No output symlinks for IntelMPI')

    def keys_and_logfiles(self, logdir):
        """Lists the logfiles (and not other stuff) in a log directory
        returns: [(key, fname)]
            key: tuple(process group ID, rank)
            fname: Full filename (including logdir)
        """
        # Assume everything is in process group 1 here.
        all = ioutil.list_dir(logdir, r'(\d+)',
            lambda match: (1, int(match.group(1))) )
        return all


# ------------------------------------------------------------
mpiRE = re.compile(
    r'(mpirun \(Open MPI\) (\d+)\.(\d+)\.(\d+).*)|'+ \
    r'(Intel\(R\) MPI Library for Linux\* OS, Version (\d+) Update (\d+) Build (\d+) \(id: (\d+)\).*)',
    re.MULTILINE)

def construct_mpi_vendor(vendor, version):
    if vendor == 'openmpi':
        if (version[0] == 1):
            return OpenMPI1(vendor,version)
        if (version[0] == 3):
            return OpenMPI3(vendor,version)
        raise RuntimeError('Unrecognized OpenMPI Version: {}'.format(version))

    if vendor == 'impi':
        return IntelMPI(vendor, version)



def mpi_vendor():
    """Constructs an MPIVendor instance by poking around the system."""

    """Returns a tuple (MPIVendor, Version)"""
    proc = subprocess.Popen(['mpirun', '-version'],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (sout, serr) = proc.communicate()
    sout = sout.decode()
    serr = serr.decode()

    match = mpiRE.match(sout)
    if match is None:
        sys.stderr.write('------------------- mpirun version output:\n')
        sys.stderr.write(sout)
        sys.stderr.write('\n----------------------------------------------\n')
        raise RuntimeError('Cannot determine MPI vendor and version: {}'.format(sout))
    if match.group(1) is not None:
        vendor = 'openmpi'
        version = (int(match.group(2)), int(match.group(3)), int(match.group(4)))
    elif match.group(5) is not None:
        vendor = 'impi'
        version = (int(match.group(6)), int(match.group(7)), int(match.group(8)), int(match.group(9)))
    else:
        raise RuntimeError("Cannot construct MPIVendor, don't know why")
    return construct_mpi_vendor(vendor,version)

def read_mpi_vendor(logdir):
    """Constructs an MPIVendor instance by reading record from a log directory."""

    with open(os.path.join(logdir, 'MPI.txt')) as fin:
        line = fin.readline()

    vendor,sversion = line.split('@')
    version = tuple(int(x) for x in sversion.split('.'))

    return construct_mpi_vendor(vendor, version)
