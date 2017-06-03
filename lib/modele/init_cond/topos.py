import collections
import os
import argparse
import copy
import numpy as np
from giss import giutil
import icebin
from icebin import ibgrid
from giss.ncutil import copy_nc
import netCDF4
import scipy.sparse

from modele.constants import SHI,LHM,RHOI,RHOS,UI_ICEBIN,UI_NOTHING

# elev_mask = File name containing the PISM/MAR mask
SheetInfo = collections.namedtuple('SheetInfo', ('name', 'elevI'))



def concat_vector(B, A):
    """Adds non-NaN items of vector A to vector B.
    B should start out as all NaNs, they will be converted to 0 as needed."""
    nonanA = ~np.isnan(A)
    nanB = np.isnan(B)
    B[np.logical_and(nanB, nonanA)] = 0
    B[nonanA] += A[nonanA]

class ConcatCoo(object):

    def __init__(self):
        self.row = []
        self.col = []
        self.data = []
        self.shape = None

    def add(self, A):
        if self.shape is None:
            self.shape = A.shape
        else:
            if self.shape != A.shape:
                raise ValueError('Inconsistent shapes: {} vs {}'.format(self.shape, A.shape))

        self.row.append(A.row)
        self.col.append(A.col)
        self.data.append(A.data)

    def __call__(self):
        return scipy.sparse.coo_matrix((
            np.concatenate(self.data),
            (np.concatenate(self.row), np.concatenate(self.col))),
            shape=self.shape)


class Topos(object):
    def __init__(self, icebin_in, topo_in):
        """
        Args:
            topo_in:
                Name of original ModelE TOPO file
            icebin_in:
                Name of IceBin input file
            stieglitz:
                If True, generate initial conditions for Stieglitz model
        """
        self.icebin_in = icebin_in
        self.topo_in = topo_in

        self.mm = icebin.GCMRegridder(icebin_in)

        # ------- Set up dimensions and elevation classes
        self.icebin_in = icebin_in

        with netCDF4.Dataset(icebin_in) as nc:
            # General dimensions
            self.indexingHC = ibgrid.Indexing(nc, 'm.indexingHC')
            self.hcdefs_ice = nc.variables['m.hcdefs'][:]
            self.nhc_ice = len(nc.dimensions['m.nhc'])
            self.nA = getattr(nc.variables['m.gridA.info'], 'cells.nfull')
            self.nE_ice = self.nhc_ice * self.nA

            # Native area of grid cells'

            indexA_sub = nc.variables['m.gridA.cells.index'][:]
            areaA_sub = nc.variables['m.gridA.cells.native_area'][:]
            self.areaA = np.zeros(self.nA)
            self.areaA[indexA_sub] = areaA_sub    # Native area of full grid cell (on sphere)


        # ------- Define elevation class structure
        segments = list()

        # Segment 0: The legacy elevation class
        self.legacy_base = 0
        self.nlegacy = 1
        segments.append(('legacy', self.legacy_base))

        # Segment 1: Two elevation classes only: one for sea, one for land
        self.sealand_base = self.legacy_base + self.nlegacy
        self.nsealand = 2
        segments.append(('sealand', self.sealand_base))

        # Segment 2: Full elevation classes
        self.ec_base = self.sealand_base + self.nsealand
        segments.append(('ec', self.ec_base))

        # Total number of EC's across all segments
        self.nhc_gcm = self.ec_base + self.nhc_ice
        self.nE_gcm = self.nhc_gcm * self.nA


    def get_fractions(self, sheets):
        """Args:
            sheets: (SheetInfo,)
                The ice sheet to process.
        """
        ret = {}    # Dict of output values





        # -------- Assemble global matrices & vectors from per-sheet versions
        AvE_c = ConcatCoo()
        elevA = np.zeros((self.nA,)) + np.nan
        wAvE = np.zeros((self.nA,)) + np.nan
        for sheet in sheets:
            self.mm.set_elevI(sheet.name, sheet.elevI)
            rm = self.mm.regrid_matrices(sheet.name)
            wAvE_i,AvE_i,_ = rm.matrix('AvE', scale=True)()
            _     ,EvI_i,_ = rm.matrix('EvI', scale=True)()
            _     ,AvI_i,_ = rm.matrix('AvI', scale=True)()


            concat_vector(wAvE, wAvE_i)
            AvE_c.add(AvE_i)


            elevA_i = icebin.coo_multiply(AvI_i, sheet.elevI)
            concat_vector(elevA, elevA_i)

        AvE = AvE_c()

        # ----------------- elevI things were originally computed with
            for sheet in sheets:

        # ------------------ Read original surface area fractions
        with netCDF4.Dataset(self.topo_in) as nc:
            focean = nc.variables['focean'][:].reshape(-1)
            flake = nc.variables['flake'][:].reshape(-1)
            fgrnd = nc.variables['fgrnd'][:].reshape(-1)    # Alt: FEARTH0
            fgice = nc.variables['fgice'][:].reshape(-1)    # Alt: FLICE
            zatmo_m = nc.variables['zatmo'][:].reshape(-1)    # _m means [meters]

        # ------------- Set things on A grid
        _maskA = ~np.isnan(elevA)
        fgice[_maskA] = wAvE[_maskA] / self.areaA[_maskA]
        fgrnd = 1. - (flake + focean + fgice)
        fgrnd[fgrnd<0] = 0.
        focean = 1. - (flake + fgrnd + fgice)
        if not np.all(focean >= 0):
            print('focean', focean[focean<0])
            raise ValueError('FOCEAN went negative; take from some other land surface type')

        # Assume elevation=0 for non-ice-sheet areas.  This is OK for ocean portions,
        # not OK for bare land portions.
        zatmo_m[_maskA] = elevA[_maskA] * fgice[_maskA]

        # ---------------- Set things on E grid
        shapeE2 = (self.nhc_ice, self.nA)
        shapeE2_gcm = (self.nhc_gcm, self.nA)

        elevE = np.zeros((self.nE_gcm,)) + np.nan    # Elevation of each GCM elevation class
        elevE2 = elevE.reshape(shapeE2_gcm)
        fhc = np.zeros((self.nE_gcm,)) + np.nan
        fhc2 = fhc.reshape(shapeE2_gcm)
        underice = np.zeros((self.nE_gcm,)) + np.nan
        underice2 = underice.reshape(shapeE2_gcm)

        # ------- Segment 0: Legacy Segment
        # Compute the legacy elevation class, but don't include in sums
        fhc2[self.legacy_base,fgice != 0] = 1.   # Legacy ice for Greenland and Antarctica
        underice2[self.legacy_base,fgice != 0] = UI_NOTHING

        elevE2[self.legacy_base,:] = zatmo_m
        # Assume elevation=0 for non-ice-sheet areas.  This is OK for ocean portions,
        # not OK for bare land portions.
        elevE2[self.legacy_base,_maskA] = zatmo_m[_maskA]


        # ------- Segment 1: SeaLand Segment
        # ihc=0: Non-ice portion of grid cell at sea level

        # FHC is fraction of ICE-COVERED area in this elevation class
        # Therefore, FHC=0 for the sea portion of the SeaLand Segment
        # NOTE: fhc[self.sealand_base,_maskA] = 1.-fgice[_maskA]
        # We could do away with this EC altogether because it's not used.
        fhc2[self.sealand_base,_maskA] = 0.
        underice2[self.sealand_base,_maskA] = 0
        elevE2[self.sealand_base,_maskA] = 0.
        # ihc=1: Ice portion of grid cell at mean for the ice portion
        # FHC is fraction of ICE-COVERED area in this elevation class
        # Therefore, FHC=1 for the land portion of the SeaLand Segment
        # NOT: fhc[self.sealand_base+1,_maskA] = fgice[_maskA]
        fhc2[self.sealand_base+1,_maskA] = 1.
        underice2[self.sealand_base+1,_maskA] = UI_NOTHING
        elevE2[self.sealand_base+1,_maskA] = elevA[_maskA]

        # ---------- Segment 2: Full Elevation Classes

        for iA,iE,weight in zip(AvE.row, AvE.col, AvE.data):
            # iE must be contained within cell iA (local propety of matrix)
            iA2,ihc = self.indexingHC.index_to_tuple(iE)
            if iA2 != iA:
                raise ValueError('Matrix is non-local: iA={}, iE={}, iA2={}'.format(iA,iE,iA2))
            fhc2[self.ec_base+ihc,iA] = weight
            underice2[self.ec_base+ihc,iA] = UI_ICEBIN

        for i in range(0,self.nA):
            elevE2[self.ec_base:,i] = self.hcdefs_ice[:]



        # --------- Disable non-prognostic segments
        fhc2[self.legacy_base,:] *= 1e-30
        fhc2[self.sealand_base:self.sealand_base+self.nsealand,:] *= 1e-30

        # ---------- Return the values we've computed
        ret['areaA'] = self.areaA
        ret['focean'] = focean
        ret['flake'] = flake
        ret['fgrnd'] = fgrnd
        ret['fgice'] = fgice
        ret['zatmo_m'] = zatmo_m
        ret['fhc'] = fhc
        ret['underice'] = underice
        ret['elevE'] = elevE

        return ret
