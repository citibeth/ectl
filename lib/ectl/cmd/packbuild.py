from __future__ import print_function
import multiprocessing
import os
import hashlib
import argparse
import llnl.util.tty as tty
import ectl.util
import ectl
import ectl.cmd
from ectl import pathutil,rundir,xhash,srcdir,launchers
import ectl.config
import ectl.rundeck
from ectl.rundeck import legacy
import subprocess
import base64
import re
import datetime
import sys
from spack.util import executable
from giss import pyar

def setup_parser(subparser):
    subparser.add_argument('--src', '-s', action='store', dest='src',
        required=True,
        help='Top-level directory of ModelE source')

MODELE_CONTROL_FILES = [
    './CMakeLists.txt',
    './aux/CMakeLists.txt',
    './cmake/DefineCMakeDefaults.cmake',
    './cmake/DefinePlatformDefaults.cmake',
    './cmake/FindBlitz++.cmake',
    './cmake/FindCGAL.cmake',
    './cmake/FindFException.cmake',
    './cmake/FindFFTW.cmake',
    './cmake/FindGALAHAD.cmake',
    './cmake/FindGMP.cmake',
    './cmake/FindGSL.cmake',
    './cmake/FindMPI.cmake',
    './cmake/FindNetCDF4_C.cmake',
    './cmake/FindNetCDF4_CXX.cmake',
    './cmake/FindNetCDF4_Fortran.cmake',
    './cmake/FindNetCDF_CXX.cmake',
    './cmake/FindPETSc.cmake',
    './cmake/FindPISM.cmake',
    './cmake/FindPNetCDF.cmake',
    './cmake/FindPROJ4.cmake',
    './cmake/FindPackageHandleStandardArgs.cmake',
    './cmake/FindPackageMultipass.cmake',
    './cmake/FindUDUNITS2.cmake',
    './cmake/GLINT2_CMake_macros.cmake',
    './cmake/GetPrerequisites.cmake',
    './cmake/LibFindMacros.cmake',
    './cmake/ModelE_CMake_macros.cmake',
    './cmake/PISM_CMake_macros.cmake',
    './cmake/PreventInSourceBuild.cmake',
    './cmake/ProcessCommandLineOptions.cmake',
    './cmake/ResolveCompilerPaths.cmake',
    './cmake/listContains.cmake',
    './cmake/scripts/rundeck_to_cmake.py',
    './cmake/scripts/write_export_constants.py',
    './cmake/scripts/write_export_constants.py.bak',
    './cmake/setup_rpath.cmake',
    './exec/cmake/modele',
    './init_cond/CMakeLists.txt',
    './model/CMakeLists.txt',
    './model/Ent/Ent_SOURCES.cmake',
    './model/MPI_Support/MPI_Support_SOURCES.cmake',
    './model/dd2d/dd2d_SOURCES.cmake',
    './model/giss_LSM/giss_LSM_SOURCES.cmake',
    './model/mk_diags/CMakeLists.txt',
    './model/mk_diags/prtdrv.f.in',
    './model/mk_diags/scaleacc_driver.f',
    './model/mk_diags/scaleaccdrv.f',
    './model/profiler/profiler_SOURCES.cmake',
    './model/shared/shared_SOURCES.cmake',
    './model/solvers/dgtsv.f',
    './model/solvers/solvers_SOURCES.cmake',
    './python/lib/modele/__init__.py',
    './python/lib/modele/pathutil.py',
    './python/lib/modele/rundeck/__init__.py',
    './python/lib/modele/rundeck/legacy.py',
    './python/lib/modele/rundir.py',
    './python/lib/modele/tests/__init__.py',
    './python/lib/modele/tests/rundeck1a.R',
    './python/lib/modele/tests/rundeck1b.R',
    './python/lib/modele/tests/rundeck2.R',
    './python/lib/modele/tests/test_hash.py',
    './python/lib/modele/xhash.py',
    './tests/CMakeLists.txt',
    './tests/MPI_Support/CMakeLists.txt',
    './tests/profiler/CMakeLists.txt',
    './tests/shared/CMakeLists.txt',
    './tests/tracers/CMakeLists.txt'
]

def packbuild(parser, args, unknown_args):
    with ectl.util.working_dir(args.src):
        with open('modele-control.pyar', 'w') as fout:
            pyar.pack_archive(fout, MODELE_CONTROL_FILES, report_fn=print)
