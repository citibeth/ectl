from __future__ import print_function
import os
import re
import sys

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
    raise IOError('File not found in search path: {0}'.format(filename))

def search_or_download_file(param_name, file_name, search_path, download_dir=None):
    try:
        return search_file(file_name, search_path)
    except IOError as e:
        if download_dir is None:
            # We can't download, just raise an error.
            sys.stderr.write('{0}: {1}\n'.format(param_name, e))
            raise
        else:
            # Could not resolve path; download it
            try:
                return download_file(file_name, download_dir, label=param_name)
            except KeyboardInterrupt as e2:
                print(e2)
                raise
            except Exception as e2:
                sys.stderr.write('{0}: {1}\n'.format(param_name, e2))
                raise


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
    """Finds what a link points to."""
    if not os.path.islink(linkname):
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

def remake_dir(dir):
    """Creates a directory, renaming the old one to <dir>.v???"""
    if os.path.exists(dir):
        print('EXISTS')
        # Move to a '.vXX' name
        root,leaf = os.path.split(dir)
        dirRE = re.compile(leaf + r'\.v(\d+)')
        max_v = 0
        for fname in os.listdir(root):
            match = dirRE.match(fname)
            if match is not None:
                v = int(match.group(1))
                if v > max_v:
                    max_v = v
        next_fname = os.path.join(root, '%s.%02d' % (leaf, max_v+1))
        os.rename(dir, next_fname)

    os.mkdir(dir)


def make_vdir(dir):
    """Creates a directory named <dir>XX, and symlinks <dir> to it."""

    # Find the next 'vXXX' name to use
    root,leaf = os.path.split(dir)
    dirRE = re.compile(leaf + r'(\d+)')
    max_v = 0
    for fname in os.listdir(root):
        match = dirRE.match(fname)
        if match is not None:
            v = int(match.group(1))
            max_v = max(max_v, v)
    next_fname = '%s%02d' % (leaf, max_v+1)
    ret = os.path.join(root, next_fname)
    os.mkdir(ret)

    # Create symlink log -> log.vXXX
    try:
        #shutil.rmtree(dir)
        os.remove(dir)
    except OSError:
        pass
    os.symlink(next_fname, dir)

    return ret
