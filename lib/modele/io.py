import os
import copy
import subprocess
import functools
import datetime
import operator
import re

import numpy as np
import netCDF4
import cf_units

from giss import memoize,ioutil,ncutil,giutil,xaccess,gidate
from giss.functional import *
from giss.xaccess import *

from ectl import rundeck

"""Stuff having to do with output files of ModelE (i.e. acc files,
results of scaleac, etc."""


# -------------------------------------------------
def extract_I(fname, keys=None):
    """Given a ModelE output files (acc) or derivative thereof
    (aic, ijhc, etc)... determines the I file in place when that
    output files was created.

    This is a little heuristic.  But the general idea is as follows:

       0. See if the entire I file is encoded in the NetCDF file itself.
          This is the best.

       1. Look for an answer in files.I NetCDF attribute.  ModelE and
          scaleacc do not write these.  But a post-processing program
          could add them easily, based on file timestamps.  Once this
          is written, ModelE output files become portable...

       2. If it's an acc file, look at file timestamps to determine
          which log directory contains the appropriate I file.  If it's
          not an acc file, look for the corresponding acc file.

       3. 

    keys:
        The set of keys to look up.
        If a linked file is desired, use the key '_file_XXX'

    Returns:
        List of (key, value)
        Do dict(extract_I_from_output_file()) if you want this in a dict.
    """

    # For now... just look for an I file in the same directory.
    dir = os.path.split(fname)[0]
    rd = rundeck.load_I(os.path.join(dir, 'I'))

    return [(key, rd[key].parsed) for key in
        (rd.params.keys() if keys is None else keys)]

#    return rundeck.rundeck_to_dict()
# ---------------------------------------------------
_topo_keys = (
    ('files', 'icebin_in', '_file_icebin_in'),
    ('segments', 'names', 'segment_names'),
    ('segments', 'bases', 'segment_bases'))
@memoize.local()
def read_topo(topo_file):
    """Given a ModelE output file that was the result of an elevation
    class run, obtains the Icebin input file used for it."""

    ret = dict()
    with netCDF4.Dataset(topo_file, 'r') as nc:
        for vname, attrname, oname in _topo_keys:
            try:
                ret[oname] = getattr(nc.variables[vname], attrname)
            except:
                raise
                pass    # variable / value does not exist in this TOPO file
    return ret
# ---------------------------------------------------

@memoize.files()
class scaleacc(object):
    hash_version = 0
    def __init__(self, _ofpat, section, accdir=None, params=dict()):
        """ofpat:
            Pattern to use for the output file name.
            Eg: /home/me/JUN1951.{section}E4F40.R.nc
        section:
            Section of ACC file we want (eg: 'aij', 'ijhc', etc)
        accdir:
            Directory to find corresponding acc files (if needed)
        params:
            Additional attributes to add to the params variable in the
            output NetCDF file (will not ovewrite).
        """

        ofpat = os.path.abspath(_ofpat)
        self.odir,leafpat = os.path.split(ofpat)
        ofname = os.path.join(self.odir,
            leafpat.format(section=section))
        ifname = os.path.join(self.odir if accdir is None else accdir,
            leafpat.format(section='acc'))

        self.section = section
        self.params = params

        # Required by @memoize.files()
        self.inputs = [ifname]
        self.outputs = [(ofname, (ifname,))]
        self.value = self.outputs[0][0]

    def __call__(self):
        try:
            os.makedirs(self.odir)
        except Exception as e:
            # print(e)
            pass
        with ioutil.pushd(self.odir):
            cmd = ['scaleacc', self.inputs[0], self.section]
            subprocess.check_output(cmd)

        # Rewrite the scaled file, with additional info
        ofname = self.outputs[0][0]
        tmpname = ofname + '.tmp'
        os.rename(ofname, tmpname)

        try:
            # Copy the whole thing to NetCDF4 and add attributes
            with netCDF4.Dataset(ofname, 'w') as ncout:

                oparam = ncout.createVariable('param', 'i')

                # Copy our default parameters
                for key,val in self.params.items():
                    oparam.setncattr(key, val)

                # Copy metadata from ACC file
                with netCDF4.Dataset(self.inputs[0], 'r') as accin:
                    for vname in ('rparam', 'iparam', 'cparam'):
                        ivar = accin.variables[vname]
                        for key in ivar.ncattrs():
                            oparam.setncattr(key, ivar.getncattr(key))

                # Copy metadata out of the TOPO file (if we can still find it)
                TOPO = oparam.getncattr('_file_topo')
                if os.path.exists(TOPO):
                    for key,value in read_topo(TOPO).items():
                        oparam.setncattr(key, value)

                # Copy data from the temporary scaleacc output file
                with netCDF4.Dataset(tmpname, 'r') as ncin:
                    nccopy = ncutil.copy_nc(ncin, ncout)
                    nccopy.define_vars(zlib=True)
                    nccopy.copy_data()
        finally:
            os.remove(tmpname)

        return self.value
# --------------------------------------------------------
@function()
def fetch(file_name, var_name, *index, region=None):
    """index:
        If the variable has elevation classes:
            (segment, <numeric indexing>)
            (segment = elevation class segment we're indexing into)
        If no elevation classes:
            Regular numeric indexing"""

    print('*******************', file_name)

    # ------ Get variable attributes
    kwargs = {'missing_threshold' : 1.e25}
    attrsW = ncutil.ncattrs(file_name, var_name)
    attrs = attrsW() # Unwrap

    # ------ Add ModelE parameters file to attributes...
    # (TODO: Look for I file in same directory if params not in the ijhc file)
    nc = ncutil.ncopen(file_name)
    Ivar = nc.variables['param']
    for key in Ivar.ncattrs():
        attrs[('param', key)] = getattr(Ivar, key)

    # --------- Adjust indexing based on the ec_segment
    dims = {d:i for i,d in enumerate(attrs[('var', 'dimensions')])}
    ihp_d = giutil.get_first(dims, ('nhp', 'nhc'))

    if ihp_d is not None:
        # ------ Variable has elevation classes
        ec_segment = index[0]
        if not isinstance(ec_segment, str):
            raise ValueError('Error in indexing; did you forget to add an ec_segment argument?')
        attrs[('fetch', 'ec_segment')] = ec_segment

        # This is elevation-classified; first index will a segment string
        segment_names = attrs[('param', 'segment_names')].split(',')
        segment_ix = segment_names.index(ec_segment)

        # Rest of index is indexes into multi-dim variable
        xindex = list(copy.copy(index[1:]))
        segment_bases = attrs[('param', 'segment_bases')]

        subdim = (segment_bases[segment_ix], segment_bases[segment_ix+1])
        print('Index', index, ihp_d)
        xindex[ihp_d] = xaccess.reslice_subdim(xindex[ihp_d], subdim)

        # Determine the grid this is on
        if ec_segment == 'ec':
            attrs[('fetch', 'grid')] = 'elevation'
        elif ec_segment == 'legacy':
            attrs[('fetch', 'grid')] = 'atmosphere'
        else:
            # Don't know what grid it's on
            pass
    else:
        # ------- Variable has no elevation classes
        file_name = attrs[('fetch', 'file_name')]
        if 'aij' in os.path.split(file_name)[1]:
            # ------ Variable has no elevation classes
            xindex = index
            attrs[('fetch', 'grid')] = 'atmosphere'
        else:
            # Don't know what grid it's on
            pass

    # Add attributes based on a low-level ncdata fetch
    ncutil.add_fetch_attrs(attrs, file_name, var_name, *xindex, **kwargs)

    # The function to use, when/if we want a plotter for this.
    plotter_kwargs = {}
    if region is not None:
        plotter_kwargs['region'] = region
    attrs[('plotter', 'kwargs')] = plotter_kwargs
    attrs[('plotter', 'function')] = ('modele.plot', 'get_plotter') # Name of function

    return ncutil.FetchTuple(attrsW, bind(ncutil.ncdata, file_name, var_name, *xindex, **kwargs))


# -----------------------------------------
months_itoa = ('<none>', 'JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC')
months_atoi = {s:i for i,s in enumerate(months_itoa)}

_accRE = re.compile(r'(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)(\d\d\d\d)\.acc(.*?)\.nc')

@memoize.local()
class Rundir(object):
    def __init__(self, run):
        self.accdir = run
        self.month_files_dict = {}    # (year, month) : fname
        self.run_name = None

        # Poke around, see the name pattern for files in this directory
        for leaf in os.listdir(self.accdir):
            match = _accRE.match(leaf)
            if match is None:
                continue

            run_name = match.group(3)    # Rewrite every time; they'd better all be the same
            if self.run_name is not None and self.run_name != run_name:
                raise ValueError('More than one run_name in a rundir; HELP!  %s %s' % (self.run_name, run_name))
            self.run_name = run_name

            month = months_atoi[match.group(1)]
            year = int(match.group(2))
            fname = os.path.join(self.accdir, leaf)
            self.month_files_dict[gidate.Date(year, month)] = fname

        self.month_files = sorted(
            (dttuple, fname)
            for dttuple, fname in self.month_files_dict.items())

    def __getitem__(self, dttuple):
        return self.month_files_dict[dttuple]

    def items(self):
        return iter(self.month_files)

    def scaled_pat_leaf(self, year, month):
        return '%s%04d.{section}%s.nc' % \
            (months_itoa[month], year, self.run_name)

@function()
def fetch_rundir(run, section, var_name, year, month, *index, **kwargs):
    """Fetches data out of a rundir, treating the entire rundir like a dataset.
    run:
        A ModelE run directory."""
    rundir = Rundir(os.path.realpath(run))
    #scaled = os.path.join(run, 'scaled')

    scaled_fname = scaleacc(
        os.path.join(run, 'scaled', rundir.scaled_pat_leaf(year, month)),
        section, accdir=rundir.accdir)

    ret = fetch(scaled_fname, var_name, *index, **kwargs)
    attrs = ret.attrs()
    attrs[('fetch', 'date')] = (year, month)

    return ret

