import os
import sys
import numpy as np
from giss.ncutil import copy_nc
import netCDF4
import argparse
from modele.constants import SHI,LHM,RHOI,RHOS,UI_ICEBIN,UI_NOTHING

def gic2stieglitz(igic, ogic):
    """Converts a GIC file for the 1984 snow/firn model into one
    for the Lynch-Stieglitz snow/firn model.

    igic:
        Input GIC file, non-Stieglitz
    ogic:
        Output GIC file, Stieglitz"""

    nlice=5

    # -------------------------------------------------------------
    # 5) Convert snowli/tlandi to Stieglitz state variables

    with netCDF4.Dataset(igic) as ncin:
        snowli = ncin.variables['snowli'][:]    # snowli[nhc, jm, im]
        tlandi = ncin.variables['tlandi'][:]    # tlandi[nhc, jm, im, 2]
        nhc,jm,im = snowli.shape

    # Generate GIC variables for the Stieglitz model
    # OUTPUT: dz,wsn,hsn,tsn

    shape_stieglitz = (nhc, jm, im, nlice)
    dz = np.zeros(shape_stieglitz)
    wsn = np.zeros(shape_stieglitz)
    hsn = np.zeros(shape_stieglitz)
    tsn = np.zeros(shape_stieglitz)

    # Just copy the ECs already there.  Don't try to make an EC file out
    # of a non-EC file.
    for ihc in range(0,nhc):

        # Handle the "snow" layer in the old ModelE
        wsn[ihc,:,:,0] = snowli[0,:,:]
        dz[ihc,:,:,0] = wsn[ihc,:,:,0] / RHOS

        # Set up thicknesses in the ice layers
        dz[ihc,:,:,1] = .1
        dz[ihc,:,:,2] = 2.9
        dz[ihc,:,:,3] = 3.
        dz[ihc,:,:,4] = 4. - dz[ihc,:,:,0]    # Balance volume from snow

        # Set mass of lower layers, as solid ice
        wsn[ihc,:,:,1:] = dz[ihc,:,:,1:] * RHOI

        # Set temperatures of the layers
        tsn[ihc,:,:,0] = tlandi[0,:,:,0]
        tsn[ihc,:,:,1:3] = tlandi[0,:,:,0:2]
        tsn[ihc,:,:,3] = tlandi[0,:,:,1]
        tsn[ihc,:,:,4] = tlandi[0,:,:,1]

        # Set enthalpy based on temperature
        hsn[ihc,:,:,:] = wsn[ihc,:,:,:] * (tsn[ihc,:,:,:] * SHI - LHM)

        # Eliminate snow layer if it is empty
        for j in range(0,dz.shape[1]):
    #        print(j,dz.shape[1])
            for i in range(0,dz.shape[2]):
                if dz[ihc,j,i,0] == 0.:
                    dz[ihc,j,i,0:3] = dz[ihc,j,i,1:4]
                    wsn[ihc,j,i,0:3] = wsn[ihc,j,i,1:4]
                    hsn[ihc,j,i,0:3] = hsn[ihc,j,i,1:4]
                    tsn[ihc,j,i,0:3] = tsn[ihc,j,i,1:4]

                    # Split last layer in two
                    dz[ihc,j,i,3:5] = dz[ihc,j,i,4] * .5
                    wsn[ihc,j,i,3:5] = wsn[ihc,j,i,4] * .5
                    hsn[ihc,j,i,3:5] = hsn[ihc,j,i,4] * .5
                    tsn[ihc,j,i,3:5] = tsn[ihc,j,i,4]


                # This is now done upon loading LANDICE_IC (LISnow.F90)
                ## Remove extra snow layer, which causes problems if it is too thin.
                #params = modelexe.Lisnowbase_Mod.Lisnowparams()
                #params.max_nl = nl_ice
                #params.target_nl_ice = nl_ice
                #fexec(lambda: modelexe.Lisnowbase_Mod.
                #    snow_redistr(params,
                #        dz[ihc,j,i,:],
                #        wsn[ihc,j,i,:],
                #        hsn[ihc,j,i,:],
                #        nl_ice, 0, 1.0)
                #)

            

    # -------------------------------------------------------------
    # -------------------------------------------------------------
    # 7) Write the GIC file
    with netCDF4.Dataset(igic) as ncin:
        with netCDF4.Dataset(ogic, 'w', format='NETCDF3_CLASSIC') as ncout:

            # ---- Store provenance in standard way...
            files = ncout.createVariable('files', 'i')
            install_path = ncout.createVariable('install_paths', 'i')
            files.source = os.path.abspath(igic)

            ncc = copy_nc(ncin, ncout)

            ncc.createDimension('nhc', nhc)
            ncc.createDimension('nlice', nlice)
            ncc.copyDimensions('jm', 'im')

            new_ice_var = lambda name : \
                ncc.createVariable(name, 'd', ('nhc', 'jm', 'im', 'nlice'))

            var = new_ice_var('dz')
            var[:] = dz[:]
            var.units = 'm^3 m-2'
            var.description = 'Volume of ice layers'

            var = new_ice_var('wsn')
            var[:] = wsn[:]
            var.units = 'kg m-2'
            var.description = 'Mass of ice layers'

            var = new_ice_var('hsn')
            var[:] = hsn[:]
            var.units = 'J m-2'
            var.description = 'Enthalpy of ice layers'

            # tsn
            var = new_ice_var('tsn')
            var[:] = tsn[:]
            var.units = 'degC'
            var.description = 'Temperature of layer.  Diagnostic only, for debugging the this input file.'

            ncc.define_vars(
                [x for x in ncin.variables.keys() if x not in {'snowli', 'tlandi'}])

            ncc.copy_data()

    #print(sum(sum(np.logical_and(snowli[0,:,:] == 0, fgice > 0))))


