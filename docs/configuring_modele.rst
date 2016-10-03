Configuring ModelE
==================

The behavior of a ModelE run is configured in the rundeck through four
principle means:

#. Listing source files (see :ref:`polymorphism`).

#. Preprocessor symbols.

#. Rundeck parameters.

#. The ``INPUT`` namelist.

The first two means happen at ModelE build time, whereas the other two
can be changed without first rebuilding ModelE.  In both cases, ModelE
may be reconfigured in the middle of a run by stopping it, changing
the coniguration and then restarting.

Source Modules
--------------

The rundeck lists the set of source modules to build.  TODO:

#. Directories of source modules

#. Hard-coded source directories (eg ``shared``).

#. Source directory parameters

Rundeck Parameters
------------------

ModelE provides a parameter database, used to provide configuration
parameters to ModelE at runtime.  The database provides a read/write
mapping between string keys and values.  The database is loaded at
ModelE-startup time, after which ModelE is allowed to read/write
values in it.  The database is saved when writing restart/checkpoint
files, and restored upon restart.

Code in ModelE may obtain values from the database using
``get_param()``, for example:

.. code-block:: fortran

      real(real64) :: var
      call get_param('my_param', var)

To create a new parameter in the database with the name ``new_par``
and set it to the value in ``var``:

.. code-block:: fortran

   call set_param('new_par', var)

It is recommended to use the same name for the variable and for its
name in the database, as this improves code readability:

.. code-block:: fortran

   call set_param('new_par', new_par ) 
   call get_param('my_param', my_param ) 


Case Insensitive
    Parameters are case insensitive; the case of a parameter name
    never matters when used as a subroutine input.  When a name is
    returned as output from a subroutine, it is always returned in
    lower case.

Access Flag
    When a parameter is accessed via ``get_param()``, an *access flag*
    associated with that parameter is set.

Restarts
    The following procedure happens on a warm start:

    #. Parameters are loaded from the rundeck.

    #. Parameters not present in the rundeck are loaded from the restart file.

    .. note:: Parameters in the rundeck overrid parameters in the restart
       file.  This allows users to change parameters as needed in the
       rundeck.

Data Types
^^^^^^^^^^

Parametes may be of type ``integer``, ``real(real64)``, ``logical`` or
``character(*)``.  They may also be scalar or array, leaving eight
distinct types total.  The type of a parameter is determined in two ways:

#. From the type provided to the parameter API subroutines
   (``get_param()``, ``set_param()``, ``sync_param()``).

#. When parsing the rundeck, according to the following type inference rules:

   - If single-quoted strings are present, then strings are inferred.  Eg:

     .. code-block:: console

        NAME='Alice'
        NAMES='Alice','Bob','Charlie'

   - Else if decimal points are present, then ``real*8`` is inferred.  Eg:

     .. code-block:: console

        GRAV=9.8
        THICKNESSES=1.1,3.0

   - Else integer is inferred.  Eg:

     .. code-block:: console

        NSTEP=3
        NLAYERS=4,6,5


   As shown in these examples, the number of data entries on the line
   specifies the dimension of the array. If only one data entry is
   present then the parameter is a scalar; or an array of dimension
   one, which is equivalent.

When ``get_param()`` or ``sync_param()`` is called, the parameters
database receives type information both from the API call and from the
rundeck (or past calls to ``set_param()``).  If the types do not
match, ModelE will abort.

sync_param()
^^^^^^^^^^^^

Although the parameter database API is fully documented in
``shared/Dictionary_mod.F90``, the function ``sync_param()`` bears
further explanation.  It is a convenience function that works
conceptually as:

.. code-block:: fortran

   if( is_set_param( name ) ) then
     get_param( name, value, dim ) 
   else
     set_param( name, value, dim )
   endif

It is expected that ``sync_param()`` will be used most frequently by
ModelE code.  At the restart each module will check if certain
parameters were provided in the rundeck or in the restart file
(i.e. they are in the database already) and use those values. If not
then it will use default values and will also copy them to the
database so that they are saved to the restart file for future
reference.

Example
^^^^^^^

Here is an example of typical usage of ``query_param()``.
One should keep in mind that though ``get_param()`` is a
generic interface, one should call it with the arguments of correct
type to extract the information. That is why ``select
case`` is required below:

.. code-block:: fortran

   subroutine ex_param 
   ! this is an example subroutine that shows how to loop
   ! over all parameters in the database
   ! it does the same thing as print_param

      USE PARAM integer, parameter :: MAXDIM=64
      character*32 name
      integer n, dim
      character*1 ptype
      integer ic(MAXDIM)
      real*8 rc(MAXDIM)
      character*16 cc(MAXDIM)
      n = 1
      print *, 'printing parameter database'
      do call query_param( n, name, dim, ptype )
        if (name == 'EMPTY' ) exit
        if ( dim &gt; MAXDIM ) then
          print *, 'dim of param ',name,' is &gt; MAXDIM'
          stop 'MAXDIM too small'
        endif
        select case( ptype )
        case ('i') !integer
          call get_param( name, ic, dim )
          print *, name, ( ic(i), i=1, dim )
        case ('r') !real
          call get_param( name, rc, dim )
          print *, name, ( rc(i), i=1, dim )
        case ('c') !character
          call get_param( name, cc, dim )
          print *, name, (cc(i), i=1, dim )
        end select
        n = n + 1
      enddo
   end subroutine ex_param

Preprocessor Options
--------------------

The preprocessor is a program that runs before the actual compiler
starts and does certain editing to the source code according to
preprocessing instructions. All preprocessing instructions start with
a hash sign (``#``) in the first column. The most typical example of
preprocessor usage in Fortran code would be:

.. code-block:: console

       <fortran code>
   #ifdef OPTION_A
       <fortran code specific for OPTION_A>
   #endif
       <more fortran code>

In the above example the code between ``#ifdef OPTION_A`` and
``#endif`` will be compiled only if the name ``OPTION_A`` was defined
(with the instruction ``#define OPTION_A``) somewhere earlier in the
file. Otherwise it will be treated as commented out.  Preprocessor
symbols therefore allow the optional inclusion/exclusion of blocks of
code.

The C preprocessor can do other things as well, which are not widely
used in ModelE; see `The C Preprocessor
<https://gcc.gnu.org/onlinedocs/cpp>`_ for further details.

Defining Preprocessor Options
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The preprocessor symbols available to the Fortran code is controlled
by setting *preprocessor options* in the rundeck.  They are specified
in an optional block that starts with the line ``Preprocessor
Options`` and ends with the line ``End Preprocessor
Options``. Everything between those lines is treated as a set of
preprocessing definitions and will be included into corresponding
source files.  Here is a simple example of preprocessing block in the
rundeck:

.. code-block:: console

   Preprocessor Options
   #define TRACERS_ON ! include tracers code
   End Preprocessor Options


   .. note:: Preprocessor options are case-sensitive.

   .. note:: By convention, preprocessor options should be all capital
      letters, only with '_' introduced for readability.  This helps
      to distinguish them from the rest of the code which is usually
      in lower case.


This block defines the name ``TRACERS_ON``.

.. note:: The text after the exclamation point is a comment, and is
   ignored.  Trailing spaces and empty lines are also ignored.

.. note:: The ModelE build process extracts preprocessor options from
   the rundeck and writes them into the ``rundeck_opts.h`` file; when
   building, it only overwrites this file if preprocessor options have
   changed.


Using Preprocessor Options
^^^^^^^^^^^^^^^^^^^^^^^^^^

Any source file that will use rundeck preprocessor options must
include the line at the very beginning of the file:

.. code-block:: c

   #include "rundeck_opts.h"

.. note:: This is the C preprocessor ``#include`` directive that
   starts from the irst column of the source file; it is not the
   Fortran ``include`` statement.

.. note:: If this ``#include`` directive is not present, all
   preprocessing options will remain undefined.  The compiler
   unfortunately will not give any warnings about this.

A typical use of a preprocessing option would be:

.. code-block:: console

   #include &quot;rundeck_opts.h&quot;
         .......... some code
   #ifdef TRACERS_ON
         some tracers code here
   #endif
         some code

The code between ``#ifdef TRACERS_ON`` and ``#endif``
will be included only when global name ``TRACERS_ON`` is defined in a
rundeck. Otherwise this code will be ignored by the compiler.

Recommendations
^^^^^^^^^^^^^^^

There is an understanding that global preprocessing options should be
used only when there is no other convenient way to reach the same
goal. One should keep in mind that once the global preprocessing block
in a rundeck is changed, all files that include ``rundeck_opts.h``
will be rebuilt, which will likely force a rebuild of most of the
model.  One should therefore limit preprocessor options to those that
will not change often from one rundeck to the next.

This functionality is introduced mainly for the options
that are global (i.e. used in many source files at the same time)
and that need to be documented (that's why this block is in a
rundeck). Typical example would be an option that controls inclusion
of tracers code into the model (as in example above).

``INPUT`` Namelist
------------------

Only used for a few parameters...  Vestigal...

