import modele.io
from giss.xaccess import *
from giss.functional import *
from giss import xaccess,functional
#from giss import ncutil
import sys
import numpy as np
from giss import ncutil

#ofpat = '/home2/rpfische/tmp/JUL1954.{section}E4F40.R.nc'
run = '/home2/rpfische/exp/160623-stieglitz/melt6'
#accdir = '/home2/rpfische/exp/160623-stieglitz/melt6'

fetch = modele.io.fetch_rundir(run, 'ijhc', 'massxfer_lndice', 1952, 3, 'ec', *_ix[:], region='greenland')

for k,v in sorted(fetch.attrs().items()):
    print(k,v)

sys.exit(0)




modele.io.scaleacc(ofpat, 'ijhc', accdir)

fname = ofpat.format(ofpat, section='ijhc')
massxfer_lndice = bind(modele.io.fetch, fname, 'massxfer_lndice', 'ec')
mass = massxfer_lndice(*_ix[:])
#mass = modele.io.fetch(fname, 'massxfer_lndice', 'ec', *_ix[:])

#print(mass.attrs()[('var', 'units')])
gmass = ncutil.convert_units(massxfer_lndice*2., 'g m-2 day-1')(*_ix[:])

print('sum', np.sum(gmass.data()))
print('sum', np.sum(mass.data()))
print('sum', np.sum((mass*2.).data()))
print('sum', np.sum((mass.data*2.)()))

sys.exit(0)

plotter = xaccess.get_plotter(mass.attrs(), region='greenland')
print('plotter', plotter)

enth = modele.io.fetch(fname, 'massxfer_lndice', 'ec', *_ix[:])

plotter = xaccess.get_plotter(enth.attrs(), region='greenland')
print('plotter', plotter)
