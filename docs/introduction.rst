Introduction
==============

ModelE-Control is a new way to build and run ModelE.  The original
impetus of the system was to improve ModelE's ability to build with
large numbers of external dependencies, in service to coupling with
dynamic ice models.  However, existing ways of running ModelE were not
particularly easy or intuitive; the author would frequently forget how
to do common tasks, or would make mistakes in submitting jobs.

Design Requirements
--------------------

This experience led to a number of design goals:

1. There should be simple, high-level commands that do what users need
   with ModelE, without bothering them with the details.  The list of
   required commands can be determined by looking at existing FAQs.
   For example:

    * How do I create a rundeck?
    * How do I prepare a run directory?
    * How do I run ModelE?
    * How do I stop ModelE?
    * How do I pause a ModelE run?
    * How do I restart a ModelE run somewhere other than it just left off?

2. ModelE runs last a long time.  Changes a user might make to ModelE
   source code or its dependencies should not affect existing
   in-progress runs.

3. Users have diverse sets of needs on how ModelE is to be built and
   run; and they should all be supported.  For example, some users run
   a single ModelE source code on dozens of rundecks.  Some users run
   multiple versions of a ModelE on the same rundeck.  Some users run
   specific rundecks on multiple compilers.  Some users want to change
   a run in the middle, others run only versions with git hashes

   All these use cases should be supported equally, without making
   specific assumptions on how users wish to work.

4. ModelE runs should be reproducible.  Enough information should be
   collected in a run so it can be reproduced.

5. A stacktrace should be provided whenever a ModelE run terminates
   prematurely, for whatever reason.  This can save countless hours of
   debugging effort.

6. Users update rundecks, and upstream changes to ModelE also update
   rundecks.  These multiple sources of changes should be accommodated
   and merged gracefully, without forcing the user to manually merge
   them (except in case of conflict).

7. Modern software ecosystems demand an ever-increasing number of
   dependencies be installed for a project to build and run; avoiding
   dependencies is no longer a viable way to make sofware easy to
   install.  It should be easy to install ModelE dependencies, and
   developers should not be inhibited from using valuable third-party
   libraries simply because they add a dependency.

8. Software dependencies of ModelE change from time to time --- for
   example, NetCDF.  Upgrading these dependencies should be easy and
   non-disruptive, and should not affect existing in-progress ModelE
   runs.

9. ModelE binaries should be useful for more than just running a
   climate simulations.  For example, unit tests, single-system runs
   or single-column models should be possible, without having to
   change the core ModelE ``main()`` program.


ModelE-Control addresses these design goals by re-thinking the process
of building and running ModelE.  It is an evolution of existing
practice and scripts.  The result is a single ``ectl`` command, like
``git``, with sub-commands for all ModelE operations.

Advantages
----------

Before we dive into using ModelE Control, this section explains a few
of the main concepts and advantages offered by the system.


Directories
^^^^^^^^^^^

In running ModelE, ModelE-Control distinguishes between five different
directories:

* **root**: An umbrella directory containing multiple run
  directories.

* **run**: The ModelE run directory; that is, the directory in
  which ModelE output and other data files are written.

* **src**: The location of the ModelE source code, as downloaded
  from Git.  ModelE-Control does not modify the src directory.

* **build**: The location where ModelE source code is built, which
  always happens out-of-source with ModelE-Control.

* **package**: The location for ModelE binaries.



The *run* directory is central to ``modele-control``, commands all
operate on a run directory.  Within the run directory are symbolic
links to the source (``src``), build (``build``) and package (``pkg``)
directories currently associated with that run.  This use of symbolic
links to associate directories with each other has many advantages:

#. Users have flexibility to place related runs together, whether or
   not they were built from the same source.
#. Different runs using the same source but different rundecks will
   build in different build directories, limiting the need for large
   rebuilds.
#. Packages are guaranteed to last at least as long as the run that
   needs them, no matter what the user does to the associated source
   or build directory in the meantime.

Rundeck Management
^^^^^^^^^^^^^^^^^^

Users typically start with a rundeck supplied in the ModleE
repository, and then modify it as needed.  This works, until ModelE is
updated, and the rundeck templates with it.  At that point, the user
is left with a new rundeck that works but without modifications; and
an old rundeck than no longer works.  The user is forced to manually
re-apply the edits made to the old rundeck, to the new rundeck.

ModelE Control mostly eliminates the need to manually merge rundecks.
When a source directory is updated, ModelE Control will use Git to
apply the user's rundeck modifications to the new rundeck.  In case a
rundeck changes in the middle of a run, this also allows the user to
reconstruct when that change happened.

`I` File Management
"""""""""""""""""""

Somtimes, users need to change rundeck parameters in the middle of a
run.  In the past, that was done by modifying the `I` file.  This was
not user friendly becuase the `I` file is not the same as the original
rundeck.  With ModelE Control, the user can edit the rundeck directly
when making parameter changes.
