#####################
# utility functions #
#####################

function complete_and_exit {
  # when completing a task early (i.e. without getting to tail.h)
  # in fact you could call this function at the end of 
  # every task in stead of including head.h
  # OR: just replace it by include tail.h ?
  if [[ $1 != "" ]] ; then
    echo "complete_and_exit: $1"
  fi
@include <tail.h>
#  TASK_FINISH_TIME=`date -u +"%Y-%m-%d %H:%M:%S"`
#  echo "===== TASK STARTED:  ${TASK_START_TIME:-unknown} ====="
#  echo "===== TASK FINISHED: ${TASK_FINISH_TIME:-unknown} ====="

#  ecflow_client --complete
#  trap 0
#  exit 0
}

function boolean {
  # returns a standard string value
  # that can be evaluated directly
  case $1 in
    y|yes|Y|YES|true|T|1) echo yes ;;
    n|no|N|NO|false|F|0) echo no ;;
    *) echo "not a boolean" ; exit 1 ;;
  esac
}
# if you return true|false you can do "if $(boolean $x) ; then ..."
# but yes/no may be a bit more common in scripting?

# return workdir for a certain cycle date
# useful to e.g. address the previous cycle's output for nesting
function workdir {
  local fcdate=${1:-$RUNDATE}
  local basedir=${2:-$BASEDIR}

  local fcRR=`echo $fcdate | cut -c 9-10`
  echo $basedir/work/run_$fcRR
}

##############################################
# extract date and lead time from an FA file #
##############################################

# uses the very simple fa_checkdate python script

function fa_rundate {
  local fafile=$1
  echo `fa_checkdate $fafile | cut -d"+" -f1`
}

function fa_leadtime {
  local fafile=$1
  echo `fa_checkdate $fafile | cut -d"+" -f2`
}

function fa_validdate {
  local fafile=$1
  local fadate=`fa_checkdate $fafile`
  local yyyymmdd=`echo $fadate | cut -c 1-8`
  local rr=`echo $fadate | cut -c 9-10`
#  local rundate=`echo $fadate | cut -d+ -f1`
  local ldt=`echo $fadate | cut -d+ -f2`
  echo `date -u -d "$yyyymmdd ${rr} +$ldt hours" +%Y%m%d%H`
}



function  GetMarsObs () {

# obsdate in hours, obsrange in minutes (+/- range around the hour)
# GET OBS HOUR AND WINDOW ( RANGE )
OBSTYPE=$1                   # ${1:-2022070100}
OBSDATE=$2                   # ${3:-60}
OBSRANGE=$3
GROUP=CONV                   # COULD BECOME AN ARGUMENT LET'S START WITH  CONV DATA

set -x
# GET TIME WINDOW RANGE  +/- OBSRANGE  ( 3h )
DATE=`dateincr -m ${OBSDATE}00 -${OBSRANGE}`
YYYY=`echo $DATE | cut -c 1-4`
MM=`echo $DATE | cut -c 5-6`
DD=`echo $DATE | cut -c 7-8`
HH=`echo $DATE | cut -c 9-10`
mm=`echo $DATE | cut -c11-12`

# Time=2100, range=360 (=6h),
# Denotes observations ---> from 21:00 to 03:00 next day

TIME=${HH}${mm}
RANGE=$(( ${OBSRANGE} * 2 ))

# MARS OBSERVATION ID IDENTIFICATIONS  (SEE https://apps.ecmwf.int/odbgov )
# LAND-SURFACE SYNOP: LSD=1/2/3/4/
# SEA: SSD               =9/11/12/13/14/19/20/21/22/23
# VERTICAL: VSNS=91/92/95/96/97/101/102/103/104/105/106/107/109/111/112/113
# GPSSOL  : 110
# METAR   : 140

# OBSTYPE ID
SYNOP="1/2/3/4/9/11/12/13/14/19/20/21/22/23"
AMDAR="144/145/146"
TEMP="101/102/103/106/109"
GPSSOL="110"
MODES="150"

# AREA DEFINITION
# NORTH/WEST/SOUTH/EAST or "GLOBE" FOR ALL
AREA=65/-20/40/20

case ${OBSTYPE} in
     synop ) PARAM=${SYNOP}  ;;
     amdar ) PARAM=${AMDAR}  ;;
     temp  ) PARAM=${TEMP}   ;;
     gpssol) PARAM=${GPSSOL} ;;
     modes ) PARAM=${MODES}  ;;
esac

REQFILE=${OBSTYPE}_${OBSDATE}.req
# START MARS REQUEST BODY
echo RETRIEVE,                                                                                      > ${REQFILE}
echo CLASS    = od,STREAM= OPER,EXPVER=1,REPRES= BUFR, TYPE=OB,OBSGROUP= ${GROUP},DUPLICATES = remove, >> ${REQFILE}

# META DATA
echo OBSTYPE  = ${PARAM},  DATE= ${YYYY}${MM}${DD},TIME= ${TIME},RANGE = ${RANGE},AREA = ${AREA},      >> ${REQFILE}

# TARGET OUTFILE
echo TARGET   = ${OBSTYPE}_${OBSDATE}00.bufr   							       >> ${REQFILE}

# RUN REQUEST
mars ${REQFILE}  1>  ${OBSTYPE}_${OBSDATE}_mars.log   2>&1
}



