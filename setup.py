
# This project will use Python's built-in distutils because it's very simple.
# http://stackoverflow.com/questions/6344076/differences-between-distribute-distutils-setuptools-and-distutils2
# https://docs.python.org/2/distutils/examples.html
# http://matthew-brett.github.io/pydagogue/installing_scripts.html

from distutils.core import setup
import os

setup(name='foo',
      version='1.0',
      package_dir={'': 'lib'},
      packages=['llnl', 'llnl.util', 'llnl.util.tty', 'ectl', 'ectl.tests', 'ectl.rundeck', 'ectl.cmd', 'spack', 'spack.util', 'modele'],
      scripts=[
            os.path.join('bin', 'ectl'),
            os.path.join('bin', 'els')]
      )

