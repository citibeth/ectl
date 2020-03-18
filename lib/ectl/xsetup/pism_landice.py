from giss import ncutil
from modele import enthalpy
import netCDF4
import os
import icebin
from modele.constants import SHW,SHI,LHM,RHOI
import numpy as np
import giss
import shutil

def redo_GIC(GIC0, TOPO, pism_ic, icebin_in, GIC=None):

    """Re-generates the state of the Stieglitz model, based on the current
    state of the PISM ice sheet.  Original GIC file respects the extent of
    the ice sheet, but not the state of its surface.

    GIC0:
        Name of GIC file that was generated (via add_fhc.py)
        based on ModelE's ice sheet (i.e. no PISM coupling)
    pism_ic:
        Name of PISM initial condition file
    icebin_in:
        Name of IceBin config / grid description file.
    """

    # Get regridding matrices
    mm = icebin.GCMRegridder(icebin_in)
    rm = mm.regrid_matrices('greenland')
    EvI_n = rm.matrix('EvI', correctA=False)    # No projection correction; use for regridding [J kg-1]
    AvI = rm.matrix('AvI')


    # Read info on EC segments from the TOPO file
    with netCDF4.Dataset(TOPO) as nc:
        segment_names = nc.variables['segments'].names.split(',')
        x = nc.variables['segments'].bases
        segment_bases = nc.variables['segments'].bases
        nhc_gcm = len(nc.dimensions['nhc'])

        segments = dict([(segment_names[i], (segment_bases[i], segment_bases[i+1])) for i in range(0,len(segment_names))])
        jm = len(nc.dimensions['lat'])
        im = len(nc.dimensions['lon'])

        fhc = nc.variables['fhc'][:]

    nlice = 4

    # Read original ModelE initial conditions
    with netCDF4.Dataset(GIC0, 'r') as nc:
        wsn0A = nc.variables['wsn'][0,:,:,0]
        hsn0A = nc.variables['hsn'][0,:,:,0]
        senth0A = hsn0A / wsn0A

    # Read data from PISM initial conditions
    with netCDF4.Dataset(pism_ic) as nc:
        tempI = nc.variables['effective_ice_surface_temp'][-1,:,:].reshape(-1)    # (y,x)  [K]
        fracI = nc.variables['effective_ice_surface_liquid_water_fraction'][-1,:,:].reshape(-1)    # [1]
    senthI = enthalpy.temp_to_senth(tempI-273.15, fracI)    # Convert to specific enthalpy (ModelE base)
    senthA = AvI.apply(senthI).reshape((jm,im))
    # Combine with global initial condition
    # This merging of ice sheets can/will create a few grid cells that
    # had an ice sheet before under ModelE, and are now off the PISM
    # ice sheet; they've become non-ice-sheet "legacy ice."
    # More careful (manual) merging would solve this.
    nans = np.isnan(senthA)
    senthA[nans] = senth0A[nans]

    shapeA = (jm,im)
    shapeEx = (nhc_gcm,jm,im,nlice)    # Ex = Stieglitz model dimensions w/ nhc_gcm

    dz = np.zeros(shapeEx)    # (nhc_gcm, j, i, nlice)
    #wsn = np.zeros(shapeEx)
    #hsn = np.zeros(shapeEx)
    #tsn = np.zeros(shapeEx)
    shsn = np.zeros(shapeEx)    # Specific enthalpy

    # Thickness of each layer of snow [m]
    dz[:,:,:,0] = .1
    dz[:,:,:,1] = 2.9
    dz[:,:,:,2] = 3.
    dz[:,:,:,3] = 4.

    # Initialize everything at ice density (promotes stability vs. ice sheet below)
    wsn = dz * RHOI

    # Initialize everything at 1/2 ice density (this IS the surface...)
    # wsn = dz * RHOI * .5

    # ------------------------ Legacy Segment
    base,end = segments['legacy']
    for il in range(0,nlice):
        shsn[base,:,:,il] = senthA

    # ------------------------ Sea/Land
    base,end = segments['sealand']
    for ihc in range(base,end):
        for il in range(0,nlice):
            shsn[ihc,:,:,il] = senthA

    # ------------------------ EC segments
    base,end = segments['ec']
    nhc = end-base
    senthE = EvI_n.apply(senthI).reshape((nhc,jm,im))
    for ihc in range(0,nhc):
        senthE_ihc = senthE[ihc,:,:]
        nans = np.isnan(senthE_ihc)
        senthE_ihc[nans] = senthA[nans]

    for il in range(0,nlice):
        shsn[base:end,:,:,il] = senthE
    # ----------------------------------------------

    shsn[fhc == 0] = np.nan

    tsn,isn = enthalpy.senth_to_temp(shsn)
    hsn = shsn * wsn

    with netCDF4.Dataset(GIC, 'w') as ncout:
        with netCDF4.Dataset(GIC0, 'r') as ncin:
            # Copy GIC0 --> GIC except for the variables we want to rewrite
            nco = giss.ncutil.copy_nc(ncin, ncout,
                var_filter = lambda x : None if x in {'dz', 'wsn', 'hsn', 'tsn'} else x)
            nco.define_vars(zlib=True)
            ncout.createDimension('nlice', 4)
            ncout.createDimension('nhc', nhc_gcm)

            args = 'd', ('nhc', 'jm', 'im', 'nlice')
            kwargs = {'zlib' : True}
            dz_v = ncout.createVariable('dz', *args, **kwargs)
            wsn_v = ncout.createVariable('wsn', *args, **kwargs)
            hsn_v = ncout.createVariable('hsn', *args, **kwargs)
            tsn_v = ncout.createVariable('tsn', *args, **kwargs)
            nco.copy_data()

            # Rewrite...
            dz_v[:] = dz[:]
            wsn_v[:] = wsn[:]
            hsn_v[:] = hsn[:]
            tsn_v[:] = tsn[:]


def xsetup(args_run, rd):
    """args_run:
        Main run directory
    rd:
        The rundeck, parsed and loaded."""

    GIC0 = rd.params.files['GIC0'].rval
    TOPO = rd.params.files['TOPO'].rval

    with netCDF4.Dataset(os.path.join('config', 'icebin.nc')) as nc:
        pism_ic = nc.variables['m.greenland.pism'].i
        icebin_in = nc.variables['m.info'].grid

    redo_GIC(GIC0, TOPO, pism_ic, icebin_in, GIC=os.path.join(args_run, 'GIC'))

