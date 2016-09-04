Getting Started
================

A number of pieces of software must be installed to run ModelE
successfully --- not just ModelE and ModelE-Control, but also ModelE
dependencies, as well as key post-processing tools.  These tools have
already been installed on some systems, allowing users to get started
immediately simply by making changes to `.bashrc`.

Check below to see if the ModelE environment has been installed on
your favorite computer.  If not, head to the
full Installation instructions below.

Quick Start: NCCS Discover
---------------------------

The ModelE environment has already been installed on NCCS Discover,
allowing users to get started quickly with ModelE.  To use this
environment:

1. Remove all ``module load`` commands from your
``.bashrc`` file.


2. Add the following to your ``.bashrc`` file::

    source /home/rpfische/env/modelex-gcc

Use the following instead for Intel compilers (not yet implemented)::

    source /home/rpfische/env/modelex-intel

3. Set ``MODELE_FILE_PATH`` in your ``.bashrc``, modifying depending
   on where you wish to keep user-generated input files.

    export MODELE_FILE_PATH=/discover/nobackup/projects/giss/prod_input_files:$HOME/modele_input/local

That's it, you are now ready to use ModelE, along with all the latest tools and full-featured dependencies (eg, NetCDF 4).


Installation
-------------

ModelE and ModelE-Control have a number of dependencies, which are
automatically handled by Spack_.  The following instructions may be
used to install ModelE, ``modele-control`` and Spack startin from a
clean machine:

.. _Spack: http://github.com/llnl/spack


Install Spack
~~~~~~~~~~~~~~

If you are not using ``discover``, then here is how to build a
ModelE environment on your machine.

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
~~~~~~~~~~~~

See Spack docs for more info on setting up compilers, bootstrapping, etc.

Actuallyxx... give instructions here on Intel, etc. compilers


Setup Packages
~~~~~~~~~~~~~~~

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



Install ModelE Environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~

This installs all the prerequisites needed to run ModelE, along with basic tools to analyze its output.

.. code-block:: sh

    spack install modele-utils
    spack install --dependencies-only modele
    spack install ncview
    spack install nco
    spack install modele-control

Generate the Module Loads
~~~~~~~~~~~~~~~~~~~~~~~~~~

Run the following script, to generate the file ``~/env/modele``.  This
will load the modules you just created::



    #!/bin/sh
    #
    # Generate commands to load the Spack environment


    SPACKENV=$HOME/env/modele
    FIND='spack module loads'

    echo '#!/bin/sh -f' >$SPACKENV
    echo '# ---- Machine generated; do not edit!' >>$SPACKENV
    #echo 'module purge' >>$SPACKENV

    # --- ModelE Stuff
    $FIND ncview >>$SPACKENV
    $FIND nco >>$SPACKENV
    $FIND modele-control >>$SPACKENV
    $FIND modele-utils >>$SPACKENV

**NOTES**:

1. Remember to include any bootstrapping modules you might need as
well: for example, pre-existing compilers sometimes must be loaded to
run anything built with them.

2. Depending on how your system's environment modules are configured, you might need to add ``--prefix`` to the ``spack module loads`` command.  See ``spack module loads --help``.

Update ``.bashrc``
~~~~~~~~~~~~~~~~~~~

Add the following to your ``.bashrc`` file, modifying accordingly::

    export SPACK_ROOT=$HOME/spack
    . $SPACK_ROOT/share/spack/setup-env.sh
    export MODULEPATH=$SPACK_ROOT/share/spack/modules:$MODULEPATH
    export PATH=$PATH:$HOME/spack/bin
    alias spack='nice spack'
    export SPACK_DIRTY=
    export LESS='-R'
    source $HOME/env/modele
