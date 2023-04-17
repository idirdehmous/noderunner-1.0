###############
# DIRECTORIES #
###############

d_ETC=$BASEDIR/etc # constants, ...
d_CYCLE=$BASEDIR/cycle # first guess for next run
d_CONST=$BASEDIR/const

# constant data paths (this data is staged to scratch with rsync or linked)
# TODO: these definitions should be elsewhere...
DPATH=@DATA_PATH@
DPATH_CLIM=@DPATH_CLIM:${DPATH}/clim/default@
DPATH_CONST=@DPATH_CONST:${DPATH}/const@
DPATH_ETC=@DPATH_ETC:${DPATH}/etc@
if [[ $ASSIMILATION == yes ]] ; then
  DPATH_JB=@DPATH_JB:${DPATH}/Jb@
fi
d_TOOLS=$DPATH/tools

##########################################
# WORK directories common for all cycles #
##########################################

d_BIN=$BASEDIR/bin
#d_TOOLS=$BASEDIR/tools
# NOTE: adding this to PATH is usually safe (also when running on another server than HPC...)
export PATH="$d_TOOLS:$d_BIN:$PATH"
# in rare cases, we may need scripts from gmkpack that are not in /bin
PACKDIR=@PACKDIR@

DATADIR_RUNTIME=${d_CONST}/runtime_data
DATADIR_ECOCLIMAP=${d_CONST}/ecoclimap
DATADIR_SAT=${d_CONST}/sat_const

d_CLIM=$BASEDIR/clim
d_JB=$BASEDIR/Jb
d_NAMELIST=$BASEDIR/name
###

WORKDIR=@WORKDIR:${BASEDIR}/work/run$(echo $RUNDATE | cut -c 9-10)@

# we have variables for all task directories
# that may be a bit of overhead
# but at least it is manageable from 1 file
d_LBC=$WORKDIR/lbc
d_FC=$WORKDIR/forecast
d_POST=$WORKDIR/post
if [[ $ASSIMILATION == yes ]] ; then
  d_GUESS=${WORKDIR}/assimilation/guess
  d_OBS=${WORKDIR}/assimilation/obs
  d_ODB=${WORKDIR}/assimilation/ODB
# the following directories depend on "upper" or "surface" assimilation step
  d_ASSIM=$WORKDIR/assimilation/${ASSIM_LABEL}
  d_BATOR=${d_ASSIM}/bator
  d_ADDFIELDS=${d_ASSIM}/addfields
  d_SST=${d_ASSIM}/sst
  d_CANARI=${d_ASSIM}/canari
  d_SCREENING=${d_ASSIM}/screening
  d_3DVAR=${d_ASSIM}/minim
fi

