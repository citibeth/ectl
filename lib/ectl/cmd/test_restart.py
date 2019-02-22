import ectl
import ectl.launch
import netCDF4
import ectl.setup
import ectl.launch
import ectl.wait
import os
from os.path import join
import sys
from ectl import iso8601, launchers, pathutil
import datetime
from ectl import rundir,rundeck
import numpy as np
import giss.ncutil
import pickle

description = 'Tests that restart capability works.'

def setup_parser(subparser):
    subparser.add_argument('run', nargs='?', default='.',
        help='Directory of run for which restart test will be run.  Rundeck and source directories will be obtained from this run.')


def test_restart(parser, args, unknown_args):

    if len(unknown_args) > 0:
        raise ValueError('Unkown arguments: %s' % unknown_args)

    _test_restart(args.run)


# ========================================================================
# Testing-specific code below



def rd_modify(total_ts):
    """Rundeck modifier, used by ectl.launch.launch.
    Changes end time to run for exactly total_ts timesteps.

    total_ts:
        Number of timesteps to run."""

    def rd_modify(rd, cold_start):
        print('************ rd_modify', cold_start, total_ts)

        # Set end time
        dtsrc = rd.params.params['dtsrc'].parsed
        start_ts = datetime.datetime(*rd.params.inputz.get_timestamp('I', dtsrc=dtsrc))
        end_ts = start_ts + total_ts*datetime.timedelta(seconds=dtsrc)
        rd.params.inputz.set_timestamp('E', (end_ts.year, end_ts.month, end_ts.day, end_ts.hour, end_ts.minute, end_ts.second), dtsrc=dtsrc)

        # Set NISurf: Number of surface timesteps per GCM timestep
        rd.params.params.set('nisurf', '1')

    return rd_modify

# The variables that are OK to be different
legal_diffvars = set(('cputime',))

def _test_restart(parent_run):
    """parent_run:
        The parent run that will be tested.  Nothing will be written in this run,
        it is just used to create two runs in subdirectories"""

    for leaf,nruns,nts in (('nors',1,2), ('rs',2,1)):
        run = os.path.join(parent_run, 'test_restart', leaf)
        print('====================== {}'.format(run))
        status = rundir.Status(run)

        if status.status <= launchers.INITIAL:
            ectl.setup.setup(
                run,
                rundeck=os.path.join(parent_run, 'config', 'rundeck.R'),
                src=os.path.realpath(os.path.join(parent_run, 'src')),
                unpack=False)

            # Go through restarts
            for runi in range(0,nruns):
                total_ts = (runi+1)*nts
                log_dir = pathutil.follow_link(join(run, 'log'), must_exist=True)
                modifys = [rd_modify(total_ts)]

                kwargs = dict()
                if runi > 0:
                    kwargs['restart_file'] = join(log_dir, 'state.nc')

                ectl.launch.launch(
                    run, force=True,
                    rundeck_modifys=modifys,
                    synchronous=True,
                    launcher='mpi',
                    ntasks=6,    # Minimum for ModelE
                    **kwargs)

                fort = rundir.newest_fort(run)
                os.rename(fort.rsf, join(run, 'log', 'state.nc'))

    extra0,extra1,diffvars = giss.ncutil.diff(
        os.path.join(parent_run, 'test_restart', 'nors', 'log', 'state.nc'),
        os.path.join(parent_run, 'test_restart',   'rs', 'log', 'state.nc'),
        os.path.join(parent_run, 'test_restart', 'diffs.nc'))

    print('extra0: {}'.format(extra0))
    print('extra1: {}'.format(extra1))
    print('diffvars: {}'.format(diffvars))
    illegal_diffvars = sorted(set(diffvars) - legal_diffvars)
    print('illegal_diffvars: {}'.format(illegal_diffvars))

    with open(os.path.join(parent_run, 'test_restart', 'diffvars.pk'), 'wb') as fout:
        pickle.dump((extra0,extra1,diffvars,illegal_diffvars), fout)

    if len(illegal_diffvars) > 0:
        raise ValueError('Something changed in the restart test')

    print('Looks like the restart test succeeded, restart works for this rundeck!')
    sys.exit(0)
