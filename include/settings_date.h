#################
# DATE SETTINGS #
#################

# skip this if RUNDATE is not set (e.g. initSuite)
if [[ $RUNDATE != "" ]] ; then

# to avoid some common errors: make sure the date is well-formed
# RUNDATE must be a string of length 10: YYYYMMDDRR
  if [[ ${#RUNDATE} != 10 ]] ; then
    echo "Malformed RUNDATE: $RUNDATE"
    exit 1
  fi

  YYYY=`echo $RUNDATE | cut -c 1-4`
  MM=`echo $RUNDATE | cut -c 5-6`
  DD=`echo $RUNDATE | cut -c 7-8`
  RR=`echo $RUNDATE | cut -c 9-10`

### next and previous month (for clim files)
  MMprev=`date -u -d "$YYYY${MM}01 -1 month" +%m`
  MMnext=`date -u -d "$YYYY${MM}01 +1 month" +%m`


### previous $ next cycle date (we may need them)

  PREV_RUNDATE=`date -u -d "$YYYY$MM$DD $RR -$CYCLE_INC hours" +%Y%m%d%H`
  PREV_YYYY=`echo $PREV_RUNDATE | cut -c 1-4`
  PREV_MM=`echo $PREV_RUNDATE | cut -c 5-6`
  PREV_DD=`echo $PREV_RUNDATE | cut -c 7-8`
  PREV_RR=`echo $PREV_RUNDATE | cut -c 9-10`

  NEXT_RUNDATE=`date -u -d "$YYYY$MM$DD $RR +$CYCLE_INC hours" +%Y%m%d%H`
  NEXT_YYYY=`echo $NEXT_RUNDATE | cut -c 1-4`
  NEXT_MM=`echo $NEXT_RUNDATE | cut -c 5-6`
  NEXT_DD=`echo $NEXT_RUNDATE | cut -c 7-8`
  NEXT_RR=`echo $NEXT_RUNDATE | cut -c 9-10`
fi


