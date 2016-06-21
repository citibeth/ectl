from __future__ import print_function
import os

# http://code.activestate.com/recipes/52224-find-a-file-given-a-search-path/
def search_file(filename, search_path):
    """Given a search path, find file
    """
    if os.path.exists(filename):
        return os.path.abspath(filename)

    for path in search_path:
        fname = os.path.abspath(os.path.join(path, filename))
        if os.path.exists(fname):
            return fname
    raise IOError('File not found in search path: {}'.format(filename))


def is_modele_root(dir):
    """Determines whether a directory is the root of a ModelE source
    distro."""

    return \
        os.path.exists(os.path.join(dir, 'init_cond')) and \
        os.path.exists(os.path.join(dir, 'model'))

def modele_root(fname):
    """Given a filename, returns the ModelE root
    directory it is located in."""

    path = os.path.abspath(os.path.split(fname)[0])
    while True:
        if is_modele_root(path):
            return path
        new_path = os.path.dirname(path)
        if new_path == path:
            return None
#            raise ValueError('File %s does not appear to be in a ModelE source directory.' % fname)
        path = new_path

def has_file(path, fname):
    ret = os.path.join(path, fname)
    if os.path.exists(ret):
        return ret
    return None

def search_up(path, condition_fn):
    """Scans up a directory tree until a condition is found on one of the paths."""

    path = os.path.abspath(path)#os.path.split(fname)[0])
    while True:
        ret = condition_fn(path)
        if ret is not None:
            return ret
        new_path = os.path.dirname(path)
        if new_path == path:
            # Didn't find it.
            return None
        path = new_path

def follow_link(linkname, must_exist=False):
    if not os.path.exists(linkname):
        return None
    fname = os.path.realpath(linkname)
    if must_exist and not os.path.exists(fname):
        return None
    return fname


class ChangePythonPath(object):
    """Context manager that temporarily changes sys.path"""
    def __init__(self, new_path):
        self.new_path = new_path
    def __enter__(self):
        self.old_path = sys.path
        sys.path = self.new_path
    def __exit__(self, type, value, traceback):
        sys.path = self.old_path
