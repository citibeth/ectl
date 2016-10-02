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
