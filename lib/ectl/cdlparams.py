from __future__ import print_function
import ectl.paths
from spack.util import executable
import netCDF4
import os
from ectl import pathutil
from giss import ioutil

def resolve_cdls_in_dir(config_dir, download_dir=None):
    """Converts .cdl auxillary Rundeck files to .nc; and resolves input
    files in them as well."""

    cdl_files = [
        os.path.join(config_dir, x)
        for x in os.listdir(config_dir)
        if x.endswith('.cdl')]

    good = True
    for ifname in cdl_files:
        ofname = os.path.splitext(ifname)[0] + '.nc'
        resolve_cdl(ifname, ofname, download_dir=download_dir)

    return good


def resolve_cdl(ifname, ofname, download_dir=None, keep_partial=False):
    """ifname:
        Input file name (xyz.cdl)
    ofname
        Output file name (xyz.nc)
    """
    ncgen = executable.which('ncgen')
    if ioutil.needs_regen((ofname,), (ifname,)):
        ncgen('-o', ofname, '-k', 'nc4', ifname)

        # Resolve input file paths
        # (see similar logic in rundeck/__init__.py)
        _good = True
        with netCDF4.Dataset(ofname, 'a') as nc:
            for var_name in nc.variables:
                var = nc.variables[var_name]
                for aname in var.ncattrs():
                    aval = getattr(var, aname)
                    if not isinstance(aval, str):
                        continue
                    if aval.startswith('input-file:'):
                        fname0 = aval[11:]
                        try:
                            fname1 = pathutil.search_or_download_file(
                                aname, fname0,
                                ectl.paths.default_file,
                                download_dir=download_dir)
                            setattr(var, aname, fname1)
                        except Exception as e:
                            # Errors were already reported in search_or_download_file
                            print(e)
                            _good = False
                    elif aval.startswith('output-file:'):
                        fname0 = aval[12:]
                        fname1 = os.path.abspath(fname0)
                        odir = os.path.split(fname1)[0]
                        try:
                            os.makedirs(odir)
                        except OSError:
                            pass
                        setattr(var, aname, fname1)
                    elif aval.startswith('output-dir:'):
                        fname0 = aval[11:]
                        fname1 = os.path.abspath(fname0)
                        try:
                            os.makedirs(fname1)
                        except OSError:
                            pass
                        setattr(var, aname, fname1)
        if not (_good or keep_partial):
            try:
                os.remove(ofname)
            except:
                pass
