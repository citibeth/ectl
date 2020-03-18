from __future__ import print_function
import multiprocessing
import os
import hashlib
import argparse
import llnl.util.tty as tty
import ectl
import ectl.cmd
from ectl import pathutil,rundeck,rundir,xhash,launchers
from ectl.rundeck import legacy
import re
from ectl import iso8601
import sys
import shutil
from ectl import iso8601
import datetime
import ectl.rundir
import signal
import subprocess

description = 'Reports on the status of a run.'

def setup_parser(subparser):
    subparser.add_argument('runs', nargs='*',
        help='Directory of run to give execution command')
    subparser.add_argument('-r', '--recursive', action='store_true', dest='recursive', default=False,
        help='Recursively descend directories')
    subparser.add_argument('-R', '--running', action='store_true', dest='running', default=False,
        help='Show only RUNNING processes') 



## This require netCDF libraries in Python; but we want to be using
## a simple System python.
#caldateRE = re.compile(r'(\d+)/(\d+)/(\d+)\s+hr\s+(\d+).(\d+)')
#def get_caldate(fort_nc):
#    """Gets the current timestamp from a fort.1.nc or fort.2.nc file."""
#    with netCDF4.Dataset(fort_nc) as nc:
#        caldate = nc.variables['itime'].caldate
#    match = caldateRE.match(caldate)
#    return datetime.datetime(match.group(3), match.group(1), match.group(2), match.group(4), match.group(5))

caldateRE = re.compile(r'(\d+)/(\d+)/(\d+)\s+hr\s+([\d\.]+)')
def get_caldate(fort_nc):
    cmd = ['ncdump', '-h', fort_nc]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    for line in proc.stdout:
        line = line.decode()    # bytes --> str
        match = caldateRE.search(line)
        if match is not None:
            hr_f = float(match.group(4))

            # Time is in floating-point hours.  Convert to hh:mm:ss
            sec = int(hr_f * 3600. + .5)
            hour = sec // 3600
            sec -= hour * 3600
            minute = sec // 60
            sec -= minute * 60

            return datetime.datetime(int(match.group(3)), int(match.group(1)), int(match.group(2)), hour, minute, sec)
    return None


def ps(parser, args, unknown_args):
    if len(unknown_args) > 0:
        raise ValueError('Unkown arguments: %s' % unknown_args)

    recursive = args.recursive
    doruns = rundir.all_rundirs(args.runs, recursive=args.recursive)

    for run,status in doruns:
        if (status.status == launchers.NONE):
            sys.stderr.write('Error: No valid run in directory %s\n' % run)
            sys.exit(-1)

        if (args.running and status.status != launchers.RUNNING):
            continue

        # Top-line status
        print('============================ {0}'.format(os.path.split(run)[1]))
        print('status:  {0}'.format(status.sstatus))

        paths = rundir.FollowLinks(run)

        # Current time
        try:
            with open(os.path.join(paths.run, 'timestep.txt')) as fin:
                sys.stdout.write(next(fin))
        except IOError as err:
            pass

        # Time in fort.1.nc and fort.2.nc
        dates = [ \
            (get_caldate(os.path.join(paths.run, 'fort.1.nc')), 'fort.1.nc'),
            (get_caldate(os.path.join(paths.run, 'fort.2.nc')), 'fort.2.nc')]
        dates = [x for x in dates if x[0] is not None]
        dates.sort()
        for dt,fname in dates:
            if dt is not None:
                print('{0}: {1}'.format(fname, dt))

        # Run configuration
        paths.dump()

        # Launch.txt
        if status.launch_list is not None:
            for key,val in status.launch_list:
                print('{0} = {1}'.format(key, val))


        # Do launcher-specific stuff to look at the actual processes running.
        launcher = status.new_launcher()
        if launcher is not None:
            launcher.ps(status.launch_txt, sys.stdout)

