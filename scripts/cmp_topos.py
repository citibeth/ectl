import netCDF4
import numpy as np

with netCDF4.Dataset('redo_topos.nc', 'r') as nc:
    t0 = 0
    t1 = len(nc.dimensions['time'])-1
    print('t1', t1)

    fhc0 = nc.variables['fhc'][t0]
    fhc1 = nc.variables['fhc'][t1]

#    bfhc0 = (nc.variables['fhc'][t0,:] != 0)
#    bfhc0[np.isnan(bfhc0)] = False

#    bfhc1 = (nc.variables['fhc'][t1,:] != 0)
#    bfhc1[np.isnan(bfhc1)] = False

    xfhc = fhc1 - fhc0

    with netCDF4.Dataset('diff.nc', 'w') as ncout:
        ncout.createDimension('HC', size=len(nc.dimensions['HC']))
        ncout.createDimension('lat', size=len(nc.dimensions['lat']))
        ncout.createDimension('lon', size=len(nc.dimensions['lon']))
        ncout.createVariable('fhc', 'd', ('HC', 'lat', 'lon'), zlib=True)

        print(xfhc.shape)
        print(ncout.variables['fhc'].shape)
        ncout.variables['fhc'][:] = xfhc

