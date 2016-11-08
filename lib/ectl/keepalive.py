import os
from giss import ioutil
import ectl.rundir
import ectl.logdir
import ectl.launch
import llnl.util.lock
from ectl import launchers

def load(keepalive):
    runs = []
    if os.path.exists(keepalive):
        with open(keepalive, 'r') as fin:
            for line in fin:
                runs.append(line.strip())
    return runs


def save(runs, keepalive):
    with ioutil.AtomicOverwrite(keepalive) as fout:
        for line in runs:
            fout.out.write(line + '\n')
        fout.commit()

def check(args, runs):
    """Makes sure a list of runs is a live; or removes from the list if
    they are done."""
    oruns = []    # List of runs we will return
    for run in runs:
        status = ectl.rundir.Status(run)
        print('Run:', status.sstatus, run)

        # If it's running, queued, etc... keep going
        if status.status < launchers.STOPPED:
            oruns.append(run)
            continue

        # If it's finished, get rid of it
        if status.status > launchers.STOPPED:
            continue

        # It's stopped... we need to know why
        if status.status == launchers.STOPPED:
            # Find out why it's stopped
            latest_logdir = ectl.rundir.latest_logdir(run)
            logfile = ectl.logdir.logfiles(latest_logdir)[0]
            digs = ectl.logdir.dig_logfile(logfile,
                [ectl.logdir.DigExitReason()],
                tail_bytes=10000)
            exit_reason = digs['exit_reason']
            print('    exit_reason:', launchers.ExitReason.str(exit_reason))

            # Restart things that timed out
            # Re-use the SAME I-file
            if exit_reason == launchers.ExitReason.MAX_WTIME:
                ectl.launch.launch(run, launcher=args.launcher,
                    ntasks=args.np, time=args.time,
                    keep_I=True, add_keepalive=False)
                oruns.append(run)

    return oruns

def add(run):
    """keepalive:
        Name of the keepalive file
    run:
        Directory of run to add to the keepalive file"""
    run = os.path.realpath(run)
    config = ectl.config.Config(run=run)

    print('keepalive=', config.keepalive)

    lock = None
    try:
        # Make sure lockfile exists...
        lockfile = config.keepalive + '.lock'
        if not os.path.exists(lockfile):
            with open(lockfile, 'w'):
                pass

        # Get the lock
        lock = llnl.util.lock.Lock(lockfile)
        lock.acquire_write()

        runs = load(config.keepalive)
        run_set = set(runs)
        if run not in run_set:
            runs.append(run)
            save(runs, config.keepalive)

    finally:
        if lock is not None:
            lock.release_write()
