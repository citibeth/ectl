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
import subprocess
import sys
import shutil
from ectl import iso8601
import datetime
import ectl.rundir
import signal
import time

def wait(runs, recursive=False, verbose=False):

    if isinstance(runs, str):
        runs = [runs]

    doruns = rundir.all_rundirs(runs, recursive=recursive)

    # Construct set of currently-running runs
    running = set()
    for run,status in doruns:
        if status.status != launchers.RUNNING:
            print('{0}: {1}'.format(status.run, status.sstatus))
        else:
            running.add(status)

    if len(running) == 0:
        return

    print('Waiting...')

    # Wait for them to all die
    while len(running) > 0:
        time.sleep(1)

        # Determine what is no longer running
        to_remove = set()
        for status in running:
            if verbose:
                print('status', status.sstatus)
            if status.refresh_status() != launchers.RUNNING:
                print('{0}: {1}'.format(status.run, status.sstatus))
                to_remove.add(status)

        # Remove those items from the running set
        for status in to_remove:
            running.remove(status)
