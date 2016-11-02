import os
import collections
import copy
import subprocess
import functools
import datetime
import operator
import re

import numpy as np
import netCDF4
import cf_units

from giss import memoize,ioutil,ncutil,giutil,xaccess,gidate,checksum
from giss.functional import *
from giss import functional
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
    def __init__(self, _ofpat, section, acc_dir=None, params=dict()):
        """ofpat:
            Pattern to use for the output file name.
            Eg: /home/me/JUN1951.{section}E4F40.R.nc
        section:
            Section of ACC file we want (eg: 'aij', 'ijhc', etc)
        acc_dir:
            Directory to find corresponding acc files (if needed)
        params:
            Additional attributes to add to the params variable in the
            output NetCDF file (will not ovewrite).
        """

        ofpat = os.path.abspath(_ofpat)
        self.odir,leafpat = os.path.split(ofpat)
        ofname = os.path.join(self.odir,
            leafpat.format(section=section))
        ifname = os.path.join(self.odir if acc_dir is None else acc_dir,
            leafpat.format(section='acc'))

        ofname = os.path.abspath(ofname)
        ifname = os.path.abspath(ifname)

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
                    oparam.setncattr('topo_params_found',1)
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
def fetch_file(file_name, var_name, *index, region=None):
    """index:
        If the variable has elevation classes:
            (segment, <numeric indexing>)
            (segment = elevation class segment we're indexing into)
        If no elevation classes:
            Regular numeric indexing"""

    print('Fetching Data:', file_name, var_name, index, region)

    # ------ Get variable attributes
    kwargs = {'missing_threshold' : 1.e25}
    attrsW = ncutil.ncattrs(file_name, var_name)
    attrs = attrsW() # Unwrap

    # ------ Add ModelE parameters file to attributes...
    # (TODO: Look for I file in same directory if params not in the ijhc file)
    nc = ncutil.ncopen(file_name)
    for vname in ('param', 'cparam', 'iparam', 'rparam'):
        if vname in nc.variables:
            Ivar = nc.variables[vname]
            for key in Ivar.ncattrs():
                attrs[('param', key)] = getattr(Ivar, key)

    # ------- Add TOPO parameters to the attributes....
    if ('param', 'topo_params_found') not in attrs:
        # Copy metadata out of the TOPO file (if we can still find it)
        TOPO = attrs[('param','_file_topo')]
        if os.path.exists(TOPO):
            attrs[('param', 'topo_params_found')] = 1
            for key,value in read_topo(TOPO).items():
                attrs[('param', key)] = value

    # --------- Adjust indexing based on the ec_segment
    dims = {d:i for i,d in enumerate(attrs[('var', 'dimensions')])}
    ihp_d = giutil.get_first(dims, ('nhp', 'nhc'))

    if ihp_d is not None:
        # ------ Variable has elevation classes
        ec_segment = index[0]
        if not isinstance(ec_segment, str):
            raise ValueError('Error in indexing; did you forget to add an ec_segment argument?')
        attrs[('fetch', 'ec_segment')] = ec_segment

        # This is elevation-classified; first index will be a segment string
        segment_names = attrs[('param', 'segment_names')].split(',')
        segment_ix = segment_names.index(ec_segment)

        # Rest of index is indices into multi-dim variable
        xindex = list(copy.copy(index[1:]))
        segment_bases = attrs[('param', 'segment_bases')]

        subdim = (segment_bases[segment_ix], segment_bases[segment_ix+1])
        xindex[ihp_d] = xaccess.reslice_subdim(xindex[ihp_d], subdim)

        # Determine the grid this is on
        if ec_segment == 'ec':
            attrs[('fetch', 'grid')] = 'elevation'
            attrs[('fetch', 'grid', 'correctA')] = True
        elif ec_segment == 'legacy':
            attrs[('fetch', 'grid')] = 'atmosphere'
        else:
            # Don't know what grid it's on
            pass
    else:
        # ------- Variable has no elevation classes
        xindex = index

        if ('jm' in dims and 'im' in dims and abs(dims['jm']-dims['im']) == 1):
            # jm,im detected...  (RSF files)
            attrs[('fetch', 'grid')] = 'atmosphere'
        elif ('lat' in dims and 'lon' in dims and abs(dims['lat']-dims['lon']) == 1):
            # lat,lon detected... (scaled files)
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

    return ncutil.FetchTuple(
        attrsW,
            bind(ncutil.ncdata, file_name, var_name, *xindex, **kwargs))
#        ncutil.data_to_xarray(attrsW,
#            bind(ncutil.ncdata, file_name, var_name, *xindex, **kwargs)))

# ----------------------------------------------------------------
months_itoa = ('<none>', 'JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC')
months_atoi = {s:i for i,s in enumerate(months_itoa)}

_dateREs = r'(\d*)(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)(\d+)'
_sectionsREs = r'(acc|rsf|adiurn|agc|aij|aijk|aijl|aijmm|aj|ajl|areg|consrv|icij|ijhc)'

# Regular expression matches ModelE output filenames
_fileRE = re.compile(_dateREs + r'\.' + _sectionsREs + r'(.*?)\.nc')

def _extract_if_equal(mylist, ix):
    """Returns lst[0][ix] if list[n][ix] is equal for all n.
    Else returns None."""
    if len(set(item[ix] for item in mylist)) == 1:
        return mylist[0][ix]
    else:
        return None


ModelEFile = collections.namedtuple('ModelEFile', ('rundeck', 'section', 'date', 'fname'))

@memoize.local()
def get_groups(dir, filter_fn = lambda rundeck, section, date, fname : True):

    """Lists the ModelE files in a directory.
    dir:
        Directory to list files in
    filter_fn:
        Tells which files to keep.  See filter_group() below.
    Returns an OrderedDict of OrderedDicts (all sorted):
        groups[(rundeck,section)][date] -->
            namedtuple(rundeck,section, date, fname)
    """

    # Poke around, see the name pattern for files in this directory
    files = list()
    for leaf in os.listdir(dir):
        match = _fileRE.match(leaf)
        if match is None:
            continue

        # Parse out the parts of the ModelE filename
        sday = match.group(1)
        day = int(sday) if len(sday) > 0 else 1
        month = months_atoi[match.group(2)]
        year = int(match.group(3))
        date = gidate.Date(year, month, day)

        section  = match.group(4)
        rundeck = match.group(5)

        # Only keep the files we like
        fname = os.path.join(dir, leaf)
        rec = ModelEFile(rundeck, section, date, fname)
        if filter_fn(*rec):
            files.append(rec)

    groups = collections.OrderedDict()    # One dict per (rundeck, section)
    if len(files) == 0:
        return groups


    # Separate files list by (rundeck, section)
    files.sort()
    files.append(ModelEFile(None,None,None,None))    # Sentinel

    accum = collections.OrderedDict()
    accum[files[0].date] = files[0]    # accum[date] = rec
    accum0 = files[0]
    for rec in files[1:]:
        if (rec[0:2] != accum0[0:2]):
            groups[tuple(accum0[0:2])] = accum
            accum = collections.OrderedDict()
            accum0 = rec
        accum[rec.date] = rec
        
    return groups


def get_one_group(*args, **kwargs):
    """Returns files from a single group from get_groups(); or throws exception"""
    groups = get_groups(*args, **kwargs)

    # Quit if our filter returned files from >1 group
    if len(groups) > 1:
        raise ValueError('More than one group of files found in {}'.format(dir))
    return next(iter(groups.items()))    # (rundeck, section), files

@memoize.local()
class filter_group(object):
    """Filter pattern so rundeck==rundeck, section==section and date0<=date<date1"""
    def __init__(self, rundeck=None, section=None, date0=None, date1=None):
        self.rundeck = rundeck
        self.section = section
        self.date0 = date0
        self.date1 = date1

    hash_version = 0
    def hashup(self,hash):
        checksum.hashup(hash, (self.rundeck, self.section, self.date0, self.date1))

    def __call__(self, rundeck, section, date, fname):
        if self.rundeck is not None and self.rundeck != rundeck:
            return False
        if self.section is not None and self.section != section:
            return False
        if self.date0 is not None and date < self.date0:
            return False
        if self.date1 is not None and date >= self.date1:
            return False
        return True

# Pre-defined filter to give everything
_all_files = filter_group()

@function()
def _fetch_from_dir(mydir, filter_fn, var_name, year, month, *index, **kwargs):
    """Fetches data out of a rundir, treating the entire rundir like a dataset.
    run:
        A ModelE run directory.
    run_name:
        The trailing part of files (or None, if auto-detect)
        Eg: MAR1964.ijhcE027testEC-ec.nc, run_name = 'E027testEC-ec'
    """
    if filter_fn is None:
        filter_fn = _all_files

    # Read the files out of the directory
    _,files = get_one_group(mydir, filter_fn=filter_fn)

    # Get the filename (if the file exists)
    date = gidate.Date(year, month,1)
    file = files[date]

    ret = fetch_file(file.fname, var_name, *index, **kwargs)
    attrs = ret.attrs()
    attrs[('fetch', 'date')] = date
    attrs[('fetch', 'rundeck')] = file.rundeck
    attrs[('fetch', 'section')] = file.section

    return ret

# ----------------------------------------------------------------
def _get_scaled_fname(mydir, section, year, month):
    """Finds a scaled file inside of a ModelE run directory"""
    #filter_fn = filter_group(section=section)

    # ----- Determine what kind of directory we were given: ACC or scaled.
    groups = get_groups(mydir, filter_group(section='acc'))
    if len(groups) == 1:
        # mydir contains ACC files; glean the rundeck name off of that
        rundeck,_ = next(iter(groups.keys()))
        acc_dir = mydir
        scaled_dir = os.path.join(acc_dir, 'scaled')
    elif len(groups) == 0:
        # mydir contains no ACC files; let's see if it contains scaled files
        # (If no scaled or acc files, this will raise)
        (rundeck, _),_ = get_one_group(mydir, filter_group(section=section))
        acc_dir = None
        scaled_dir = mydir
    else:
        raise ValueError('Found more than one group in {}'.format(mydir))

    # Determine what the scaled file SHOULD be called
    scaled_pat = '{month}{year:04d}.{section}{rundeck}.nc'.format(
        month=months_itoa[month],
        year=year, section='{section}', rundeck=rundeck)
    scaled_leaf = scaled_pat.format(section=section)

    # Look for scaled file pre-existing in scaled_dir dir (we didn't put it there)
    if acc_dir is None:    # Just a plain scaled dir
        fname = os.path.join(scaled_dir, scaled_leaf)
        if os.path.exists(fname):
            return fname
        raise Exception('Cannot find file {} in scaled directory {}'.format(scaled_leaf, scaled_dir))

    # Create it in the scaled/ directory
    return scaleacc(
        os.path.join(scaled_dir, scaled_pat),
        section, acc_dir=acc_dir)

@function()
def fetch_from_dir(mydir, section, var_name, year, month, *index, **kwargs):

    if section == 'acc' or section == 'rsf':
        # Fetch an unscaled file; either it's there or it's not
        return _fetch_from_dir(mydir, filter_group(section=section),
            var_name, year, month, *index, **kwargs)
    else:
        # Fetch a scaled file; can run scaleacc
        fname = _get_scaled_fname(mydir, section, year, month)

        ret = fetch_file(fname, var_name, *index, **kwargs)
        attrs = ret.attrs()
        attrs[('fetch', 'date')] = gidate.Date(year, month)

        return ret

# ----------------------------------------------------------------
