from modele.constants import SHW,SHI,LHM,RHOI
import numpy as np
import contextlib

@contextlib.contextmanager
def np_seterr(**kwargs):
    # http://stackoverflow.com/questions/15192637/runtimewarning-invalid-value-encountered-in-maximum
    errs = np.geterr()
    np.seterr(**kwargs)
    yield
    np.seterr(**errs)

    
# -------------------------------------------------------------------------
# subroutine hsn_to_tsn(hsn, wsn, tsn, isn, nl)
#     double precision, dimension(:), intent(in) :: hsn, wsn
#     double precision, dimension(:), intent(inout) :: tsn, isn
#     integer :: nl        ! Number of layers to compute it for
# 
#     ! -------- Local Vars
#     integer :: i
#     double precision :: lhmw
# 
#     do i=1,nl
#         if ( hsn(i) > 0.d0 ) then
#             ! All water
#             tsn(i) = hsn(i) / (wsn(i) * SHW)
#             isn(i) = 0d0
#         else if ( hsn(i) > -wsn(i)*LHM ) then
#             ! Temperate ice
#             tsn(i) = 0.d0
#             isn(i) = -hsn(i)/(wsn(i) * LHM)
#         else
#             ! 100% ice, no liquid content
#             !        ([J m-2] + [kg m-2][J kg-1]) / ([J kg-1 K-1][kg m-2])
#             !                          [J m-2]    /   [J m-2 K-1]   ---> [K]
#             tsn(i) = (hsn(i)+wsn(i)*LHM) / (SHI * wsn(i))
#             isn(i) = 1.d0
#         endif
#     end do
# end subroutine hsn_to_tsn

def temp_to_senth(tsn, isn):
    """tsn: [C]
        Temperature
    isn: [1]
        Water fraction"""

    # When tsn == 0...
    senth = -isn * LHM

    when_a = (tsn > 0.)
    senth[when_a] = tsn[when_a] * SHW

    when_b = (tsn < 0.)
    senth[when_b] = tsn[when_b] * SHI - LHM

    return senth

def senth_to_temp(shsn):
    """Converts specific enthalpy of ice to (temperature, water fraction)"""

    nans = np.isnan(shsn)

    # Else clause first
    tsn = shsn * (1./SHI) + LHM/SHI            # Temperature [C]
    isn = np.zeros(shsn.shape)                # Water content [1]

    tsn[nans] = np.nan
    isn[nans] = np.nan

    where_b = (shsn > -LHM)
    tsn[where_b] = 0.
    isn[where_b] = (-shsn[where_b] * (1./LHM))

    where_a = (shsn > 0.)
    tsn[where_a] = (shsn[where_a] * (1./SHW))
    isn[where_a] = 0.

    return tsn,isn

def enth_to_temp(hsn, wsn):    # hsn=enthalpy, wsn=mass
    with np_seterr(invalid='ignore'):
        return senth_to_temp(hsn / wsn)

