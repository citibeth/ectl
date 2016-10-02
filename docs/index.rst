.. ModelE-Control documentation master file, created by
   sphinx-quickstart on Sun Sep  4 12:49:29 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

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

Contents:

.. toctree::
   :maxdepth: 2
   :caption: User's Guide

   introduction
   gettingstarted
   running

.. toctree::
   :maxdepth: 2
   :caption: ModelE Developer's Guide

   domain_decomposition
   initialization
   polymorphism
   fortran_gotchas




Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

