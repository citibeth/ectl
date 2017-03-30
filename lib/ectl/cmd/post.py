import os
import ectl
import re
import sys
from ectl import iso8601,launchers
import ectl.rundir
import netCDF4
import giss.ncutil
import numpy as np
import scipy.sparse
import collections
from modele.constants import SHW,SHI,LHM
from contextlib import contextmanager

class IndexSet(object):
    """Copy of C++ IndexSet"""
    def __init__(self, *keys):
        self._key_to_ix = dict()
        self._ix_to_key = list()
        for key in keys:
            self._key_to_ix[key] = len(self._ix_to_key)
            self._ix_to_key.append(key)

    def __len__(self):
        return len(self._ix_to_key)
    def __contains__(self, key):
        return key in self._key_to_ix
    def __getitem__(self, key):
        if isinstance(key, int):
            return self._ix_to_key[key]
        else:
            return self._key_to_ix[key]
    def __iter__(self):
        return iter(self._ix_to_key)


def transform_matrix(outputs, inputs, scalars, tuples, scalar_values):
    tensor = np.zeros((len(outputs), len(inputs), len(scalars)))
    for os,iis,ss,val in tuples:
        tensor[outputs[os], inputs[iis], scalars[ss]] = val

    scalar_vec = np.zeros(len(scalars))
    for key,val in scalar_values.items():
        scalar_vec[scalars[key]] = val

#    print('tensor', tensor.shape)
#    print('scalar', scalar_vec.shape)
    matrix0 = np.tensordot(tensor, scalar_vec, axes=1)

    data = list()
    row_ind = list()
    col_ind = list()
    for i in range(0,matrix0.shape[0]):
        for j in range(0,matrix0.shape[1]):
            val = matrix0[i,j]
            if val != 0:
                data.append(val)
                row_ind.append(i)
                col_ind.append(j)
    return scipy.sparse.csr_matrix((data, (row_ind, col_ind)), shape=matrix0.shape)

# -------------------------------------------------------------------------
@contextmanager
def np_seterr(**kwargs):
    # http://stackoverflow.com/questions/15192637/runtimewarning-invalid-value-encountered-in-maximum
    errs = np.geterr()
    np.seterr(**kwargs)
    yield
    np.seterr(**errs)

    
# -------------------------------------------------------------------------
def process_gcm_out(ifname):
    """Post-process files named gcm-out-*.nc"""

    copy_vars = {'timespan', 'timespan.txt'}
    inputs = IndexSet('runo', 'eruno', 'deltah', 'massxfer', 'enthxfer', 'volxfer')
#    outputs = IndexSet('runo', 'runo_T', 'runo_liquid', 'deltah', 'massxfer', 'massxfer_T', 'massxfer_liquid', 'volxfer')
    scalars = IndexSet('1', 'bydt')
    ounits = collections.OrderedDict([
        ('runo', 'kg m-2 y-1'),
        ('runo_T', 'degC'),
        ('runo_liquid', '1'),
        ('deltah', 'W m-2'),
        ('massxfer', 'kg m-2 y-1'),
        ('massxfer_T', 'degC'),
        ('massxfer_liquid', '1'),
        ('volxfer', 'm^3 m-2 y-1')
    ])
    outputs = IndexSet(*ounits.keys())

    with netCDF4.Dataset(ifname, 'r') as ncin:

        timespan = ncin.variables['timespan'][:]

        # Check for a dummy file
        if timespan[1] == timespan[0]:
            return

        sec_in_yr = 86400. * 365.

        matrix = transform_matrix(outputs, inputs, scalars, (
            ('runo', 'runo', 'bydt', sec_in_yr),    # [kg m-2 y-1]
            ('deltah', 'deltah', 'bydt', 1.),        # [J m-2]
            ('massxfer', 'massxfer', 'bydt', sec_in_yr),    # [kg m-2 y-1]
            ('volxfer', 'volxfer', 'bydt', sec_in_yr)),    # [m^3 m-2 y-1]
            {'1' : 1., 'bydt' : 1./(timespan[1] - timespan[0])})

        ofname = get_ofname(ifname)
        print('process_gcm_out', ifname, ofname)

        with netCDF4.Dataset(ofname, 'w') as ncout:
            nco = giss.ncutil.copy_nc(ncin, ncout,
                var_filter = lambda x : x if x in copy_vars else None)

            # Copy all dimensions
            nco.copyDimensions(*list(ncin.dimensions.keys()))

            # Copy certain variables
            nco.define_vars()

            # Create all other variables
            dim_names = ncin.variables[inputs[0]].dimensions
            for ovname in outputs:
                units = None
                if ovname in ounits:
                    units = ounits[ovname]
                elif ovname in ncin.variables and hasattr(ncin.variables[ovname], 'units'):
                    units = ncin.variables[ovname].units
                ovar = ncout.createVariable(ovname, 'd', dim_names, zlib=True)
                if units is not None:
                    ovar.units = units

            # ---------- Linear Transformations of Input to Output
            dims = [len(ncin.dimensions[x]) for x in dim_names]
            ivals = np.zeros([len(inputs)] + dims)
            for i in range(0,len(inputs)):
                ivals[i,:] = ncin.variables[inputs[i]][:]

            ivals2 = ivals.reshape((ivals.shape[0], -1))
            ovals2 = matrix.dot(ivals2)
            ovals = ovals2.reshape([len(outputs)] + dims)

            # ----------- Non-linear transformations of input to output variables
#            with np_seterr(invalid='ignore'):
#           ovals[outputs['eruno'],:] = ivals[inputs['eruno'],:] / ivals[inputs['runo'],:]
#                ovals[outputs['enthxfer'],:] = ivals[inputs['enthxfer'],:] / ivals[inputs['massxfer'],:]

            tsn,isn = hsn_to_tsn(ivals[inputs['eruno'],:], ivals[inputs['runo'],:])
            ovals[outputs['runo_T'],:] = tsn[:]
            ovals[outputs['runo_liquid'],:] = isn[:]

            tsn,isn = hsn_to_tsn(ivals[inputs['enthxfer'],:], ivals[inputs['massxfer'],:])
            ovals[outputs['massxfer_T'],:] = tsn[:]
            ovals[outputs['massxfer_liquid'],:] = isn[:]



            # ------------- Write Data
            for i in range(0,len(outputs)):
                ovar = ncout.variables[outputs[i]]
                ovar[:] = ovals[i,:]

            nco.copy_data()


# -------------------------------------------------------------------------
class UpToDateException(Exception):
    pass

def get_ofname(ifname):
    iroot,iext = os.path.splitext(ifname)
    ofname = iroot + '-x' + iext

    idt = os.path.getmtime(ifname)
    try:
        odt = os.path.getmtime(ofname)
    except:
        odt = 0

    # Check if we need to regenerate the file
#    if odt > idt:
#       raise UpToDateException(ofname)
    return ofname

# -------------------------------------------------------------------------
patterns = re.compile(
    '(?P<process_gcm_out>gcm-out-\d\d\d\d\d\d\d\d.nc)'
)

def post_process(run_dir):
    for fname in os.listdir(run_dir):
        match = patterns.match(fname)
        if match is None:
            continue
        func_name = match.lastgroup
        mod = sys.modules[__name__]    # current module
        try:
            getattr(mod, func_name)(os.path.join(run_dir, fname))
        except UpToDateException:
            pass

# -------------------------------------------------------------------------
description = 'Post-process a run.  May be re-started later.'

def setup_parser(subparser):
    subparser.add_argument('run', nargs='?', default='.',
        help='Directory of run to post-process')

def post(parser, args, unknown_args):
    if len(unknown_args) > 0:
        raise ValueError('Unkown arguments: %s' % unknown_args)

    run = os.path.abspath(args.run)

    status = ectl.rundir.Status(run)
    if (status.status == launchers.NONE):
        sys.stderr.write('Error: No valid run in directory %s\n' % run)
        sys.exit(-1)

    post_process(args.run)

