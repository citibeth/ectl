Installation
=============

ModelE and ``modele-control`` have a number of dependencies, which are
automatically handled by Spack_.  The following instructions may be
used to install ModelE, ``modele-control`` and Spack startin from a
clean machine:

.. _Spack: http://github.com/llnl/spack


Install Spack
--------------

1. Download::

    cd ~
    # git clone git@github.com:citibeth/spack.git -b efischer/develop
    git clone https://github.com/citibeth/spack.git -b efischer/develop

2. Add to your ``.bashrc`` file::

    export SPACK_ROOT=$HOME/spack
    . $SPACK_ROOT/share/spack/setup-env.sh

3. Remove non-system stuff from your ``PATH``, ``LD_LIBRARY_PATH`` and
   other environment variables, which can cause strange errors when
   building with Spack.

Setup Spack
------------

See Spack docs for more info on setting up compilers, bootstrapping, etc.

Actually... give instructions here on Intel, etc. compilers


Setup Packages
---------------

Copy the following to your ``~/.spack/packages.yaml`` file::

    packages:
        python:
            # Lie about the version in the system, so it's new enough for Spack to recognize.
            paths:
                python@2.7.8: /        # Spack can't install Python2, I don't know why
            version: [3.5.2,2.7.8]

        py-cython:
            version: [0.23.5]
        py-proj:
            version: [1.9.5.1.1]    # Normal released version 1.9.5.1 is buggy
        py-matplotlib:
            variants: +gui +ipython
        py-numpy:
            variants: +blas +lapack

        ibmisc:
            version: [develop]
            variants: +python +netcdf
        icebin:
            version: [develop]
            variants: +gridgen +python ~coupler ~pism

        # Running without dynamic ice
        modele:
            version: [landice]

    #    # Running with dynamic ice
    #    modele:
    #        version: [glint2]
    #        variants: [+couler +pism]

        pism:
            version: [glint2]
        glint2:
            version: [glint2]
            variants: +coupler +pism

        everytrace:
            version: [develop]
        eigen:
            variants: ~suitesparse
        netcdf:
            variants: +mpi


        # Recommended for security reasons
        # Do not install OpenSSL as non-root user.
        openssl:
            paths:
                openssl@system: /usr
            version: [system]
            buildable: False

        # Recommended, unless your system doesn't provide Qt4
        qt:
            paths:
                qt@system: /usr
            version: [system]
            buildable: False

        all:
            compiler: [gcc@4.9.3]
            providers:
                mpi: [openmpi]
                blas: [openblas]
                lapack: [openblas]



Install Modele-Control
-----------------------

.. code-block:: sh

    spack install modele-control


Install ModelE Prerequisites
-----------------------------

To install ModelE dependencies::

    spack install --dependencies-only modele

Download and Setup ModelE
---------------------------

To download ModelE::

    cd ..../my/directory
    git clone simplex.giss.nasa.gov:/giss/gitrepo/modelE.git
    cd modelE
    git checkout <branch>

.. note:: ``<branch>`` is the ModelE branch you wish to use: ``master``,
``develop``, ``landice``, ``cmake``, etc.

.. note:: The ``cmake`` build *must* be enabled on the branch you choose.

From the ModelE download directory, type the following (where
``<branch>`` is the name of the branch you checked out above)::

    spack setup modele@local

This creates a file `spconfig.py`, which is used in the build process
to configure CMake for your system.
