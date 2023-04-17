######################
# LOCAL settings     #
# platform dependent #
# suite dependent    #
######################

# executables

# we also expect standard RMI utilities from MODULE

#CREATE_IOASSIGN=$PACKDIR/src/main/odb/scripts/create_ioassign
#FIXME: maybe there shouldn't be a reference to $BASEDIR in the local settings!
MERGE_IOASSIGN=$BASEDIR/etc/ioassign/merge_ioassign.43t2
CREATE_IOASSIGN=$BASEDIR/etc/ioassign/create_ioassign.43t2

##############
# ARCHIVING  #
##############

#  ARCH_HOST=@ARCH_HOST:hpca-login@ # hpca-login | bofur | nori | moria
# for users: don't use hpca-login, because HDS_ALD_DATA is not mounted there
# for oper: set to @HPC_HOST@
ARCH_HOST=@ARCH_HOST@
ARCH_PATH=@ARCH_PATH@

# where are archived LBC's?
if [ $( echo $ARCH_HOST | cut -c 1-3 ) = "hpc" ] ; then
  OPER_PATH=/mnt-meteo/HDS_ALADIN/ALADIN
else
  OPER_PATH=/mnt/HDS_ALADIN/ALADIN
fi

#ARCH_NESTING=@ARCH_NESTING:${OPER_PATH}/OPER/RECENT@
#ARCH_TELECOM=@ARCH_TELECOM:${OPER_PATH}/telecom@

# observations (/may/ be different from arch!)
OBS_HOST=@OBS_HOST:${HPC_HOST}@
OBS_PATH=@OBS_PATH:/mnt-meteo/HDS_ALADIN/ALADIN/OBSERVATIONS/bufr@

# AFD _SHELF : always use the HPC mount
AFD_SHELF_HOST=@HPC_HOST@
AFD_SHELF_PATH=/mnt-meteo/afd_shelf # for model data: HDS_AFD_MODELS
# NOTE: if you use moria, it is /mnt/afd_data/shelf !!!

#########################
# scratch manipulation: #
#########################

# find the same path on the alternative scratch
# original path may be a link
# you can "guess" $scratch via "realpath"!
# at RMI it's either /scratch-[ab] or /scratch-op-[ab]
# ATTENTION: - realpath only works if you run it on hpc
#            - may not work if current scratch is down
#  if [[ `echo $scratch | grep a$ -` ]] ; then
#    scratch2=`echo $scratch | sed "s/a$/b/"`
#  path2=$(realpath $path | sed "s/$scratch/$scratch2/")
# so for safety we only do the simple a <-> b swap
function other_scratch {
#  path=$1
#  scratch=$( echo $(realpath $path ) | cut -d/ -f2)
  scratch=$1
  if [[ `echo $scratch | grep scratch-a ` ]] ; then
    scratch2=`echo $scratch | sed "s/scratch-a/scratch-b/"`
  elif [[ `echo $scratch | grep scratch-b ` ]] ; then
    scratch2=`echo $scratch | sed "s/scratch-b/scratch-a/"`
  elif [[ `echo $scratch | grep scratch-op-a ` ]] ; then
    scratch2=`echo $scratch | sed "s/scratch-op-a/scratch-op-b/"`
  elif [[ `echo $scratch | grep scratch-op-b ` ]] ; then
    scratch2=`echo $scratch | sed "s/scratch-op-b/scratch-op-a/"`
  else
    echo ERROR: not a scratch path!
    exit 1
  fi
  echo $scratch2
}

SCRATCH=@SCRATCH:/scratch-a/@HPC_USER@@
SYNC_SCRATCH=$(boolean @SYNC_SCRATCH:no@)
if [[ ${SYNC_SCRATCH} == yes ]] ; then
  SCRATCH2=$(other_scratch $SCRATCH)
  BASEDIR2=$(other_scratch $BASEDIR)
fi

function afd_save {
# NOTE: copying to AFD_REPOSITORY is not the same as AFD_SHELF !
#       there is some delay, so we shouldn't trigger other products?
  # for putting on AFD:
  # use .tmp extension while copying !
  #     does rsync do this automatically? has *random* extension
  # and rename after copy is complete
  local mfile=$1
  local fname=$(basename $mfile)
  local arch_host=`echo $2 | cut -d":" -f 1`
  local arch_path=`echo $2 | cut -d":" -f 2`
  # NOTE: we use "ssh -n" to make sure everything works OK
  #       even if the script is run via "ssh < <script>"
  # NOTE: unless we're testing on a dummy, we should *never* create directories on afd_repository !
#  ssh -n ${arch_host} " [ -e $arch_path ] || mkdir -p $arch_path "
  rsync $mfile ${arch_host}:${arch_path}/.$fname
  ssh -n $arch_host chmod 644 ${arch_path}/.$fname
  ssh -n $arch_host mv ${arch_path}/.$fname ${arch_path}/$fname
}

# saving to archive
function archive_save {
  local mfile=$1
  local fname=$(basename $mfile)
  local arch_host=`echo $2 | cut -d":" -f 1`
  local arch_path=`echo $2 | cut -d":" -f 2`

  ssh -n ${arch_host} " [ -e $arch_path ] || mkdir -p $arch_path "
  rsync $mfile ${arch_host}:${arch_path}

}

###########################################

# LBC retrieval #
function retrieve_lbc {
  local hh=$1
  local lbc_hh=$(printf %02g $(( 10#$hh + 10#$LBC_LAG )) )

  if [[ $REALTIME == yes && $DELAY == no ]] ; then
    if [[ $COUPLING == direct_afd ]] ; then
      scp ${AFD_SHELF_HOST}:${AFD_SHELF_PATH}/models/alaro/coupling/$LRR/COUPL0${lbc_hh} LBC_$hh
    elif [[ $COUPLING == direct ]] ; then
      ln -sf /home/ald_op/OPER/Suite/telecom/$LRR/image${lbc_hh} LBC_$hh
    else
      ln -sf /home/ald_op/OPER/Suite/work/fc_ao40_$LRR/ICMSHAO40+00${lbc_hh} LBC_$hh
    fi
    # TODO: check the file date (it could be from yesterday...)
  else
    # archived data is in a tar file
    # parallel lbc retrieval: only retrieve for $hh == 00
    if [[ $COUPLING == direct || $COUPLING == direct_afd ]] ; then
      tarfile=${OPER_PATH}/telecom/$(date -u -d $LYMD +"%Y/%m/%d")/telecom-${LYMD}r${LRR}.tar
      templ=image
    else
      # get a tar file from the "RECENT" operational archive
      # containing hourly full historical files
      # only available for the past 30 days
      # i.e. we should check that RUNDATE is less than 1 month in the past
      # Let's not worry about a few hours difference.
      oldest_recent=$(date -u -d "today -1 month" +%Y%m%d%H)
      if (( $RUNDATE < ${oldest_recent} )) ; then
        echo "ERROR: RUNDATE $RUNDATE is no longer available from RECENT."
        exit 1
      fi
      tarfile=${OPER_PATH}/OPER/RECENT/ao40_${LDD}${LRR}.tar
      templ=ICMSH${COUPLING}+00
    fi
    if [[ $hh == 00 ]] ; then
      rsync ${ARCH_HOST}:$tarfile .
    elif [[ $lbc_parallel == yes ]] ; then
      while [[ ! -e LBC_00 ]] ; do
        sleep 10
      done
    fi
    tar -xf $(basename $tarfile) ${templ}${lbc_hh}
    mv ${templ}$lbc_hh LBC_$hh
  fi
}

###########################################
# OBSERVATIONS #
################

# raw GTS observations:
GTS_synop=${AFD_SHELF_PATH}/observations/bufrsynops
GTS_amdar=${AFD_SHELF_PATH}/observations/amdar
GTS_temp=${AFD_SHELF_PATH}/observations/bufrtemp


function GetMissing(){
  # FUNCTION TO GET SYNOP OBS AT LEAST FROM OGIMET WEBSITE
  # TO AVOID THE SUITE TO CRASH FOR MISSING OBS
  obstype=$1
  cd ${d_OBS}
  case $obstype in
    synop)
      TYPE=IS
      CC="EBSZ EBUM EBWM EHAM EHDB LFPW EDZW EBBR EBSH EBST EGRR"  ;;
    amdar)
      TYPE=IUA
      CC="EBSZ EBUM EBWM EHAM EHDB LFPW EDZW EBBR EBSH EBST EGRR"  ;;
    temp)
      TYPE=IU
      CC="LFPW EDZW EGRR" ;;  # FOR TEMP THESE CENTERS SEND STRUCTURED BUFR FILES
    *)
      CC=" " ;;
  esac

  url="http://www.ogimet.com/getbufr.php?res=tar"
  for  cc in ${CC} ; do
    echo $cc
    curl "$url&beg=${RUNDATE}00&end=${RUNDATE}00&ecenter=${cc}&type=${TYPE}" -o ${cc}_${RUNDATE}00.bufr
    if  [ -f  ${cc}_${RUNDATE}00.bufr  ]  ;  then
      cat ${cc}_${RUNDATE}00.bufr >> ${obstype}_${RUNDATE}00.bufr
    else
      echo "File not in ogimet database"
      continue
    fi
    rm  -f  ${cc}_*.bufr
  done
}

function GetRadar () {
# RADAR STATION NAMES
  RadarSites="bejab bewid behel bezav frave"
  HdsPath=/mnt/HDS_RADAR_EDP/realtime
  Suffix=pvol/dbzh/scanz/hdf

  i=0
  for stat in ${RadarSites} ; do
    #i=$(( $i + 1 ))
    echo $stat
    ArchName="${YYYY}${MM}${DD}.rad.${stat}.pvol.dbzh.scanz.tar"
    # GET RADAR FILE FROM REMOTE SERVER ( HDS_RADAR_EDP
    if  ssh ${OBS_HOST} [ -f  ${HdsPath}/$YYYY/$MM/$DD/${stat}/${Suffix}/${ArchName}  ] ; then
      scp ${OBS_HOST}:${HdsPath}/${YYYY}/${MM}/${DD}/${stat}/${Suffix}/${ArchName}  .

      ArchivePath=home/rad_op/.rmiradpro/realtime/${YYYY}/${MM}/${DD}/${stat}/pvol/dbzh/scanz/hdf
      FileName=${ArchivePath}/${RUNDATE}0000.rad.${stat}.pvol.dbzh.scanz.hdf
 
      # CHECK EXISTENCE IN .tar FILE
      if tar -tf ${ArchName}  ${FileName} >/dev/null 2>&1  ; then
        i=$(( $i + 1 ))
        tar -xvf   ${ArchName}  ${FileName}

        # RENAME THE FILE AS EXPECTED BY batormap
        cp ${FileName} HDF5.site${i}
        rm -rf home
      else
        echo "File  ${FileName} doesn't exist in tar file   !"
        continue
      fi
    else
      echo "$ArchName  doesn't exist on ${OBS_HOST}  server !"
      continue
    fi
  done
  # REMOVE ARCHIVE FILES 
  rm -f  *.tar  
}

function SynopLocal() {
  if [[ `dateincr -h $RUNDATE +120` < `date -u +%Y%m%d%H` ]] ; then
    # GTS data is only available for 5 days=120h.
    echo "ERROR: no observations available from GTS for date $RUNDATE."
    exit 1
  fi
  echo "extracting BUFR $obstype data from GTS."
  # the aladin module may clash with python/3.7.5
  module purge
  module load gts_extract/v1
  # first use a ramdisk for a copy of the GTS data (and the SQLite file)
  # then copy GTS BUFR data and run extraction
  if [[ -e /dev/shm ]] ; then
    ln -sf /dev/shm ramdisk
  else
    mkdir ramdisk
  fi
  ls ramdisk
  mkdir -p ramdisk/GTS/$obstype
 
  # the GTS BUFR's may have arrived in the time slot just before RUNDATE
  # (e.g. just a few seconds before 12UTC)
  # NOTE: the AFD directories are in UTC
  #       so if you get "yyyymmdd03" this is in fact 01UTC or 02UTC (depending on summer time)
  #       BUT: make sure to retrieve enough /later/ directories!!!
  mindate=`dateincr -h $RUNDATE -2` # we go 2h back just in case. Also necessary if obs window> 1h
  echo $mindate
#    rsync ${OBS_HOST}:${GTS_OBS}/ ramdisk/GTS/
  case $obstype in
    synop) obsdir=${AFD_SHELF_PATH}/observations/bufrsynops ;;
    amdar) obsdir=${AFD_SHELF_PATH}/observations/amdar ;;
    temp)  obsdir=${AFD_SHELF_PATH}/observations/bufrtemp ;;
  esac
  while [[ $mindate -le `date -u +%Y%m%d%H` ]] ; do
    rsync -a ${AFD_SHELF_HOST}:${obsdir}/$mindate ramdisk/GTS/$obstype || {
      echo $obsdir/$mindate appears to be missing.
    }
    mindate=`dateincr -h $mindate +1`
  done
  ls ramdisk/GTS/$obstype
  # call gts extraction. We also put the SQLite file in the ramdisk
  # the obs file is placed in the current directory
  gts_extract_${obstype}.py $RUNDATE ./ramdisk/GTS/$obstype ./ramdisk/GTS/$obstype
  rm -rf ramdisk/GTS/$obstype
}

function GetModes() {
  OBS_PATH=/mnt/HDS_ALD_TEAM/ALD_TEAM/OBS/MODE-S/bufr
  #  DATE : 15 MINUTES BEFORE AND AFTER THE OPTIMAL TIME ( ONLY FOR MODE-S)
  BDATE=$(date -d "${YYYY}${MM}${DD} ${RR} -15 minutes" +%Y%m%d%H%M )
  NDATE=$(date -d "${YYYY}${MM}${DD} ${RR} +15 minutes" +%Y%m%d%H%M )
  echo "$BDATE -- $NDATE"
  yy1=$( echo $BDATE | cut -c1-4   )   ;  yy2=$( echo $NDATE | cut -c1-4   )
  mm1=$( echo $BDATE | cut -c5-6   )   ;  mm2=$( echo $NDATE | cut -c5-6   )
  dd1=$( echo $BDATE | cut -c7-8   )   ;  dd2=$( echo $NDATE | cut -c7-8   )
  hh1=$( echo $BDATE | cut -c9-10  )   ;  hh2=$( echo $NDATE | cut -c9-10  )
  mn1=$( echo $BDATE | cut -c11-12 )   ;  mn2=$( echo $NDATE | cut -c11-12 )
  obsfile=${OBS_PATH}/$YYYY/$MM/$DD/Mode-S-EHS_MUAC_${YYYY}${MM}${DD}_${RR}00.bufr
  obsfile1=${OBS_PATH}/$yy1/$mm1/$dd1/Mode-S-EHS_MUAC_${yy1}${mm1}${dd1}_${hh1}00.bufr #15' before
  obsfile2=${OBS_PATH}/$yy2/$mm2/$dd2/Mode-S-EHS_MUAC_${yy2}${mm2}${dd2}_${hh2}00.bufr #15' after

  for ff in $obsfile $obsfile1 $obsfile2 ; do
    if  ssh ${OBS_HOST} [ -f  $ff ] ; then
      scp ${OBS_HOST}:$ff  .
    else
      echo "mode-s : $ff not found in archive"
    fi
  done
  cat Mode-S-EHS_MUAC*.bufr  > modes_${RUNDATE}00.bufr 
  rm  -f  Mode-S-EHS_MUAC*.bufr
}

function retrieve_obs () {
  if  [ $obstype == "radar" ] ; then
    GetRadar
  elif [ $obstype == "modes" ] ; then
    GetModes
  else 
    case $obstype in
      temp)
        OBS_PATH=/mnt/HDS_ALD_TEAM/ALD_TEAM/idehmous/DASK/bufr/TEMP  ;;
      gpssol)
        OBS_PATH=/mnt/HDS_ALD_TEAM/ALD_TEAM/idehmous/DASK/bufr/GPS   ;;
      *)
        OBS_PATH=/mnt/HDS_ALADIN/ALADIN/OBSERVATIONS/bufr ;;
    esac
    obsfile=${OBS_PATH}/$YYYY/$MM/$DD/${obstype}_${RUNDATE}00.bufr

    # CHECK THE FILES'S EXISTENCE DIRECTLY IN THE REMOTE SERVER !
    if ssh ${OBS_HOST} [ -f ${obsfile}  ] ; then
      echo "$obstype exists in archive !"
      scp ${OBS_HOST}:${obsfile}  .
    else
      echo "$obstype : $obsfile not found !"
    fi
  fi
}
 
