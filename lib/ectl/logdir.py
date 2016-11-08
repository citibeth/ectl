import operator
import functools
import re
from giss import ioutil
from ectl import launchers

def logfiles(logdir):
    """Lists the logfiles (and not other stuff) in a log directory"""
    all = ioutil.list_dir(logdir, r'q\.(\d+).(\d+)',
        lambda match: (int(match.group(1)), int(match.group(2))) )
    return [x[1] for x in all]


class Digger(object):
    def __init__(self):
        self._done = False
    def __call__(self, line, digs):
        pass
    def done(self):
        return self._done


def dig_loglines(loglines, diggers):
    """diggers: {fn(output, line)}
        Each digger function returns True to continue, or False if finished."""

    digs = {}    # Stuff read out of the logfile
    for line in loglines:
        # Run the diggers
        dones = [digger(line, digs) for digger in diggers]
        done = functools.reduce(operator.__or__, dones)

        # Remove a digger if at least one finished
        if done:
            diggers = [x for x in diggers if not x.done()]
            if len(diggers) == 0:
                break
    return digs

def head(lines, n=1):
    """Iterator yields the first n lines of a file."""
    nread = 0
    for line in lines:
        yield line
        nread += 1
        if nread >= n:
            return

def open_tail(file, bytes=1024):
    """Opens a files to the last "bytes" bytes"""
    out = open(file, 'r')
    if bytes > 0:
        try:
            out.seek(-bytes, 2)
        except:
            pass
    return out


def dig_logfile(logfile, diggers, head_lines=0, tail_bytes=0):
    with open_tail(logfile, tail_bytes) as fin:
        lines = fin
        lines = head(fin, head_lines) if head_lines > 0 else fin
        return dig_loglines(lines, diggers)
# --------------------------------------------------------------
class DigExitReason(Digger):
    state0RE = re.compile(r'(.*?)Program terminated due to the following reason:.*')
    state1RE = re.compile(r'(.*?)'
        '((Terminated normally \(reached maximum time\))|'
        '(Run stopped with sswE)|'
        '(Reached maximum wall clock time.)|'
        '(Got signal 15))'
        '.*')

#    state1_reason = {3 : launchers.FINISHED_TIME, 4 : launchers.USER_STOPPED, 5 : launchers.MAX_WTIME, 6 : launchers.SIGNAL_15}

    def __init__(self):
        super().__init__()
        self.run_state = self.state0

    def __call__(self, line, digs):
        return self.run_state(line, digs)

    def state0(self, line, digs):
        match = DigExitReason.state0RE.match(line)
        if match is not None:
            self.run_state = self.state1
        return self._done

    def state1(self, line, digs):
        match = DigExitReason.state1RE.match(line)
        exit_reason = launchers.ExitReason.UNKNOWN
        if match is not None:
            if match.group(3) is not None:
                exit_reason = launchers.ExitReason.FINISHED_TIME
            elif match.group(4) is not None:
                exit_reason = launchers.ExitReason.USER_STOPPED
            elif match.group(5) is not None:
                exit_reason = launchers.ExitReason.MAX_WTIME
            elif match.group(6) is not None:
                exit_reason = launchers.ExitReason.SIGNAL_15
        digs['exit_reason'] = exit_reason
        self._done = True
        return self._done

