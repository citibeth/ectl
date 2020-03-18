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
GlobalRegrids = collections.namedtuple('GlobalRegrids',
    ('AvE', 'elevA', 'wAvE'))


def concat_vector(B, A):
    """Adds non-NaN items of vector A to vector B.
    B should start out as all NaNs, they will be converted to 0 as needed."""
    nonanA = ~np.isnan(A)
    nanB = np.isnan(B)
    B[np.logical_and(nanB, nonanA)] = 0
    B[nonanA] += A[nonanA]

def get_global_regrids(mm, sheets, nA):
    # -------- Assemble global matrices & vectors from per-sheet versions
    AvE_c = ConcatCoo()
    elevA = np.zeros((nA,)) + np.nan
    wAvE = np.zeros((nA,)) + np.nan
    for sheet in sheets:
        mm.set_elevI(sheet.name, sheet.elevI)
        rm = mm.regrid_matrices(sheet.name)
        wAvE_i,AvE_i,_ = rm.matrix('AvE', scale=True)()
        _     ,EvI_i,_ = rm.matrix('EvI', scale=True)()
        _     ,AvI_i,_ = rm.matrix('AvI', scale=True)()


        concat_vector(wAvE, wAvE_i)
        AvE_c.add(AvE_i)


        elevA_i = icebin.coo_multiply(AvI_i, sheet.elevI)
        concat_vector(elevA, elevA_i)

    AvE = AvE_c()

    return GlobalRegrids(AvE, elevA, wAvE)


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

class ToposSuper(object):
    def read_icebin_in(self, icebin_in):
        self.mm = icebin.GCMRegridder(icebin_in)

        # ------- Set up dimensions and elevation classes
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

    def setup_segments(self):

        # ------- Define elevation class structure
        segments = list()

        # Segment 0: The legacy elevation class
        self.legacy_base = 0
        self.nlegacy = 1    # [all ice in cell + ocean] * 1e-30
        segments.append(('legacy', self.legacy_base))

        # Segment 1: Separate out icecap, dynamic ice
        self.sealand_base = self.legacy_base + self.nlegacy
        self.icecap_ec = self.sealand_base + 0
        self.dynice_ec = self.sealand_base + 1
        self.nsealand = 2
        segments.append(('sealand', self.sealand_base))

        # Segment 2: Full elevation classes
        self.ec_base = self.sealand_base + self.nsealand
        segments.append(('ec', self.ec_base))

        # Total number of EC's across all segments
        self.nhc_gcm = self.ec_base + self.nhc_ice
        self.nE_gcm = self.nhc_gcm * self.nA

    def computeE(self, ficecap, eicecap, fdynice, edynice, fgrnd, egrnd,
        focean, flake,
        regrids):

        ficecap[abs(ficecap)<1e-14] = 0
        fdynice[abs(fdynice)<1e-14] = 0
        fgrnd[abs(fgrnd)<1e-14] = 0


        mask_icecap = (ficecap != 0)
        mask_grnd = (fgrnd != 0)
        print('mask_grnd1 sum', sum(mask_grnd))
        mask_dynice = ~np.isnan(regrids.elevA)    # A grid cells touched by ice sheet

        # ---------------- Set things on E grid
        shapeE2 = (self.nhc_ice, self.nA)
        shapeE2_gcm = (self.nhc_gcm, self.nA)

        elevE = np.zeros((self.nE_gcm,)) + np.nan    # Elevation of each GCM elevation class
        elevE2 = elevE.reshape(shapeE2_gcm)
        fhc = np.zeros((self.nE_gcm,)) + np.nan
        fhc2 = fhc.reshape(shapeE2_gcm)
        underice = np.zeros((self.nE_gcm,)) + np.nan
        underice2 = underice.reshape(shapeE2_gcm)

        # ------- Segment 1: ocean,icecap
        # ihc=0: Non-ice portion of grid cell at sea level

        # icecap_ec
        # focean is zero elevation; assume fgrnd and ice are same elevation
        # This is initial TOPO, so no sharing of icecap & dynice
        fhc2[self.icecap_ec,mask_icecap] = ficecap[mask_icecap]
        underice2[self.icecap_ec,mask_icecap] = UI_NOTHING
        elevE2[self.icecap_ec,:] = eicecap

        # dynice_ec (Summary diagnostic EC of all the individual EC's)
        fhc2[self.dynice_ec,mask_dynice] = fdynice[mask_dynice] * 1e-30
        underice2[self.dynice_ec,mask_dynice] = UI_NOTHING
        elevE2[self.dynice_ec,:] = edynice

        # ------- Segment 0: Legacy Segment
        # Compute the legacy elevation class, but don't include in sums
        # Assumes non-ice areas have elevation = 0
        fhc2[self.legacy_base,:] = (ficecap + fdynice) * 1e-30
        underice2[self.legacy_base,:] = UI_NOTHING

        zatmo_m = np.zeros(self.nA)

        print('---------- BEGIN computeE()')
        val = egrnd[mask_grnd] * fgrnd[mask_grnd]
        print('NaN: grnd', np.any(np.isnan(val)), np.any(np.isnan(egrnd[mask_grnd])), np.any(np.isnan(fgrnd[mask_grnd])))
        if np.any(np.isnan(egrnd[mask_grnd])):
            print('egrnd2 is NaN')
#        if np.any(np.isnan(val)):
#            print('NaN: grnd')
        zatmo_m[mask_grnd] += val

        val = eicecap[mask_icecap] * ficecap[mask_icecap]
        if np.any(np.isnan(val)):
            print('NaN: icecap')
        zatmo_m[mask_icecap] += val

        val = edynice[mask_dynice] * fdynice[mask_dynice]
        if np.any(np.isnan(val)):
            print('NaN: dynice')
        zatmo_m[mask_dynice] += val


#        zatmo_m[mask_icecap] += eicecap[mask_icecap] * ficecap[mask_icecap]
#        zatmo_m[mask_dynice] += edynice[mask_dynice] * fdynice[mask_dynice]

        mask = (fhc2[self.legacy_base,:] != 0)
        elevE2[self.legacy_base,mask] = zatmo_m[mask]

        # ---------- Segment 2: Full Elevation Classes
        AvE = regrids.AvE
        for iA,iE,weight in zip(AvE.row, AvE.col, AvE.data):
            # iE must be contained within cell iA (local propety of matrix)
            iA2,ihc = self.indexingHC.index_to_tuple(iE)
            if iA2 != iA:
                raise ValueError('Matrix is non-local: iA={}, iE={}, iA2={}'.format(iA,iE,iA2))
            fhc2[self.ec_base+ihc,iA] = weight * (fdynice[iA] / (fdynice[iA] + ficecap[iA]))
            underice2[self.ec_base+ihc,iA] = UI_ICEBIN

        for i in range(0,self.nA):
            elevE2[self.ec_base:,i] = self.hcdefs_ice[:]


        ftotal = fgrnd + ficecap + fdynice + focean + flake
 

        # ---------- Return the values we've computed
        ret = {}
        ret['areaA'] = self.areaA
        ret['focean'] = focean
        ret['flake'] = flake
        ret['fgrnd'] = fgrnd
        ret['ficecap'] = ficecap
        ret['fdynice'] = fdynice
        ret['fgice'] = ficecap + fdynice
        ret['ftotal'] = ftotal
        ret['zatmo_m'] = zatmo_m
        ret['fhc'] = fhc
        ret['underice'] = underice
        ret['elevE'] = elevE
        ret['egrnd'] = egrnd
        ret['eicecap'] = eicecap
        ret['edynice'] = edynice

        return ret



class ToposInitial(ToposSuper):
    """Use the first time you're setting up TOPOS stuff."""

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
        self.read_icebin_in(icebin_in)
        self.setup_segments()

    def get_fractions(self, sheets):
        """Args:
            sheets: (SheetInfo,)
                The ice sheet to process.
        """
        mm = icebin.GCMRegridder(self.icebin_in)
        regrids = get_global_regrids(mm, sheets, self.nA)

        # ------------------ Read original surface area fractions
        focean = np.zeros(self.nA)
        flake = np.zeros(self.nA)
        fgrnd = np.zeros(self.nA)
        ficecap = np.zeros(self.nA)
        zatmo_m = np.zeros(self.nA)

        with netCDF4.Dataset(self.topo_in) as nc:
            focean[:] = nc.variables['focean'][:].reshape(-1)
            flake[:] = nc.variables['flake'][:].reshape(-1)
            fgrnd[:] = nc.variables['fgrnd'][:].reshape(-1)    # Alt: FEARTH0
            ficecap[:] = nc.variables['fgice'][:].reshape(-1)    # non-ice-sheet ice
            zatmo_m[:] = nc.variables['zatmo'][:].reshape(-1)    # _m means [meters]
        fdynice = np.zeros(self.nA)

        # ------------- Divide ice into icecap vs. dynice
        mask_dynice = ~np.isnan(regrids.elevA)    # A grid cells touched by ice sheet
        ficecap[mask_dynice] = 0          # Ice sheet eliminates non-ice-sheet ice in cell
        fdynice[mask_dynice] = regrids.wAvE[mask_dynice] / self.areaA[mask_dynice]    # Dynamic ice

        # Make up elevation for bare-ground cells that didn't used to exist
        egrnd = np.zeros(self.nA) + np.nan    # Elevation
        eicecap = np.zeros(self.nA) + np.nan    # Elevation
        edynice = np.zeros(self.nA) + np.nan    # Elevation

        # Apportion original elevation equally between bare land and original ice
        elev_land = zatmo_m[:] / (1. - focean)    # Will be NaN over ocean
        mask = (fgrnd != 0)
        egrnd[mask] = elev_land[mask]
        mask = (ficecap != 0)
        eicecap[mask] = elev_land[mask]
        edynice[mask_dynice] = regrids.elevA[mask_dynice]

        # ------------ Finish stuff on A grid
        fgrnd = 1. - (flake + focean + ficecap + fdynice)

        fgrnd[abs(fgrnd)<1e-14] = 0
        lz = (fgrnd < 0)
        print('fgrnd < 0:', sum(lz))
        ficecap[lz] += fgrnd[lz]
        fgrnd[lz] = 0.

        # The remaining indicates that dynice covered some of what was
        # previously ocean.  Take away from either focean or fdynice,
        # depending on which ones is bigger
        for ix in np.where(ficecap < 0)[0]:
            if focean[ix] > fdynice[ix]:
                focean[ix] += ficecap[ix]
            else:
                fdynice[ix] += ficecap[ix]
            ficecap[ix] = 0

        mask = (fgrnd != 0)
        egrnd[np.logical_and(mask, np.isnan(egrnd))] = 0

        mask = (ficecap != 0)
        eicecap[np.logical_and(mask, np.isnan(eicecap))] = 0


#        ficecap = 1. - (flake + focean + fgrnd + fdynice)

#        focean = 1. - (flake + fgrnd + fgice)
#        if not np.all(focean >= 0):
#            print('focean', focean[focean<0])
#            raise ValueError('FOCEAN went negative; take from some other land surface type')
 
        return self.computeE(ficecap,eicecap, fdynice,edynice, fgrnd,egrnd, focean, flake, regrids)


class ToposSubsequent(ToposSuper):
    def __init__(self, icebin_in, ncout, topo0_itime, elevI):
        self.icebin_in = icebin_in
        self.ncout = ncout
        self.topo0_itime = topo0_itime
        self.elevI = elevI

        self.read_icebin_in(icebin_in)
        self.setup_segments()


    def get_fractions(self, sheets):
        """Args:
            sheets: (SheetInfo,)
                The ice sheet to process.
        """
        mm = icebin.GCMRegridder(self.icebin_in)
        regrids = get_global_regrids(mm, sheets, self.nA)

        # Read result of first call to ToposInitial()
        it = self.topo0_itime
        nc = self.ncout
        areaA0 = nc.variables['areaA'][it,:].reshape(-1)
        focean0 = nc.variables['focean'][it,:].reshape(-1)
        flake0 = nc.variables['flake'][it,:].reshape(-1)
        fgrnd0 = nc.variables['fgrnd'][it,:].reshape(-1)
        ficecap0 = nc.variables['ficecap'][it,:].reshape(-1)
        fdynice0 = nc.variables['fdynice'][it,:].reshape(-1)
        fgice0 = nc.variables['fgice'][it,:].reshape(-1)
        ftotal0 = nc.variables['ftotal'][it,:].reshape(-1)
        zatmo_m0 = nc.variables['zatmo_m'][it,:].reshape(-1)
        fhc0 = nc.variables['fhc'][it,:].reshape(-1)
        underice0 = nc.variables['underice'][it,:].reshape(-1)
        elevE0 = nc.variables['elevE'][it,:].reshape(-1)
        egrnd0 = nc.variables['egrnd'][it,:].reshape(-1)
        eicecap0 = nc.variables['eicecap'][it,:].reshape(-1)
        edynice0 = nc.variables['edynice'][it,:].reshape(-1)

        # Carry forward values from original TOPO
        ficecap = ficecap0
        fgrnd = fgrnd0
        focean = focean0
        flake = flake0

        # Figure out new fdynice, based on GrIS
        fdynice = np.zeros(self.nA)
        mask_dynice = ~np.isnan(regrids.elevA)    # A grid cells touched by ice sheet
        fdynice[mask_dynice] = regrids.wAvE[mask_dynice] / self.areaA[mask_dynice]    # Dynamic ice
        edynice = regrids.elevA



        diff = fdynice - fdynice0
        fgrnd -= diff

        lz = (fgrnd < 0)
        ficecap[lz] += fgrnd[lz]
        fgrnd[lz] = 0

        lz = (ficecap < 0)
        focean[lz] += ficecap[lz]
        ficecap[lz] = 0

        # New ground is at zero elevation
        egrnd = (egrnd0 * fgrnd0) / fgrnd

        # Icecap retains same average elevation it had
        eicecap = eicecap0

        return self.computeE(ficecap,eicecap, fdynice,edynice, fgrnd,egrnd, focean, flake, regrids)
