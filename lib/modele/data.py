import copy
import numpy as np
from giss.functional import *
from giss import functional,ncutil
from modele.constants import *
import itertools

# -----------------------------------------------------------
def hsn_to_tsn(dataset, shsn, swsn, stsn, sisn):
    """Convert (enthalpy, mass) to (T, ice fraction)
    dataset:
        An xarray.DataSet object containing enthalpy and mass variables
    shsn:
        Key in dataset for the enthalpy variable [J m-2]
    swsn:
        Key in dataset for the mass variable [kg m-2]
    stsn: OUT
        Key to store temperature under [degC]
    sisn: OUT
        Key to store ice fraction under [1]
    """

    # -------------- Work on the attributes
    wsn_attrs = dataset.attrs[swsn]
    hsn_attrs = dataset.attrs[shsn]

    attrs0 = intersect_dicts(wsn_attrs, hsn_attrs)

    tsn_attrs0 = copy.copy(attrs0)
    tsn_attrs0[('var', 'name')] = 'tsn'
    tsn_attrs0[('var', 'units')] = 'degC'

    isn_attrs0 = copy.copy(attrs0)
    isn_attrs0[('var', 'name')] = 'isn'
    isn_attrs0[('var', 'units')] = '1'

    dataset.attrs[stsn] = tsn_attrs0
    dataset.attrs[sisn] = isn_attrs0

    def hsn_to_tsn_data():
        # ---------------------- Work on the data
        hsn = dataset.data[shsn]
        wsn = dataset.data[swsn]
        tsn = np.zeros(hsn.shape)
        isn = np.zeros(hsn.shape)

        hsn0 = hsn.reshape(-1)
        wsn0 = wsn.reshape(-1)
        tsn0 = tsn.reshape(-1)
        isn0 = isn.reshape(-1)

        tsn0[:] = np.nan
        isn0[:] = np.nan

        # From LISnowCol.F90
        # All water
        cond0 = (hsn0 > 0)
        tsn0[cond0] = hsn0[cond0] / (wsn0[cond0] * SHI)
        isn0[cond0] = 0

        # Temperate ice
        cond1 = np.logical_and(hsn0 > -wsn0*LHM, hsn0 <= 0)
        tsn0[cond1] = 0
        isn0[cond1] = -hsn0[cond1] / (wsn0[cond1] * LHM)

        # All ice
        cond2 = (hsn0 <= -wsn0*LHM)
        tsn0[cond2] = (hsn0[cond2] + wsn0[cond2]*LHM) / (SHI * wsn0[cond2])
        isn0[cond2] = 1

        dataset.data[stsn] = tsn
        dataset.data[sisn] = isn

    dataset.data.lazy[stsn] = hsn_to_tsn_data
    dataset.data.lazy[sisn] = hsn_to_tsn_data
# ---------------------------------------
def sum_to_depth_data(var, nl_ice, depth_dim, oshape, ranges, finalshape):
    """Zeroes out thins in var deeper than nl_ice)
    depth_dim: int
        Index of dimension indicating depth"""

    print('sum_to_depth_data', var.shape, oshape)
    ovar = np.zeros(oshape)
    for ix in itertools.product(*ranges):
        vix = var[ix]
        ovar[ix] = np.sum(var[ix])
    return ovar.reshape(finalshape)

@function()
def sum_to_depth1(fetch, nl_ice, sdepth_dim):
    print('fetch', type(fetch.attrs))
    attrs0 = fetch.attrs()
    data1 = fetch.data

    ashape = attrs0[('fetch', 'shape')]
    adims = attrs0[('fetch', 'dimensions')]
    depth_dim = adims.index(sdepth_dim)

    ranges = []
    oshape = []
    odims = []
    finalshape = []
    for i in range(0, len(ashape)):
        if i == depth_dim:
            ranges.append((slice(None),))    # == [:]
            oshape.append(1)
        else:
            ranges.append(range(0,ashape[i]))
            oshape.append(ashape[i])
            finalshape.append(ashape[i])
            odims.append(adims[i])

    attrs0[('fetch', 'shape')] = tuple(finalshape)
    attrs0[('fetch', 'dimensions')] = tuple(odims)

    data = functional.lift_once(sum_to_depth_data,
        fetch.data, nl_ice.data,
        depth_dim, oshape, ranges, finalshape)

    return ncutil.FetchTuple(fetch.attrs, data)
sum_to_depth2 = sum_to_depth1
#sum_to_depth2 = functional.lift()(sum_to_depth1)
