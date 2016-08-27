ModelE Control
================

ModelE Control makes it simple to setup, build and run the GISS ModelE
climate model.  It offers the following feature:

* ModelE run directories are decoupled from the ModelE software
  distribution, and may be placed anywhere convenient to the user.
  They will often reside together in "experiment" directories that
  might contains runs from more than one ModelE source download, as
  well as additional scripts to post-process experimental output.

* The ModelE software directory is not modified.  This allows, for
  example, easy ``rsync`` of ModelE between computers.

* ModelE binaries are decoupled from source and build directories, and
  are only deleted when no longer used by any run.  Re-building ModelE
  can never accidentally "mess up" an existing in-progress ModelE run.

Table of Contents
---------------------

.. toctree::
   :maxdepth: 2

    installation
