Fortran Gotchas
===============

This section documents some common Fortran language issues that can
trip up ModelE programmers.

Passing Assumed Shape Arrays
----------------------------

When you pass an assumed shape ("Fortran 90") array in Fortran without
doing anything special, the base of the array is set to 1 in the
called procedure, no matter how it was set in the calling procedure.
For example:

.. code-block:: fortran

   subroutine mysub(arr)
       real*8, dimension(:) :: arr
       print *,lbound(arr),ubound(arr)
   end subroutine

   real*8, dimension(:) :: aa
   allocate(aa(0:17))
   print *,lbound(aa),ubound(aa)
   call mysub(aa)

The output of this program will be:

.. code-block:: console

   0 17
   1 18

In order to get the subroutine to see the same bounds on the array as
the caller, one must also pass the lower bound of eahc dimension:

.. code-block:: fortran

   subroutine mysub(arr, lbound)
       integer :: lbound
       real*8, dimension(lbound:) :: arr
       print *,lbound(arr),ubound(arr)
   end subroutine

   real*8, dimension(:) :: aa
   allocate(aa(0:17))
   print *,lbound(aa),ubound(aa)
   call mysub(aa, lbound(aa))


This aspect of Fortran might seem un-intuitive.  As long as all arrays
have a base of 1, then everything will work.  But there is an
opportunity for error any time an array is allocated with non-unity
base.  In ModelE, such arrays are common.  For example:

* Array distributed between MPI nodes.  Lower and upper bounds depend
  on the domain decomposition.  See section on
  :ref:`passing-distributed-array` for more details.

* The ``atmglas`` variable (FLUXES.f).  When more than one elevation
  class is used, this array has a lower bound of 0.


There are no good ways to "fix" this issue with the Fortran design.
In some cases, one can avoid passing arrays directly by including it
in a derived type.  Then its bounds will be passed through as
originally declared / allocated.  For example:


.. code-block:: fortran

   type mytype
       real*8, dimension(:,:), allocatable :: arr
   end type mytype

   subroutine mysub(myobj)
       type(mytype) :: myobj
       print *,lbound(myobj%arr),ubound(myobj%arr)
   end subroutine

   type(mytype) :: obj
   allocate(obj%arr(0:17))
   print *,lbound(obj%arr),ubound(obj%arr)
   call mysub(obj)


This can seem clumsy if a derived type is set up just to hold one
array; but it can be quite natural if the derived type is a class
holding many related arrays.

References
""""""""""

* `<http://www.cs.mtu.edu/~shene/COURSES/cs201/NOTES/chap08/assumed.html>`_


Intent(Out) Variables
---------------------

Fortran allows one to declare parameters ``intent(in)``,
``intent(out)`` or ``intent(inout)`` (the default if no intent is
declared).  If a variable is declared ``intent(out)``, then *any
values it has when passed in will be destroyed*.  This may seem like
the intended action, but can have unintended consequences.


For example, consider the following code:

.. code-block:: fortran

   ! [WRONG CODE]
   type mytype
       real*8, dimension(:,:), allocatable :: arr
   end type mytype

   subroutine mysub(myobj)
       type(mytype), intent(out) :: myobj
       myobj%arr(:) = 17
   end subroutine

   type(mytype) obj
   allocate(obj%arr(3))
   call mysub(obj)

When ``mysub()`` is run, ``myobj%arr`` will be de-allocated.  This
will cause an error on the statement ``myobj%arr(:) = 17``.

Moral on Intent(Out)
""""""""""""""""""""""

*Always be suspicious of intent(out) parameters.  If the parameter is
an array or derived type, intent(out) is almost never correct.  Use
intent(inout) instead.*


Double Precision Constants
--------------------------

**Question:** Why do I get single precision answers from double
precision variables?, and what are all those 'd0' doing?

All numbers in the GCM should be accurate to the degree of their
representation, however, many are not. This mostly stems from the
automatic conversion that takes place when a single precision or
integer number is converted to a double precision variable. In the
following examples the double precision variables will only be
accurate to 6 or so decimal places (instead of the 12 or so
expected).

.. code-block:: fortran

   REAL*8 X
   X = 0.1 =&gt; 0.10000000149011612
   X = 1/3 =&gt; 0. (integer division)
   X = 1./3. =&gt; 0.3333333432674408 
   X = 1./3 =&gt; 0.3333333432674408 
   X = 0.3333333333333333 =&gt; 0.3333333432674408 (!!!!)

To get double precision results you must use 'd' ie. ``X=0.1d0``,
``X=1d-1``, ``X=1d0/3d0`` or ``X=1./3d0`, or even ``X=1d0/3``.

.. note::
   * For decimals expressable exactly in binary formulation,
     there are no problems, ie. ``X=0.5`` is the same as ``X=5d-1``.

   * Where integer division is concerned, the integer is converted to
     the type of the numerator (I think). Thus ``1./IM`` gives only
     single precision.

   * ``REAL*8 :: FIM = IM, BYIM = 1./FIM`` gives double precision,
     since the denominator is already double precision).

On some compilers, but not all, there is a compiler option (such as
``-r8``) that removes these problems.  This is not standard Fortran.
Hence for maximum portability we are trying to be explicit about
writing out those ``d0`` indications.

