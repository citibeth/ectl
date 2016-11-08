Advanced Usage
==============

Continuing a Run
----------------

If a run directory has stopped running, it may be restarted where it
left off with `ectl run`.  For example:

.. code-block:: console

   $ ectl run myrun --time 12:00:00 -np 28

.. note::

   Command-line parameters related to HOW to run this job must be
   repeated, since they might be different from the last run:
   ``--launcher``, ``--ntasks``, ``--time``.

The above command rewrites the ``I`` file from your edited
``rundeck.R``.  This makes it easy to change rundeck parameters and
restart arun.  However, any command-line modifications to start/end
time will be lost.  If this behavior is not desired, you can either:

#. Specify the end time again on the command-line.  For example to end in 1960:

   .. code-block:: console

      $ ectl run myrun --timespan ,1960-01-01 --time 12:00:00 -np 28

#. Put the end time in your ``rundeck.R`` ,eliminating the need to
   specify it on the command line.

#. Continue the run with the ``--resume`` option.  This will use the
   ``I`` file from the last run, rather than the rundeck.  Using this
   option, it is not possible to change rundeck parameters:

   .. code-block:: console

      $ ectl run myrun --resume --time 12:00:00 -np 28


Restarting from fort.X.nc or an .rsf file
-----------------------------------------

You can restart a run from the ``fort.1.nc``, ``fort.2.nc`` or a
restart (``.rsf``) file using the ``--restart-file`` option.  Examples
include:

   .. code-block:: console

      $ ectl run myrun --restart-file myrun/fort.1.nc --time 12:00:00 -np 28
      $ ectl run myrun --restart-file myrun/1MAR1957.rsfmyrun.R.nc --time 12:00:00 -np 28

The ``fort.X.nc`` files will be overwritten.  If you want to restart
from one of them while ensuring your restart file is not overwritten,
copy ``fort.X.nc`` to a different name.  For example:

   .. code-block:: console

      $ cd myrun
      $ cp fort.1.nc myrestart.nc
      $ ectl run . --restart-file myrestart.nc --time 12:00:00 -np 28


Restarting by Date
------------------

It is also possible to restart from an ``.rsf`` file by specifying a date.  For example:

   .. code-block:: console

      $ ectl run myrun --restart-date 1957-03-01 --time 12:00:00 -np 28

This command will find the restart file for March 1957 and restart
from it.  If there is no restart file for the date you choose,
ModelE-Control will restart from the most recent ``.rsf` file less
than the date.  For example, the following will produce the same
result when used with monthly restart files:

   .. code-block:: console

      $ ectl run myrun --restart-date 1957-03-17 --time 12:00:00 -np 28


Create a Rundeck
------------------

Although ModelE-Control can work directly out of the templates
directory, it can also also assemble rundecks for further manual
editing.  This is done with `ectl flatten`.  Rundecks may be created
in any directory on the filesystem:

.. code-block:: console

   $ cd ~/exp
   $ ectl flatten modelE/templates/E4F40.R e4f40.R


One Root per User
-----------------

Alternately, users may choose to have only one root, presumably in the
user's home directory.  ModelE-Control then manges only one ``builds``
and ``pkgs`` directories for the entire user.  This simplifies
management in some ways, but it slows down certain ``ectl`` operations
(``ps``, ``purge``).
