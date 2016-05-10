import ectl
from ectl import rundeck

import sys
import os
import string
import tempfile
import filecmp
import shutil
from ectl import pathutil

# TODO: Be careful not to leave around zero-length files when downloading

# --------------------------------------
def resolve_fname(run_dir):
    """Given a user-generated rundir name, returns a pathname to it."""
    if os.path.isabs(run_dir):
        return run_dir
    else:
        return os.path.join(ectl.root, 'runs', run_dir)


def namelist_time(suffix, dt):
    return 'YEAR{0}={1},MONTH{0}={2},DATE{0}={3},HOUR{0}={4},' \
        .format(suffix,dt.year,dt.month,dt.day,dt.hour)

def make_rundir(rd, rundir):
    ret = True

    # output line sections
    parameters = []
    data_files = []
    data_lines = []
    inputz = []
    inputz_cold = []

    # Organize parameters into ModelE sections
    for param in sorted(list(rd.params.values())):
        pname = param.pname
        if isinstance(pname, str):    # Non-compound name
            if (id(param.type) == id(rundeck.FILE)):
                if param.rval is not None:
                    data_lines.append(" _file_{}='{}'".format(pname, param.rval))
                    data_files.append((pname, param.rval))
#                else:
#                    parameters.append("! Not Found: {}={}".format(pname, param.sval))

            elif (id(param.type) == id(rundeck.GENERAL)):
                parameters.append(' %s=%s' % (param.pname, param.value))
            elif (id(param.type) == id(rundeck.DATETIME)):
                raise ValueError('Cannot put DATETIME values into parameters section of rundeck.')
            else:
                raise ValueError('Unknown parameter type %s' % param.type)
        elif len(pname) == 2:
            if pname[0].lower() == 'inputz':
                iz = inputz
            elif pname[0].lower() == 'inputz_cold':
                iz = inputz_cold
            else:
                raise ValueError('Unknown compound name: {}'.format(pname))

            if pname[1].upper() == 'END_TIME':
                iz.append(namelist_time('E', param.value))
            elif pname[1].upper() == 'START_TIME':
                iz.append(namelist_time('I', param.value))
            else:
                iz.append('{}={},'.format(pname[1],param.value))



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
    for label, fname in data_files:
        try:
            os.remove(os.path.join(rundir, label))
        except OSError:
            pass

    # -------- Link data files
    for label, fname in data_files:
        os.symlink(fname, os.path.join(rundir, label))

    # Write them out to the I file
    fname = os.path.join(rundir, 'I')
    out = open(fname, 'w')
    out.write(rd.preamble[0])    # First line of preamble
    out.write('\n')

    out.write('&&PARAMETERS\n')
    out.write('\n'.join(parameters))
    out.write('\n')
    out.write('\n'.join(data_lines))
    out.write('\n&&END_PARAMETERS\n')

    out.write('\n&INPUTZ\n')
    out.write('\n'.join(inputz))
    out.write('\n/\n\n')

    out.write('&INPUTZ_cold\n')
    out.write('\n'.join(inputz_cold))
    out.write('\n/\n')

INITIAL=0
RUNNING=1
PAUSED=2
FINISHED=3

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
    for file in files:
        if file[-3:] == '.nc':
            has_nc = True
            break
    if not has_nc:
        return INITIAL

    # Check for fort.1.nc and fort.2.nc
    if not (('fort.1.nc' in files) or ('fort.2.nc' in files)):
        # No fort.x.nc files, we cannot continue the run
        return FINISHED

    # It's not INITIAL or FINISHED, assume PAUSED
    # (until we know better how to detect the loc file)
    return PAUSED
