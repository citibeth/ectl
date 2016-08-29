




; and it will provide a status report much like the one above.






1. Print out the configuration of this run directory.

Getting config from run
-------- Ectl Config:
    ectl:   /gpfsm/dnb53/rpfische/exp
    runs:   /gpfsm/dnb53/rpfische/exp
    builds: /gpfsm/dnb53/rpfische/exp/builds
    pkgs:   /gpfsm/dnb53/rpfische/exp/pkgs

Run: /gpfsm/dnb53/rpfische/exp/test
-------- Old Setup:
    rundeck: /gpfsm/dnb53/rpfische/exp/e4f40.R
    src:     /gpfsm/dnb53/rpfische/f15/modelE
    build:   /gpfsm/dnb53/rpfische/exp/builds/9b3ea947a57318e1e33018503c16b82d
    pkg:     /gpfsm/dnb53/rpfische/exp/pkgs/dbef2a57a30f196c8085dbaeeaaeabd5
    status:  0
========= BEGIN Rundeck Management
$ git checkout user
Already on 'user'
$ git commit -a -m Changes from user
On branch user
nothing to commit, working directory clean
$ git checkout upstream
Switched to branch 'upstream'
$ git commit -a -m Changes from upstream
On branch upstream
nothing to commit, working directory clean
$ git checkout user
Switched to branch 'user'
$ git merge upstream -m Merged changes
Already up-to-date.
========= END Rundeck Management
-------- New Setup:
    rundeck: /gpfsm/dnb53/rpfische/exp/e4f40.R
    src:     /home/rpfische/f15/modelE
    build:   /gpfsm/dnb53/rpfische/exp/builds/9b3ea947a57318e1e33018503c16b82d
    pkg:     /gpfsm/dnb53/rpfische/exp/pkgs/1e35f5f359ecbb675e04a1c75f9ee260
-- CMAKE_INSTALL_RPATH /gpfsm/dnb53/rpfische/exp/pkgs/1e35f5f359ecbb675e04a1c75f9ee260/lib
-- Found MPI_C: /usr/local/other/SLES11.3/openmpi/1.10.1/gcc-5.3/lib/libmpi.so
-- Found MPI_CXX: /usr/local/other/SLES11.3/openmpi/1.10.1/gcc-5.3/lib/libmpi_cxx.so;/usr/local/other/SLES11.3/openmpi/1.10.1/gcc-5.3/lib/libmpi.so
-- Found MPI_Fortran: /usr/local/other/SLES11.3/openmpi/1.10.1/gcc-5.3/lib/libmpi_usempif08.so;/usr/local/other/SLES11.3/openmpi/1.10.1/gcc-5.3/lib/libmpi_usempi_ignore_tkr.so;/usr/local/other/SLES11.3/openmpi/1.10.1/gcc-5.3/lib/libmpi_mpifh.so;/usr/local/other/SLES11.3/openmpi/1.10.1/gcc-5.3/lib/libmpi.so
-- Found NETCDF4_FORTRAN_LIBRARY: /gpfsm/dnb53/rpfische/spack2/opt/spack/linux-SuSE11-x86_64/gcc-5.3.0/netcdf-fortran-4.4.4-stdk2xq6tmvqg5deklveicisqgdz2dae/lib/libnetcdff.so
('sys.argv', ['/home/rpfische/f15/modelE/cmake/scripts/rundeck_to_cmake.py', '/home/rpfische/f15/modelE', '/gpfsm/dnb53/rpfische/exp/builds/9b3ea947a57318e1e33018503c16b82d', '/gpfsm/dnb53/rpfische/exp/e4f40.R'])
('** component option', 'USE_ENT', 'YES')
('** component option', 'PFT_MODEL', 'ENT')
('** component option', 'PS_MODEL', 'FBB')
('** component option', 'ONLINE', 'YES')
('** component option', 'NC_IO', 'PNETCDF')
-- ********************************************
-- ********** PROJECT: ModelE **********
-- Architecture: x86_64
-- System:       Linux
-- MODELERC:     
-- COMPILER:     GNU 5.3.0
-- RUNSRC:       
-- RUN:          /gpfsm/dnb53/rpfische/exp/e4f40.R
-- MPI:          YES
-- WITH_PFUNIT:  
-- ********************************************
-- Configuring done
-- Generating done
-- Build files have been written to: /gpfsm/dnb53/rpfische/exp/builds/9b3ea947a57318e1e33018503c16b82d
[  0%] Generating landice/ExportConstants.F90
[  1%] Generating shared/RunTimeControls_mod.F90
[  2%] Generating shared/Attributes.F90
[  2%] Generating Ent/ent_mod.f
[  3%] Generating shared/AttributeHashMap.F90, shared/AbstractTimeStamp.F90, shared/CalendarDate.F90
[  3%] Generating shared/AttributeDictionary.F90
Writing /gpfsm/dnb53/rpfische/exp/builds/9b3ea947a57318e1e33018503c16b82d/model/landice/ExportConstants.F90
Reading /home/rpfische/f15/modelE/model/shared/Constants_mod.F90
Reading /home/rpfische/f15/modelE/model/SEAICE.f
Scanning dependencies of target modele
[  4%] Building Fortran object model/CMakeFiles/modele.dir/landice/DebugType.F90.o
[  5%] Building Fortran object model/CMakeFiles/modele.dir/shared/TimeConstants.F90.o
[  5%] Building Fortran object model/CMakeFiles/modele.dir/landice/remap1d.F90.o
[  6%] Building Fortran object model/CMakeFiles/modele.dir/profiler/TimeFormatUtilities_mod.F90.o
[  6%] Building Fortran object model/CMakeFiles/modele.dir/shared/GetTime_mod.F90.o
[  6%] Building Fortran object model/CMakeFiles/modele.dir/shared/ArrayBundle_mod.F90.o
[  7%] Building Fortran object model/CMakeFiles/modele.dir/MPI_Support/Hidden_mod.F90.o
[  8%] Building Fortran object model/CMakeFiles/modele.dir/MPI_Support/Domain_mod.F90.o
[  8%] Building Fortran object model/CMakeFiles/modele.dir/Ent/ent_debug.f.o
[  9%] Building Fortran object model/CMakeFiles/modele.dir/shared/KindParameters.F90.o
[ 11%] Building Fortran object model/CMakeFiles/modele.dir/AtmL40.F90.o
[  9%] Building Fortran object model/CMakeFiles/modele.dir/shared/SystemTools.F90.o
[ 10%] Building Fortran object model/CMakeFiles/modele.dir/landice/LISnowParams.F90.o
[ 12%] Building Fortran object model/CMakeFiles/modele.dir/shared/RunTimeControls_mod.F90.o
[ 12%] Building Fortran object model/CMakeFiles/modele.dir/shared/RootFinding_mod.F90.o
[ 12%] Building Fortran object model/CMakeFiles/modele.dir/giss_LSM/GHY_H.f.o
[ 14%] Building Fortran object model/CMakeFiles/modele.dir/shared/Precision_mod.F90.o
[ 14%] Building Fortran object model/CMakeFiles/modele.dir/shared/AbstractAttribute.F90.o
[ 15%] Building Fortran object model/CMakeFiles/modele.dir/shared/MathematicalConstants.F90.o
[ 16%] Building Fortran object model/CMakeFiles/modele.dir/shared/Random_mod.F90.o
[ 16%] Building Fortran object model/CMakeFiles/modele.dir/shared/CubicEquation_mod.F90.o
[ 16%] Building Fortran object model/CMakeFiles/modele.dir/shared/SystemTimers_mod.F90.o
[ 17%] Building Fortran object model/CMakeFiles/modele.dir/Atm144x90.F90.o
[ 17%] Building Fortran object model/CMakeFiles/modele.dir/shared/StringUtilities_mod.F90.o
[ 17%] Building Fortran object model/CMakeFiles/modele.dir/shared/PolynomialInterpolator.F90.o
[ 17%] Building Fortran object model/CMakeFiles/modele.dir/shared/SpecialFunctions.F90.o
[ 18%] Building Fortran object model/CMakeFiles/modele.dir/shared/dast.F90.o
[ 18%] Building Fortran object model/CMakeFiles/modele.dir/MPI_Support/MpiSupport_mod.F90.o
[ 18%] Building Fortran object model/CMakeFiles/modele.dir/Ent/ent_const.f.o
[ 19%] Building Fortran object model/CMakeFiles/modele.dir/MPI_Support/dd2d_utils.f.o
[ 19%] Building Fortran object model/CMakeFiles/modele.dir/shared/Rational.F90.o
[ 20%] Building Fortran object model/CMakeFiles/modele.dir/shared/OrbitUtilities.F90.o
[ 21%] Building Fortran object model/CMakeFiles/modele.dir/AtmRes.F90.o
[ 22%] Building Fortran object model/CMakeFiles/modele.dir/shared/AttributeReference.F90.o
[ 23%] Building Fortran object model/CMakeFiles/modele.dir/profiler/Timer_mod.F90.o
[ 24%] Building Fortran object model/CMakeFiles/modele.dir/Ent/ent_types.f.o
[ 24%] Building Fortran object model/CMakeFiles/modele.dir/Ent/FBBpfts_ENT.f.o
[ 25%] Building Fortran object model/CMakeFiles/modele.dir/Ent/physutil.f.o
[ 26%] Building Fortran object model/CMakeFiles/modele.dir/shared/BaseTime.F90.o
[ 26%] Building Fortran object model/CMakeFiles/modele.dir/shared/Attributes.F90.o
[ 26%] Building Fortran object model/CMakeFiles/modele.dir/shared/AttributeHashMap.F90.o
[ 27%] Building Fortran object model/CMakeFiles/modele.dir/shared/AbstractTimeStamp.F90.o
[ 27%] Building Fortran object model/CMakeFiles/modele.dir/shared/CalendarMonth.F90.o
[ 27%] Building Fortran object model/CMakeFiles/modele.dir/shared/GenericType_mod.F90.o
[ 27%] Building Fortran object model/CMakeFiles/modele.dir/profiler/ReportColumn_mod.F90.o
[ 28%] Building Fortran object model/CMakeFiles/modele.dir/dd2d/pario_nc.f.o
[ 28%] Building Fortran object model/CMakeFiles/modele.dir/profiler/TimerList_mod.F90.o
[ 29%] Building Fortran object model/CMakeFiles/modele.dir/Ent/ent_pfts_ENT.f.o
[ 29%] Building Fortran object model/CMakeFiles/modele.dir/Ent/disturbance.f.o
[ 29%] Building Fortran object model/CMakeFiles/modele.dir/shared/TimeInterval.F90.o
[ 29%] Building Fortran object model/CMakeFiles/modele.dir/Ent/allometryfn.f.o
[ 30%] Building Fortran object model/CMakeFiles/modele.dir/Ent/respauto_physio.f.o
[ 31%] Building Fortran object model/CMakeFiles/modele.dir/profiler/ProfileReport_mod.F90.o
[ 32%] Building Fortran object model/CMakeFiles/modele.dir/shared/KeyValuePair_mod.F90.o
[ 32%] Building Fortran object model/CMakeFiles/modele.dir/Ent/FBBphotosynthesis.f.o
[ 32%] Building Fortran object model/CMakeFiles/modele.dir/Ent/ent_prescr_veg.f.o
[ 33%] Building Fortran object model/CMakeFiles/modele.dir/Ent/cohorts.f.o
[ 33%] Building Fortran object model/CMakeFiles/modele.dir/shared/Dictionary_mod.F90.o
[ 33%] Building Fortran object model/CMakeFiles/modele.dir/shared/AnniversaryDate.F90.o
[ 33%] Building Fortran object model/CMakeFiles/modele.dir/profiler/TimerPackage_mod.F90.o
[ 34%] Building Fortran object model/CMakeFiles/modele.dir/shared/CalendarDate.F90.o
[ 35%] Building Fortran object model/CMakeFiles/modele.dir/shared/AttributeDictionary.F90.o
[ 36%] Building Fortran object model/CMakeFiles/modele.dir/Ent/patches.f.o
[ 37%] Building Fortran object model/CMakeFiles/modele.dir/shared/AbstractCalendar.F90.o
[ 37%] Building Fortran object model/CMakeFiles/modele.dir/shared/Parser_mod.F90.o
[ 37%] Building Fortran object model/CMakeFiles/modele.dir/shared/PlanetaryParams.F90.o
[ 37%] Building Fortran object model/CMakeFiles/modele.dir/shared/FileManager_mod.F90.o
[ 38%] Building Fortran object model/CMakeFiles/modele.dir/shared/stop_model.F90.o
[ 38%] Building Fortran object model/CMakeFiles/modele.dir/shared/AbstractOrbit.F90.o
[ 38%] Building Fortran object model/CMakeFiles/modele.dir/shared/FixedCalendar.F90.o
[ 39%] Building Fortran object model/CMakeFiles/modele.dir/shared/Constants_mod.F90.o
[ 39%] Building Fortran object model/CMakeFiles/modele.dir/shared/Time.F90.o
[ 41%] Building Fortran object model/CMakeFiles/modele.dir/Ent/entcells.f.o
[ 41%] Building Fortran object model/CMakeFiles/modele.dir/Ent/soilbgc.f.o
[ 41%] Building Fortran object model/CMakeFiles/modele.dir/Ent/canopyspitters.f.o
[ 42%] Building Fortran object model/CMakeFiles/modele.dir/Ent/ent_prescribed_drv_geo.f.o
[ 43%] Building Fortran object model/CMakeFiles/modele.dir/MPI_Support/dist_grid_mod.F90.o
[ 43%] Building Fortran object model/CMakeFiles/modele.dir/landice/LISnowOut.F90.o
[ 44%] Building Fortran object model/CMakeFiles/modele.dir/landice/LISnowIn.F90.o
[ 45%] Building Fortran object model/CMakeFiles/modele.dir/landice/LANDICE.f.o
[ 46%] Building Fortran object model/CMakeFiles/modele.dir/shared/FixedOrbit.F90.o
[ 46%] Building Fortran object model/CMakeFiles/modele.dir/dd2d/ParallelIo.F90.o
[ 46%] Building Fortran object model/CMakeFiles/modele.dir/dd2d/cdl_mod.f.o
[ 47%] Building Fortran object model/CMakeFiles/modele.dir/dd2d/timestream_mod.f.o
[ 48%] Building Fortran object model/CMakeFiles/modele.dir/shared/JulianCalendar.F90.o
[ 48%] Building Fortran object model/CMakeFiles/modele.dir/Ent/phenology.f.o
[ 48%] Building Fortran object model/CMakeFiles/modele.dir/Ent/ent_prescribed_drv.f.o
[ 48%] Building Fortran object model/CMakeFiles/modele.dir/MPI_Support/GatherScatter_mod.F90.o
[ 48%] Building Fortran object model/CMakeFiles/modele.dir/MPI_Support/Halo_mod.F90.o
[ 49%] Building Fortran object model/CMakeFiles/modele.dir/MPI_Support/pario_fbsa.f.o
[ 50%] Building Fortran object model/CMakeFiles/modele.dir/shared/ModelClock.F90.o
[ 50%] Building Fortran object model/CMakeFiles/modele.dir/shared/Earth365DayOrbit.F90.o
[ 51%] Building Fortran object model/CMakeFiles/modele.dir/shared/ParameterizedEarthOrbit.F90.o
[ 53%] Building Fortran object model/CMakeFiles/modele.dir/Ent/ent.f.o
[ 53%] Building Fortran object model/CMakeFiles/modele.dir/Ent/ent_prescribed_updates.f.o
[ 53%] Building Fortran object model/CMakeFiles/modele.dir/Ent/ent_mod.f.o
[ 53%] Building Fortran object model/CMakeFiles/modele.dir/shared/PlanetaryCalendar.F90.o
[ 54%] Building Fortran object model/CMakeFiles/modele.dir/MPI_Support/GlobalSum_mod.F90.o
[ 54%] Building Fortran object model/CMakeFiles/modele.dir/MPI_Support/SpecialIO_mod.F90.o
[ 54%] Building Fortran object model/CMakeFiles/modele.dir/shared/PlanetaryOrbit.F90.o
[ 54%] Building Fortran object model/CMakeFiles/modele.dir/MPI_Support/DomainDecompLatLon.f.o
[ 54%] Building Fortran object model/CMakeFiles/modele.dir/MPI_Support/DomainDecomposition_mod.F90.o
[ 54%] Building Fortran object model/CMakeFiles/modele.dir/RAD_UTILS.f.o
[ 55%] Building Fortran object model/CMakeFiles/modele.dir/landice/LIGrid.F90.o
[ 55%] Building Fortran object model/CMakeFiles/modele.dir/READ_AERO.f.o
[ 55%] Building Fortran object model/CMakeFiles/modele.dir/landice/LISnowCol.F90.o
[ 56%] Building Fortran object model/CMakeFiles/modele.dir/MODEL_COM.f.o
[ 56%] Building Fortran object model/CMakeFiles/modele.dir/QUSDEF.f.o
[ 57%] Building Fortran object model/CMakeFiles/modele.dir/solvers/TRIDIAG.f.o
[ 57%] Building Fortran object model/CMakeFiles/modele.dir/VEG_DRV.f.o
[ 57%] Building Fortran object model/CMakeFiles/modele.dir/giss_LSM/SNOW.f.o
[ 57%] Building Fortran object model/CMakeFiles/modele.dir/landice/lisnowsubs.F90.o
[ 58%] Building Fortran object model/CMakeFiles/modele.dir/landice/LISnowState.F90.o
[ 59%] Building Fortran object model/CMakeFiles/modele.dir/giss_LSM/SNOW_DRV.f.o
[ 60%] Building Fortran object model/CMakeFiles/modele.dir/giss_LSM/GHY.f.o
[ 60%] Building Fortran object model/CMakeFiles/modele.dir/GEOM_B.f.o
[ 61%] Building Fortran object model/CMakeFiles/modele.dir/ATM_COM.f.o
[ 61%] Building Fortran object model/CMakeFiles/modele.dir/QUS_COM.f.o
[ 61%] Building Fortran object model/CMakeFiles/modele.dir/landice/LANDICE_DIAG.f.o
[ 62%] Building Fortran object model/CMakeFiles/modele.dir/CLOUDS_COM.F90.o
[ 63%] Building Fortran object model/CMakeFiles/modele.dir/ocalbedo.f.o
[ 63%] Building Fortran object model/CMakeFiles/modele.dir/FLUXES.f.o
[ 63%] Building Fortran object model/CMakeFiles/modele.dir/DIAG_ZONAL.f.o
[ 64%] Building Fortran object model/CMakeFiles/modele.dir/ATMDYN_COM.F90.o
[ 64%] Building Fortran object model/CMakeFiles/modele.dir/QUS_DRV.f.o
[ 64%] Building Fortran object model/CMakeFiles/modele.dir/CLOUDS2.F90.o
[ 65%] Building Fortran object model/CMakeFiles/modele.dir/QUS3D.f.o
[ 65%] Building Fortran object model/CMakeFiles/modele.dir/landice/LISheet.F90.o
[ 68%] Building Fortran object model/CMakeFiles/modele.dir/SEAICE.f.o
[ 68%] Building Fortran object model/CMakeFiles/modele.dir/ALBEDO.f.o
[ 68%] Building Fortran object model/CMakeFiles/modele.dir/GHY_COM.f.o
[ 69%] Building Fortran object model/CMakeFiles/modele.dir/landice/LISheetFHC.F90.o
[ 70%] Building Fortran object model/CMakeFiles/modele.dir/landice/LISnow.F90.o
[ 70%] Building Fortran object model/CMakeFiles/modele.dir/RADIATION.f.o
[ 71%] Building Fortran object model/CMakeFiles/modele.dir/landice/LANDICE_COM.f.o
[ 72%] Building Fortran object model/CMakeFiles/modele.dir/PBL.f.o
[ 72%] Building Fortran object model/CMakeFiles/modele.dir/LAKES_COM.f.o
[ 73%] Building Fortran object model/CMakeFiles/modele.dir/ICEDYN.f.o
[ 73%] Building Fortran object model/CMakeFiles/modele.dir/ENT_COM.f.o
[ 73%] Building Fortran object model/CMakeFiles/modele.dir/ENT_DRV.f.o
[ 75%] Building Fortran object model/CMakeFiles/modele.dir/DIAG_COM.f.o
[ 75%] Building Fortran object model/CMakeFiles/modele.dir/PBL_COM.f.o
[ 75%] Building Fortran object model/CMakeFiles/modele.dir/ICEDYN_DRV.f.o
[ 75%] Building Fortran object model/CMakeFiles/modele.dir/PBL_DRV.f.o
[ 77%] Building Fortran object model/CMakeFiles/modele.dir/OCNML.f.o
[ 77%] Building Fortran object model/CMakeFiles/modele.dir/MOMEN2ND.f.o
[ 78%] Building Fortran object model/CMakeFiles/modele.dir/LAKES.f.o
[ 79%] Building Fortran object model/CMakeFiles/modele.dir/RAD_COM.f.o
[ 79%] Building Fortran object model/CMakeFiles/modele.dir/DIAG.f.o
[ 79%] Building Fortran object model/CMakeFiles/modele.dir/GHY_DRV.f.o
[ 79%] Building Fortran object model/CMakeFiles/modele.dir/GCDIAGb.f.o
[ 81%] Building Fortran object model/CMakeFiles/modele.dir/DIAG_PRT.f.o
[ 81%] Building Fortran object model/CMakeFiles/modele.dir/ATMDYN.f.o
[ 82%] Building Fortran object model/CMakeFiles/modele.dir/ATM_UTILS.f.o
[ 83%] Building Fortran object model/CMakeFiles/modele.dir/Ent/reproduction.f.o
[ 83%] Building Fortran object model/CMakeFiles/modele.dir/FFT144.f.o
[ 84%] Building Fortran object model/CMakeFiles/modele.dir/shared/Geometry_mod.F90.o
[ 84%] Building Fortran object model/CMakeFiles/modele.dir/POUT.f.o
[ 84%] Building Fortran object model/CMakeFiles/modele.dir/shared/modele_python.F90.o
[ 85%] Building Fortran object model/CMakeFiles/modele.dir/giss_LSM/VEGETATION.f.o
[ 85%] Building Fortran object model/CMakeFiles/modele.dir/landice/LISnoGli.F90.o
[ 85%] Building Fortran object model/CMakeFiles/modele.dir/MODELE_DRV.f.o
[ 85%] Building Fortran object model/CMakeFiles/modele.dir/shared/System.F90.o
[ 85%] Building Fortran object model/CMakeFiles/modele.dir/landice/LANDICE_DRV.f.o
[ 85%] Building Fortran object model/CMakeFiles/modele.dir/shared/orbpar.f.o
[ 85%] Building Fortran object model/CMakeFiles/modele.dir/IO_DRV.f.o
[ 85%] Building Fortran object model/CMakeFiles/modele.dir/landice/SURFACE_LANDICE.f.o
[ 86%] Building Fortran object model/CMakeFiles/modele.dir/OCN_DRV.f.o
[ 86%] Building Fortran object model/CMakeFiles/modele.dir/ATM_DRV.f.o
[ 87%] Building Fortran object model/CMakeFiles/modele.dir/MPI_Support/ProcessTopology_mod.F90.o
[ 87%] Building Fortran object model/CMakeFiles/modele.dir/MPI_Support/assert.F90.o
[ 88%] Building Fortran object model/CMakeFiles/modele.dir/FLUXESIO.f90.o
[ 89%] Building C object model/CMakeFiles/modele.dir/shared/system_tools.c.o
[ 91%] Building Fortran object model/CMakeFiles/modele.dir/shared/Utilities.F90.o
[ 90%] Building Fortran object model/CMakeFiles/modele.dir/shared/GaussianQuadrature.F90.o
[ 91%] Building Fortran object model/CMakeFiles/modele.dir/solvers/dgtsv.f.o
[ 92%] Building Fortran object model/CMakeFiles/modele.dir/shared/PlanetParams_mod.F90.o
[ 92%] Building Fortran object model/CMakeFiles/modele.dir/OCEAN.f.o
[ 93%] Building Fortran object model/CMakeFiles/modele.dir/DIAG_RES_F.f.o
[ 93%] Building Fortran object model/CMakeFiles/modele.dir/STRATDYN.f.o
[ 93%] Building Fortran object model/CMakeFiles/modele.dir/landice/ExportConstants.F90.o
[ 94%] Building Fortran object model/CMakeFiles/modele.dir/DEFACC.f.o
[ 95%] Building Fortran object model/CMakeFiles/modele.dir/SEAICE_DRV.f.o
[ 95%] Building Fortran object model/CMakeFiles/modele.dir/MODELE.f.o
[ 96%] Building Fortran object model/CMakeFiles/modele.dir/ATURB.f.o
[ 96%] Building Fortran object model/CMakeFiles/modele.dir/CLOUDS2_DRV.F90.o
[ 96%] Building Fortran object model/CMakeFiles/modele.dir/SURFACE.f.o
[ 97%] Building Fortran object model/CMakeFiles/modele.dir/STRAT_DIAG.f.o
[ 98%] Building Fortran object model/CMakeFiles/modele.dir/RAD_DRV.f.o
[ 98%] Linking Fortran shared library libmodele.so
[ 98%] Built target modele
Scanning dependencies of target modelexe
[ 99%] Building Fortran object model/CMakeFiles/modelexe.dir/main.F90.o
[100%] Linking Fortran executable modelexe
[100%] Built target modelexe
Install the project...
-- Install configuration: "Release"
-- Installing: /gpfsm/dnb53/rpfische/exp/pkgs/1e35f5f359ecbb675e04a1c75f9ee260/lib/libmodele.so
-- Set runtime path of "/gpfsm/dnb53/rpfische/exp/pkgs/1e35f5f359ecbb675e04a1c75f9ee260/lib/libmodele.so" to "/gpfsm/dnb53/rpfische/exp/pkgs/1e35f5f359ecbb675e04a1c75f9ee260/lib:/gpfsm/dnb53/rpfische/spack2/opt/spack/linux-SuSE11-x86_64/gcc-5.3.0/netcdf-fortran-4.4.4-stdk2xq6tmvqg5deklveicisqgdz2dae/lib:/usr/local/other/SLES11.3/openmpi/1.10.1/gcc-5.3/lib:/gpfsm/dnb53/rpfische/spack2/opt/spack/linux-SuSE11-x86_64/gcc-5.3.0/everytrace-develop-p5wmb25f43r65y424elllbbcia7m6v2z/lib"
-- Installing: /gpfsm/dnb53/rpfische/exp/pkgs/1e35f5f359ecbb675e04a1c75f9ee260/bin/modelexe
-- Set runtime path of "/gpfsm/dnb53/rpfische/exp/pkgs/1e35f5f359ecbb675e04a1c75f9ee260/bin/modelexe" to "/gpfsm/dnb53/rpfische/exp/pkgs/1e35f5f359ecbb675e04a1c75f9ee260/lib:/gpfsm/dnb53/rpfische/spack2/opt/spack/linux-SuSE11-x86_64/gcc-5.3.0/netcdf-fortran-4.4.4-stdk2xq6tmvqg5deklveicisqgdz2dae/lib:/usr/local/other/SLES11.3/openmpi/1.10.1/gcc-5.3/lib:/gpfsm/dnb53/rpfische/spack2/opt/spack/linux-SuSE11-x86_64/gcc-5.3.0/everytrace-develop-p5wmb25f43r65y424elllbbcia7m6v2z/lib"
rpfische@discover17:~/exp> cd test/
























Create a Rundeck
------------------

Rundecks may be created in any directory convenient, inside or outside
any particular ModelE source or experiment directory.  For example::

    cd ~/exp
    ectl flatten modelE/templates/E4F40.R e4f40.R

This command copies a rundeck from inside a ModelE source directory to the user's experiment directory.  In the process of copying, 

The command is
``ectl flatten``.


ModelE-Control allows the use of rundecks



HOWTO
------

Continue a run with newly changed code


One Root per User
~~~~~~~~~~~~~~~~~~

Alternately, users may choose to have only one root, presumably in the
user's home directory.  ModelE-Control then manges only one ``builds``
and ``pkgs`` directories for the entire user.  This simplifies
management in some ways, but it slows down certain ``ectl`` operations
(``ps``, ``purge``).
