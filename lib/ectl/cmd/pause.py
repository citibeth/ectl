#!/bin/sh
# 
# ## defaults
#   CMRUNDIR='/u/cmrun'
#   if [ -f $HOME/.modelErc ]; then . $HOME/.modelErc; fi
# 
#   if [ $# -ne 1 ] ; then
#       echo "Usage: sswE RUNID"
#       echo "Stops the model run RUNID"
#       exit; fi
#   RUNID=$1
# 
#   if [ ! -d $CMRUNDIR/$RUNID ] ; then
#       echo "Run directory not found: $CMRUNDIR/$RUNID"
#       exit ; fi
# 
#   cd "$CMRUNDIR/$RUNID"
#   if [ -s flagGoStop ] ; then
#     if grep STOP flagGoStop  > /dev/null ; then
#       echo "$RUNID is already stopped"; exit; fi
#     echo "__STOP__" > flagGoStop
#     echo "Set the flag to STOP position. Please wait for $RUNID to stop."
#   elif [ -s sswOnOff ] ; then  # be compatible with older runs
#     if grep OFF flagGoStop  > /dev/null ; then
#       echo "$RUNID is already stopped"; exit; fi
#     echo "___OFF__" > sswOnOff
#     echo "Set the switch to OFF position. Please wait for $RUNID to stop."
#   elif [ -s fort.3 ] && [ "`strings fort.3`" = XXXXXXXX ] ; then
#     # be compatible with very old runs
#     echo "___OFF__" > fort.3
#     echo "Set the switch to OFF position. Please wait for $RUNID to stop."
#   else
#     echo "flagGoStop not found. $RUNID not running?  No action ..."
#   fi
# 
def pause():
    pass

