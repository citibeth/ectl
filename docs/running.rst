Build and Run ModelE
=============================

Now that the ModelE environment has been installed, it is possible to
begin downloading and running climate models.  This section serves as a tutorial, not reference manual.  Definitive usage for any ModelE-Control command may be obtained via ``ectl <cmd> --help``.  For example:

.. code-block:: control

   $ ectl setup help
   usage: ectl setup [-h] [--ectl ECTL] [--rundeck RUNDECK] [--src SRC]
                     [--pkgbuild] [--rebuild] [--jobs JOBS]
                     run

   positional arguments:
     run                   Directory of run to setup

   optional arguments:
     -h, --help            show this help message and exit
     --ectl ECTL           Root of ectl tree: ectl/runs, ectl/builds, ectl/pkgs
     --rundeck RUNDECK, -rd RUNDECK
                           Rundeck to use in setup
     --src SRC, -s SRC     Top-level directory of ModelE source
     --pkgbuild            Name package dir after build dir.
     --rebuild             Rebuild the package, even if it seems to be fine.
     --jobs JOBS, -j JOBS  Number of cores to use when building.


Setup the ModelE Root
---------------------

Begin by setting up a ModelE **root directory**; this must be an ancestor of
all your run directories.  It is marked as a root directory by the
presence of a file named ``ectl.conf``.  For example:

.. code-block:: console

   $ mkdir ~/exp    # The root directory
   $ echo >~/exp/ectl.conf

**Notes:**

#. Run directories need to be held within the root directory, but not
   necessarily as direct children.  For example, the following
   directory structure is common:

   .. modele-control:: console
      exp/               # Root directory
          experiment1/
              run1/      # Run 1 of experiment 1
              run2/      # Run 2 of experiment 1
          experiment2/
              run1/      # Run 1 of experiment 2
              run2/      # Run 2 of experiment 2

#. There are no restrictions on what can go inside the root in
   addition to ModelE runs.  Typically, they may contain
   pre-processing and post-processing code, graphs, ModelE source
   directories --- anything needed by the user while building an
   experiment.

#. The user may have more than one root; although there is rarely a
   need to do so.

#. Any existing directory may be turned into a root.  For example:

   .. code-block:: console

      $ echo >~/ectl.conf   # Turn ~ into a root



Download ModelE Source
^^^^^^^^^^^^^^^^^^^^^^

Once a root has been set up, the user must find or download a ModelE
source directory.  This directory can be anywhere on the filesystem,
it does not have to live within a root.  Source directories may be
shared by mutliple run directories.  ModelE source is typically
obtained by downloading from Simplex, or some other Git repository:

.. code-block:: console

   $ cd ~/exp    # Root directory
   $ git clone simplex.giss.nasa.gov:/giss/gitrepo/modelE.git -b <branch>

**Notes:**

#. ``<branch>`` is the ModelE branch you wish to use: ``master``,
   ``develop``, ``landice``, ``cmake``, etc.

#. The ``cmake`` build *must* be enabled on the branch you choose.  If
   it is not, merge the ``cmake`` branch into your branch.  For
   example:

   .. code-block:: console

      $ git clone simplex.giss.nasa.gov:/giss/gitrepo/modelE.git -b <branch>
      $ cd modelE
      $ git merge origin/cmake

   This should add about 70 files; but should not have any conflicts
   or change any existing source files.


Setup ModelE Source
^^^^^^^^^^^^^^^^^^^

From the ModelE download directory, type the following::

.. code-block:: console

    $ cd ~/exp/modelE
    $ spack uninstall -ay modele@local;spack setup modele@local

This finds all of ModelE's dependencies and creates a file
``spconfig.py``, which is used in the build process to configure
ModelE's dependencies for your system.  Alternately, you can copy
``spconfig.py`` from another working ModelE source directory.

Create a Run
^^^^^^^^^^^^

It is now possible to create a ModelE run directory.  ModelE-Control
needs to know which source directory and rundeck you wish to use for
this run, as well as the name of the run directory you are creating.
For example, suppose you wish to create a run directory called
``myrun``::

    cd ~/exp
    ectl setup myrun --src ~/exp/modelE --rundeck ~/exp/modelE/templates/E4F40.R

This will do the following:

1. Create your run directory.  Run directories may be created anywhere
   that is a sub-directory of the ModelE-Control root.

2. Link input files into the run directory, downloading any missing
   input files.

3. Record your choices of source directory and run directory; these
   will be saved as symbolic links calld ``src`` and ``upstream.R``
   inside your run directory.  For example::

    $ ls myrun
    src -> ../../../../../home/rpfische/f15/modelE
    upstream.R -> ../e4f40.R

4. Create a build directory, where the source code for ModelE will be
   built.  It will be created in a subdirectory
   ``builds`` of the ModelE-Control.  In this case::

       build -> ../builds/768603dc2b58f45a96b72c5839d79dbd

   Note that the build directory is named by a random-looking hash.
   This hash is generated based on the ModelE source directory and the
   contents of your chosen rundeck; more on this later.

5. Use CMake to generate a build, linked up to the proper
   dependencies.  This is done by running the ``spconfig.py`` script
   generated above by Spack::

       -- CMAKE_INSTALL_RPATH /gpfsm/dnb53/rpfische/exp/pkgs/1e35f5f359ecbb675e04a1c75f9ee260/lib
       -- Found MPI_C: /usr/local/other/SLES11.3/openmpi/1.10.1/gcc-5.3/lib/libmpi.so
       ...
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
       -- Build files have been written to: ~/exp/builds/9b3ea947a57318e1e33018503c16b82d

6. Use ``make`` to build ModelE with the CMake-generated build::

       [  0%] Generating landice/ExportConstants.F90
       [  1%] Generating shared/RunTimeControls_mod.F90
       [  2%] Generating shared/Attributes.F90
       [  2%] Generating Ent/ent_mod.f
       [  3%] Generating shared/AttributeHashMap.F90, shared/AbstractTimeStamp.F90, shared/CalendarDate.F90
       [  3%] Generating shared/AttributeDictionary.F90
       Writing .../landice/ExportConstants.F90
       Reading /home/rpfische/f15/modelE/model/shared/Constants_mod.F90
       Reading /home/rpfische/f15/modelE/model/SEAICE.f
       Scanning dependencies of target modele
       [  4%] Building Fortran object model/CMakeFiles/modele.dir/landice/DebugType.F90.o
       ...
       [ 96%] Building Fortran object model/CMakeFiles/modele.dir/SURFACE.f.o
       [ 97%] Building Fortran object model/CMakeFiles/modele.dir/STRAT_DIAG.f.o
       [ 98%] Building Fortran object model/CMakeFiles/modele.dir/RAD_DRV.f.o
       [ 98%] Linking Fortran shared library libmodele.so
       [ 98%] Built target modele
       Scanning dependencies of target modelexe
       [ 99%] Building Fortran object model/CMakeFiles/modelexe.dir/main.F90.o
       [100%] Linking Fortran executable modelexe
       [100%] Built target modelexe

7. Create a package directory, where the executable for this run will
   live.  It will be created in a subdirectory ``pkgs`` of the
   ModelE-Control.  In this case::

       pkg -> ../pkgs/1e35f5f359ecbb675e04a1c75f9ee260

8. Install the built ModelE binaries into the package directory::

       Install the project...
       -- Install configuration: "Release"
       -- Installing: .../lib/libmodele.so
       -- Set runtime path of ".../libmodele.so" to ...
       -- Installing: .../bin/modelexe
       -- Set runtime path of ".../bin/modelexe" to ...

Start the Run
^^^^^^^^^^^^^

To start a run, for example, to run with two processors::

    ectl run ~/exp/test -np 2

Note that this command works from any directory.  You could just as
well have typed::

    cd ~/exp
    ectl run test

or even::

    cd ~/exptest
    ectl run

Before launching ModelE, this command will generate the ModelE `I`
file based on your run's `rundeck.R` file.  This ensure that any
parameter changes made to `rundeck.R` will be reflected in `I`.  The
user should *never* have to edit the ``I`` file directly.

This will start the run in the background and return to your shell
prompt.  The run will continue until it ends by itself or is stopped;
logging out will NOT stop the run.  After starting the run,
ModelE-Control shows run status::

    mpirun -timestamp-output -output-filename /gpfsm/dnb53/rpfische/exp/test/log/q -np 2 --report-pid /gpfsm/dnb53/rpfische/exp/test/modele.pid /gpfsm/dnb53/rpfische/exp/test/pkg/bin/modelexe -cold-restart -i I
    nohup: ignoring input and appending output to `nohup.out'
    ============================ test
    status:  RUNNING
    run:     /gpfsm/dnb53/rpfische/exp/test
    rundeck: /gpfsm/dnb53/rpfische/exp/e4f40.R
    src:     /gpfsm/dnb53/rpfische/f15/modelE
    build:   /gpfsm/dnb53/rpfische/exp/builds/768603dc2b58f45a96b72c5839d79dbd
    pkg:     /gpfsm/dnb53/rpfische/exp/pkgs/1e35f5f359ecbb675e04a1c75f9ee260
    launcher = mpi
    pidfile = /gpfsm/dnb53/rpfische/exp/test/modele.pid
    mpi_cmd = mpirun -timestamp-output -output-filename /gpfsm/dnb53/rpfische/exp/test/log/q -np 2 --report-pid /gpfsm/dnb53/rpfische/exp/test/modele.pid
    modele_cmd = /gpfsm/dnb53/rpfische/exp/test/pkg/bin/modelexe -cold-restart -i I
    cwd = /gpfsm/dnb53/rpfische/exp/test
    USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
    rpfische   436  7.9  0.0 4280812 4124 pts/9    Sl+  17:31   0:00 mpirun -timestamp-output -output-filename /gpfsm/dnb53/rpfische/exp/test/log/q -np 2 --report-pid /gpfsm/dnb53/rpfische/exp/test/modele.pid /gpfsm/dnb53/rpfische/exp/test/pkg/bin/modelexe -cold-restart -i I
    rpfische   443 86.8  0.1 13635064 245040 pts/9 Dl   17:31   0:00 /gpfsm/dnb53/rpfische/exp/test/pkg/bin/modelexe -cold-restart -i I
    rpfische   445 92.2  0.1 13624436 242348 pts/9 Rl   17:31   0:00 /gpfsm/dnb53/rpfische/exp/test/pkg/bin/modelexe -cold-restart -i I

View the Log
^^^^^^^^^^^^

The ModelE STDOUT/STDERR log file(s) are written into the directory
``myrun/log``, and are named by MPI rank::

    ~/exp/test> ls -l log
    total 960
    -rw-r----- 1 rpfische s1001 599042 Aug 28 17:32 q.1.0
    -rw-r----- 1 rpfische s1001 329834 Aug 28 17:32 q.1.1

Output is separated by MPI rank to enhance scalability, and to avoid
the occasional garbled output when two MPI ranks write output at the
same time.  Timestamps in the per-rank log files allow them to be
combined into one file if desired.

While ModelE is running, a log file may be watched via::

    tail -f myrun/log/q.1.0

Manage the Run
^^^^^^^^^^^^^^

After a run has been started, you can inspect the status of the run; for example::

    ectl ps myrun

If you have many runs going at once, you can also inspect the status
of them all together.  For example::

    ectl ps myrun1 myrun2

or to get the status of all the runs in your ModelE-Control root::

    cd ~/exp
    ectl ps

In any case, the status will tell the current model date/time, and
whether the simulation is currently running.  For example, after a
simulation has terminated, ``ectl ps`` looks like::

    ============================ test
    status:  STOPPED
    itime =     16033 timestamp = 1949-12-01T00:00
    fort.1.nc: 1949-12-01 00:00:00
    fort.2.nc: 1949-12-01 01:00:00
    run:     /gpfsm/dnb53/rpfische/exp/test
    rundeck: /gpfsm/dnb53/rpfische/exp/e4f40.R
    src:     /gpfsm/dnb53/rpfische/f15/modelE
    build:   /gpfsm/dnb53/rpfische/exp/builds/768603dc2b58f45a96b72c5839d79dbd
    pkg:     /gpfsm/dnb53/rpfische/exp/pkgs/1e35f5f359ecbb675e04a1c75f9ee260
    launcher = mpi
    pidfile = /gpfsm/dnb53/rpfische/exp/test/modele.pid
    mpi_cmd = mpirun -timestamp-output -output-filename /gpfsm/dnb53/rpfische/exp/test/log/q -np 2 --report-pid /gpfsm/dnb53/rpfische/exp/test/modele.pid
    modele_cmd = /gpfsm/dnb53/rpfische/exp/test/pkg/bin/modelexe -cold-restart -i I
    cwd = /gpfsm/dnb53/rpfische/exp/test
    <No Running Processes>

Stop the Run
^^^^^^^^^^^^

In order to stop a run::

    ectl stop myrun

This will do a "soft stop" by requesting ModelE to terminate.  It is
also possible to do a "hard stop" that kills the ModelE process as
expediently as possible::

    ectl stop -f myrun

Once the ``stop`` process is complete, ``ectl ps`` output should reflect that.

Post-Mortem
~~~~~~~~~~~~

Once a ModelE run has stopped, it is possible to determine how it
stopped, using Everytrace::

    $ etr myrun/log

    ======== Resolving Everytrace-enabled binaries:
       /gpfsm/dnb53/rpfische/exp/pkgs/1e35f5f359ecbb675e04a1c75f9ee260/lib/libmodele.so
    ref_addr_lib 495072 /gpfsm/dnb53/rpfische/exp/pkgs/1e35f5f359ecbb675e04a1c75f9ee260/lib/libmodele.so
    =============== q.1.0
    Exiting with return code: 13
      0x7FFEFB7804C7
      0x7FFEFBA860D6
      0x7FFEFBA8612D
      /home/rpfische/f15/modelE/model/MODELE.f:448
      /home/rpfische/f15/modelE/model/MODELE_DRV.f:28
      0x400A57
      0x7FFEFAD35C35
    =============== q.1.1
    Exiting with return code: 13
      0x7FFEFB7804C7
      0x7FFEFBA860D6
      0x7FFEFBA8612D
      /home/rpfische/f15/modelE/model/MODELE.f:448
      /home/rpfische/f15/modelE/model/MODELE_DRV.f:28
      0x400A57
      0x7FFEFAD35C35


Everytrace provides a stacktrace, with filenames and line numbers, of how ModelE stopped on each MPI rank.  In this case, ModelE terminated on line 448 of ``MODELE.f``, which is normal termination::

    CALL stop_model('Terminated normally (reached maximum time)',13)


In this case, normal termination can also be confirmed by inspecting the log files.
