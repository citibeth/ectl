import os
import re
from ectl import xhash

badRE = re.compile(r"\.git|\..*|doc|aux|init_cond|tests|pyext|pylib|decks|\.DS_Store|\.#.*|a\.out|.*\.o|spconfig\.py")

def list_src_files(src_dir):
    # Add build files in top-level ModelE directory (above model/)
    modele_control = os.path.join(src_dir, 'modele-control.pyar')
    if os.path.exists(modele_control):
        yield modele_control
    else:
        yield os.path.join(src_dir, 'CMakeLists.txt')

    for top_dir in ('model', 'cmake'):
        for root, dirs, files in os.walk(os.path.join(src_dir, top_dir)):
            for file in files:
                if badRE.match(file) is None:
                    yield os.path.join(root, file)


def update_hash(src_dir, hash):
    """Hashes an entire ModelE source directory"""
    src_files = sorted(list_src_files(src_dir))
    for file in src_files:
        fname = os.path.join(src_dir, file)
        with open(fname) as fin:
            try:
                code = fin.read()
                xhash.update(code, hash)
            except:
                print('Error hashing file %s' % fname)
                raise

