# main settings
# make all output etc. readable to others
umask 0022 

SUITE=@SUITE@
HPC_USER=@HPC_USER@
HPC_HOST=@HPC_HOST@
BASEDIR=@BASEDIR@

#host=`echo ${HOSTNAME,,} | cut -f1 -d'.' ` # requires bash >= 4
host=`echo "$HOSTNAME" | tr '[:upper:]' '[:lower:]' | cut -f1 -d'.' `

@include <settings_functions.h>

###########################
### ecFlow dependencies ###
###########################

CYCLE_INC=@CYCLE_INC@
RUNMODE=@MODE:exp@ # oper | exp
#FIXME: better let $DELAY depend directlty on RUNDATE and real date
#       the macro should mainly be used in triggers only
DELAY=$(boolean @DELAY:no@) # set to yes if running in delayed mode
  # this turns off date-checking and gets LBC's from RECENT archive
# is this a "realtime" suite?
REALTIME=$(boolean @REALTIME:no@)

USER=@USER@
# HOST=@HOST@
# In fact, we never use the HOST variable inside the job
# that variable is ONLY used for running/submitting the job correctly
######


RUNDATE=@RUNDATE:""@
DOMAIN=@DOMAIN@
CNMEXP=@CNMEXP@
HOURRANGE=@FCLEN:0@
NLEVELS=@NLEVELS@
TIMESTEP=@TIMESTEP@
THIS_RUN=@THIS_RUN@
PREV_RUN=@PREV_RUN@
NEXT_RUN=@NEXT_RUN@



# basic model switches
MODEL=@MODEL@  # arome | alaro
SURFACE=@SURFACE@ # isba | surfex
HYDROSTATIC=$(boolean @HYDROSTATIC@)
DFI=$(boolean @DFI:yes@)
ASSIMILATION=$(boolean @ASSIMILATION:yes@)
if [[ $ASSIMILATION == yes ]] ; then
  ASSIM_UPPER=@ASSIM_UPPER:none@
  ASSIM_SURFACE=@ASSIM_SURFACE:none@
  COLDSTART=@COLDSTART:yyyymmddhh@
  OBSTYPES="@OBSTYPES: @"
  OBSTYPES_SURFACE="@OBSTYPES_SURFACE: @"
  OBSTYPES_UPPER="@OBSTYPES_UPPER: @"
  OBS_SOURCE=@OBS_SOURCE:mars@
  ODB_ARCH=@ODB_ARCH:no@
  ODB_PATH=@ODB_PATH:""@
  ASSIM_LABEL=@ASSIM_LABEL:""@ # are we in surface or upper?
else
  ASSIM_UPPER=none
  ASSIM_SURFACE=none
fi


OBS_NPOOL=@OBS_NPOOL:4@

# IO server (forecast only)
NPROC_IO=@NPROC_IO:0@
if [[ $NPROC_IO -gt 0 && @TASK@ == "integration" ]] ; then
  IO_SERVER=yes
else
  IO_SERVER=no
fi

# Climate files
PGD_FILE=@PGD_FILE:${DOMAIN}_PGD_2L.fa@

# boundary conditions:
COUPLING=@COUPLING:none@ # meaning may depend on type of suite
LBC_INC=@LBC_INC@
COUPLING_DOMAIN=@COUPLING_DOMAIN@

# who do we wake up when things go wrong?
# TODO: should we have a "verbosity-level" oper vs exp?
MAIL_LIST=@MAIL_LIST:""@

###########################

@include <settings_date.h>
@include <settings_namelists.h>
@include <settings_directories.h>
##include <settings_local_@PLATFORM@.h>

