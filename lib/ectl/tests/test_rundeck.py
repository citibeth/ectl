from ectl import rundeck
import hashlib
import unittest
import os

srcdir = os.path.dirname(os.path.abspath(__file__))

class TestRundeck(unittest.TestCase):

    def xtest_legacy(self):
        fname = os.path.join(srcdir, 'rundeck1a.R')
        fin = rundeck.legacy.preprocessor(fname, ['.'])
        for line in fin:
            print(line)

    def test_rundeck(self):
        modele_root = os.path.join(os.environ['HOME'], 'f15', 'modelE')
        rd = rundeck.load(os.path.join(srcdir, 'rundeck1a.R'), modele_root=modele_root)
        print(rd)

if __name__ == "__main__":
    unittest.main()
