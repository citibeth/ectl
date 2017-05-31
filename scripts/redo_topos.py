import os
srcdir = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.append(os.path.join(srcdir, '..', '..', 'python', 'lib'))

import copy
import numpy as np
from giss import giutil
import icebin
from icebin import ibgrid
from giss.ncutil import copy_nc
import netCDF4
import argparse
from modele.constants import SHI,LHM,RHOI,RHOS,UI_ICEBIN,UI_NOTHING


gcm_out_RE = re.compile('gcm-out-(\d\d\d\d\d\d\d\d).nc')
def run_dates(run):
    ret = list()
    for fname in os.listdir(run):
        match = gcm_out_RE.match(fname)
        if match is not None:
            ret.append(match.group(1))
    ret.sort()
    return ret
        


def redo_topos(icebin_in, topo_in, run='.'):
    mytopos = topos.Topos(icebin_in, topo_in)

    pism_out_nc = None
    ncout = None

    try:
        mytopos = topos.Topos(icebin_in, topo_in)

        pism_out_nc =  netCDF4.Dataset(os.path.join(run, 'greenland', 'pism-out.nc'))

        # Get times as list of Python's datetime.datetime
        time_nc = pism_out_nc.variables['time']
        units = time_nc.units
        calendar = time_nc.calendar
        times = netCDF4.num2date(time_nc[:], units, calendar=calendar)

        # ----------- Get 2D dimensions
        with netCDF4.Dataset(os.path.join(run, 'gcm-in-19491231.nc'), 'r') as nc:
            lat = len(nc.dimensions['lat'])
            lon = len(nc.dimensions['lon'])
            if lat*lon != mytopos.nA:
                raise ValueError('lat*lon ({}) != nA ({}), but it should'.format(lat*lon, mytops.nA))

        # ----------- Open output NetCDF file
        ncout = netCDF4.Dataset(os.path.join(run, 'redo_topos.nc'), 'w')
        time = ncout.createDimension('time', size=0)
        HC = ncout.createDimension('HC', size=mytopos.nhc_gcm)
        lat = ncout.createDimension('lat', size=lat)
        lon = ncout.createDimension('lon', size=lon)

        # Vars on A grid
        Avars = ('focean', 'flake', 'fgrnd', 'fgice', 'zatmo_m')
        for name in Avars:
            ncout.createVariable(name, 'd', ('time', 'lat', 'lon'))

        # Vars on E grid
        Evars = ('fhc', 'elevE')
        for name in Evars:
            ncout.createVariable(name, 'd', ('time', 'HC', 'lat', 'lon'))
        # -------------------------------------------



        for i in range(0,len(times)-1):
            # Manage loop
            dt0 = times[i]
            dt1 = times[i+1]
            if dt1 >= end:
                break

            # Reshape and write out variables that were computed
            elevI = pism_out_nc.variables['elevI'][i]
            sheet = SheetInfo('greenland', elevI)
            vars = mytopos.get_fractions((sheet,))

            for name in Avars:
                val = vars[name].reshape((lat, lon))
                ncout[name][:] = val[:]

            for name in Evars:
                val = vars[name].reshape((mytopos.nhc_gcm, lat, lon))
                ncout[name][:] = val[:]


    finally:
        if pism_out_nc is not None:
            pism_out_nc.close()
        if ncout is not None:
            ncout.close()


def redo_topos_in_run_dir(run):
    with open(os.path.join('config', 'icebin.nc')) as nc:
        icebin_in = nc.variables['m.info'].grid

    file_path = os.environ['MODELE_FILE_PATH'].split(os.pathsep)
    iTOPO = giutil.search_file(args.topo+'.nc', file_path)
    print(' READ: iTOPO = {}'.format(iTOPO))

    redo_topos(icebin_in, topo_in, run=run)

redo_topos_in_run_dir('.')
