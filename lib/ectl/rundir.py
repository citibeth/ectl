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

# TODO: Be careful not to leave around zero-length files when downloading

# --------------------------------------
class FollowLinks(object):
    """Reads links from an existing run directory.  If the links don't
    exist, or if the entire directory doesn't exist, sets to None."""

    def __init__(self, run):
        self.run = run
        self.rundeck = pathutil.follow_link(
            os.path.join(run, 'rundeck.R'), must_exist=True)
        self.src = pathutil.follow_link(
            os.path.join(run, 'src'), must_exist=True)
        self.build = pathutil.follow_link(
            os.path.join(run, 'build'))
        self.pkg = pathutil.follow_link(
            os.path.join(run, 'pkg'))



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

INITIAL=0
RUNNING=1
PAUSED=2
FINISHED=3

accRE = re.compile('(.*?)\.acc(.*?)\.nc')
def status(run_dir):
    """Determines whether a run directory is:
        INITIAL: Run not yet begun
        RUNNING: A process is actively running it
        PAUSED: In the middle of a run, but nothing running
        FINISHED: No more runs possible (rsf vs fort.1.nc?)."""
    try:
        files = set(os.listdir(run_dir))
    except:
        return INITIAL    # The dir doesn't even exist!

    # First, check for any netCDF files.  If there are NO such files,
    # then we've never run.
    has_nc = False

    fort_files = ('fort.1.nc' in files) or ('fort.2.nc' in files)

    if fort_files:
        return PAUSED

    acc_files = False
    for file in files:
        if accRE.match(file) != None:
            acc_files = True
            break

    if acc_files:
        return FINISHED

    return INITIAL
