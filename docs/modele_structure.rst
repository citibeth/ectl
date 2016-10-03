ModelE Structure
================


Functional Areas and Source Files
---------------------------------

ModelE is organized into physically relevant functional areas --- for
example: atmosphere, ocean, landice, groudn hydrology, etc.  Every
area of physics functionality is built using three (or more) Fortran
source files.  For example, consider the ``GHY`` functional area:

``GHY_COM.f``
    This is a "common block" of variables, which includes all the
    state for the ``GHY`` functional area.  ``GHY_COM.f`` has the
    following functions:

    #. It defines the module ``GHY_COM``.

    #. It owns the variables on the main model grid inside
       ``GHY_COM``.  These variables may be used by other parts of the
       code.

       .. note::

          Uncontrolled access of global variables between functional
          areas works against modularity and debugabbility.  ModelE is
          moving toward state being private within each functional
          area, with state to be transferred between functional areas
          via well-defined "exchange" variables.  See, for example,
          the ``atmXXX` variables in ``FLUXES.f``.

    #. It must provide methods to:

       - Allocate the ``GHY`` state (``alloc_ghy_com()``).

       - Read initial conditions on a cold start (``read_landsurf_ic()``).

       - Define NetCDF variables the ``GHY`` state
         (``def_rsf_earth()``, ``def_rsf_soils()``,
         ``def_rsf_snow()``, ``def_rsf_veg_related()``).

       - Read/write the ``GHY`` state (``new_io_earth()``,
         ``new_io_soils()``, ``new_io_snow()``,
         ``new_io_veg_related()``).

       .. note:: These methods are traditionally provided OUTSIDE the
          ``GHY_COM`` module.  They may be called without any ``USE``
          statements, but calls are not typechecked.


``GHY.f``
    This is the main local physics code (for instance, pure 1D column
    physics).  It should not access the variables in ``GHY_COM.f``.
    Instead, all state it requires should be passed into its
    subroutines as parameters.  This allows the pure physics code to
    be tested and used in situations other than the GCM context.

    .. note:: The physics subroutines are generally put *inside* a
       module, which would normally be called ``GHY``.  In this case,
       the module is called ``sle001``.

``GHY_DRV.f``
    This consists of the "drivers", i.e. the programs that access the
    local physics routines, do initiallisation etc.  There is no
    consistent regarding the placement of these subroutines in
    modules.


Three separate files are used for each functional area to avoid
circular dependencies in the Fortran code.  Consider a situation where
the module needs information from another module - i.e. there is a
``USE`` statement in one of the drivers.  Conceivably, that module
might USE a variable from this module also.  This would create a
circular dependency if the USE statements and the variable definitions
were in the same file, which is not legal Fortran.

Therefore, at minimum the common block and the drivers must be
seperated. We choose generally to make the local physics a seperate
file also because it is not usually dependent on anything except the
CONSTANT module and possibly the main model common block.  This
separation reduces recompilations when drivers or common blocks
change.  However, sometimes the local physics is in the same file as
the COM module.

Finding Definitions and Declarations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Definitions and declarations may be found according to some simple rules (but not yet implemented 100% of
the time):

* Variables defined on the model grid are in the COM file.

* Module specific parameters are in the local physics module. 

* local variables are defined wherever they are needed. 

* Variables from other parts of the code are listed in the USE only
  statements.

One exception to this is when local parameters are required by another
part of the model (i.e. for the input NAMELIST), then the variable
might be defined in the local physics module, `USE`d by the COM module
and only accessed through COM. - Drivers can `USE` both the COM
variables and the local physics parameters.

The Unix `grep` utility can always be used to find uses and
declarations.  For example:

.. code-block:: console

   $ grep -i mdwnimp `find . -name '*.f'`

This will only search files ending in `.f`.  To search all Fortran files, try:

.. code-block:: console

   $ grep -i mdwnimp `findf .`



Object-Oriented Functional Areas
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``LANDICE`` functional area increasingly uses object-oriented
features in Fortran 2003 and 2008.  This has some practical effects on
the above organization:

#. Typically, a single class will represent all the state required for
   the functional area.  Therefore, the ``_COM`` module would ideally
   contain only one globa variable (an instance of the functional
   area's class).

#. In the spirit of encapsulation, object-oriented code should avoid
   ``USE`` statements to obtain data from other parts of the model.
   The following techniques should be used instead:

   - Pass the data into methods at the time it is needed.

   - Pass references to the data into the class constructor.  This is
     less preferable, because it allows changes in state in other
     modules to invisibly affect the behavior of local class methods.


.. _polymorphism:

Polymorphism and Rundecks
-------------------------

ModleE contains more than one implementation of many functional areas.
For example, there are two ocean models and multiple grids.  ModelE
predates the rise of language support for polymorphism and dynamic
dispatch, and does not use now-standard object-oriented features.

Instead, ModelE implements a static form of polymorphism in the build
system.  Two versions of the same functional area are coded in
separate files that define the same symbols (modules, subroutines,
variables, etc).  When building ModelE, only one of those source files
may be linked into the final executable; they cannot be linked
together.

This design choice has far-reading practical consequences.  Unlike
most systems, there *is no single ModelE binary* that can be built,
nor is there a single list of which source files to link together.
Instead, ModelE comes with a set of *rundeck* files, which specify the
set of source files to link for any particular ModelE build.  The
rundecks are the *only* and *definitive* guide on how to linke ModelE
source files together.  One can think of the ModelE build process as a
function that produces a binary executable, given a ModelE source tree
and a rundeck.  It will produce a different executable if either the
source tree or the rundeck is different.


.. _domain-decomposition:

ModelE Domain Decomposition
---------------------------

See also :ref:`esmf_change_guide` for more information on this section.

ModelE computations are split over multiple MPI nodes, with each node
handling only a portion of each array.  Historically, ModelE has
divided its domain only along latitude slices; starting with the cube
sphere version, ModelE will divide its domain in two dimensions.  This
document describes the old domain decomposition only.

ModelE distributed arrays may or may not contain a single-cell "halo"
that overlaps with neighboring domains.  Halos are essential for the
solution of differential equations, but not so mcuh when working with
column-only physics.

Obtaining the Decomposition
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The domain is set up early in ModelE initialization
(``MPI_Support/DomainDecompLatLon.f``, or
``CS_Support/DOMAIN_DECOMPcs.f`` for cube sphere).  Details of the
decomposition are stored in the ``grid`` variable, which may be
accessed via:

.. code-block:: fortran

   use domain_decomp_atm, only : grid

More modern subroutines may also choose to take ``grid`` as a parameter:

.. code-block:: fortran

   subroutine mysub(grid, ...)
       USE DOMAIN_DECOMP_ATM, ONLY : DIST_GRID
       TYPE (DIST_GRID), INTENT(IN) :: grid
       ...
   end subroutine mysub


Decomposition Details
"""""""""""""""""""""

The ``grid`` object provides the following values describing the
domain and its decomposition:

* ``grid%j_strt``, ``grid%j_stop``: The lower and upper bounds of the
  ``j`` (latitude) dimension on this MPI node.

* ``grid%i_strt``, ``grid%i_stop``: The lower and upper bounds of the
  ``i`` (longitude) dimension on this MPI node.

* ``grid%j_strt_halo``, ``grid%j_stop_halo``: The lower and upper
  bounds of the ``j`` (latitude) dimension on this MPI node, including
  the halo.

* ``grid%i_strt_halo``, ``grid%i_stop_halo``: The lower and upper
  bounds of the ``i`` (longitude) dimension on this MPI node,
  including the halo.

* ``grid%jm_world``: Number of grid cells in the latitude direction.
  May also be obtained via:

  .. code-block:: fortran

     use resolution, only : jm

* ``grid%im_world``: Number of grid cells in the longitude direction.
  May also be obtained via:

  .. code-block:: fortran

     use resolution, only : im

Grid at the Poles
"""""""""""""""""

The latitude/longitude grid has special "polar cap" grid cells at the
poles, which include all the area above a particular latitude.  Thus,
for ``j==1`` (latitude at the south pole), only the grid cell at
``i==0`` is used; grid cells ``i==1..im`` are redundant.  Similarly at
the north pole (``j==jm``), only ``i==0`` is used as well.

The following classmembers also provide interesting information about
the grid the poles:

* ``grid%hasSouthPole``: ``.true.`` if this MPI domain contains the
  south pole.

* ``grid%hasNorthPole``: ``.true.`` if this MPI domain contains the
  north pole.

* ``grid%j_strt_skp``: Lower bound of local domain, exclusive of the
  south pole.

* ``grid%j_stop_skp``: Lower bound of local domain, exclusive of the
  north pole.


Allocating a Distributed Array
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``grid`` object contains the lower and upper bounds that
distributed arrays should have on any particular MPI node.  This may
be used to allocate distributed arrays.  For example:

.. code-block:: fortran

   real(REAL64), allocatable, dimension(:,:,:,:) :: wsn
   allocate(wsn(grid%I_STRT:grid%I_STOP, grid%J_STRT:grid%J_STOP))

The following will allocate a distributed array with halo:

.. code-block:: fortran

   real(REAL64), allocatable, dimension(:,:,:,:) :: wsn
   allocate(wsn(
       grid%I_STRT_HALO:grid%I_STOP_HALO, &
       grid%J_STRT_HALO:grid%J_STOP_HALO))


Iterating over a Distributed Array
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

One may iterate over all non-halo grid cells in an array as follows:

.. code-block:: fortran

   integer :: i,j
   DO J=grid%J_STRT,grid%J_STOP
   DO I=grid%I_STRT,grid%I_STOP
       Do my thing on myvar(i,j)...
   end do
   end do

The above example will iterate over redundant grid cells at the poles.
In order to avoid this, the ``imax(j)`` function may be used as
follows:

.. code-block:: fortran

   USE GEOM, only : imaxj
   do j=grid%J_STRT,grid%J_STOP
   do i=grid%I_STRT,imaxj(j)
       Do my thing on myvar(i,j)...
   end do
   end do


.. _passing-distributed-array:

Passing a Distributed Array
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Since distributed arrays typically have a base other than 1 on local
MPI nodes, care must be taken when passing them to subroutines: the
lower bound must be declared in the formal parameter declaration.
This is typically achieved by passing the ``grid`` object into the
subroutine along with the arrays.  The ``grid`` object may then be
used to declare array lower bounds.  For example:

.. code-block:: fortran

   subroutine mysub(grid, zatmo)
       real(real64), dimension(grid%i_strt:,grid%j_strt:) :: ZATMO

If the distributed array has a halo, the following form must be used
instead:

   subroutine mysub(grid, zatmo)
       real(real64), dimension(grid%i_strt_halo:,grid%j_strt_halo:) :: ZATMO

.. note::

   There is no way for the compiler to typecheck halo vs. non-halo
   arrays here.  If you pass a non-halo array to a subroutine
   expecting a halo array (or vice versa), bad things will happen.


Passing inside a Derived Type
"""""""""""""""""""""""""""""

The above procedures are inherently dangerous: mysterious errors can
result if one fails to specify a lower bound when passing an array ---
or even if one mixes up halo vs. non-halo array parameters.  A safer
approach is to encapsulate the array in a derived type.  This often
works out naturally if one is following an object-oriented approach.  For example, consider ``LISnowState_t`` (in ``LISnowState.F90``):

.. code-block:: fortran

   type LISnowState_t
       real(REAL64), allocatable, dimension(:,:,:,:) :: wsn, hsn, dz
   contains
       procedure :: allocate
       procedure :: io_rsf
   end type LISnowState_t


Increasing Readability
^^^^^^^^^^^^^^^^^^^^^^

The examples above can quickly become verbose; this can be a problem
especially in fixed-format source files.  Verbosity issues may be
addressed in a few ways:

Local Variables for Array Bounds
""""""""""""""""""""""""""""""""

In many cases, ModelE subroutines define local variables that are set
to the array bounds from the ``grid`` object.  These variables may
then be used to allocate or loop over the array.  Typically, the
following variable names are used:

.. code-block:: fortran

   i0 = grid%i_strt
   i1 = grid%i_stop
   j0 = grid%j_strt
   j1 = grid%j_stop
   i0h = grid%i_strt_halo
   i1h = grid%i_stop_halo
   j0h = grid%j_strt_halo
   j1h = grid%j_stop_halo

**Pros**:

* Uses standard Fortran.

* Works well in fixed-format source files.

**Cons**:

* Cannot be used to declare lower bounds when passing arrays.

* Clumsy definition of new variables to hold these values

Macros for Array Bounds
"""""""""""""""""""""""

One can also use the C preprocessor to achieve a similar end.  For
example:

.. code-block:: fortran

   #define I0 grid%i_strt
   #define I1 grid%i_stop
   #define J0 grid%j_strt
   #define J1 grid%j_stop
   #define I0H grid%i_strt_halo
   #define I1H grid%i_stop_halo
   #define J0H grid%j_strt_halo
   #define J1H grid%j_stop_halo

These macros may then be used in many cases, as long as there is a
variable named ``grid``:

.. code-block:: fortran

   subroutine mysub(grid, arr)
       type(dist_grid), intent(in) :: grid
       real(real64) :: arr(I0:I1,J0:J1)
   end subroutine

**Pros**:

* Convenient.  Macros need only be defined once per source file, not
  in every function.

* May be used to declare bounds in subroutines, as well as to allocate.

**Cons**:

* Not appropriate for fixed-format Fortran, due to line length issues.
  One must also be careful with the 132-character line limit in free
  format Fortran.

Model Initialization
--------------------


