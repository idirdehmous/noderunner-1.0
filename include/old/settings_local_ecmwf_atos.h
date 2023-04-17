######################
# LOCAL settings     #
# platform dependent #
# suite dependent    #
######################

# On atos, troika uses "hpc" to submit
# But if another task needs to connect to HPC (ssh ...) it must be
# hpc-login
HPC_HOST=${HPC_HOST}-login

# executables

#CREATE_IOASSIGN=$PACKDIR/src/main/odb/scripts/create_ioassign
#FIXME: maybe there should not be a reference to $BASEDIR in the local settings!
MERGE_IOASSIGN=$BASEDIR/etc/ioassign/merge_ioassign.43t2
CREATE_IOASSIGN=$BASEDIR/etc/ioassign/create_ioassign.43t2


##############
# ARCHIVING  #
##############

# NOTE: don't call this from TC suites!
function archive_save {
  local mfile=$1
  local arch_path=`echo $2 | cut -d":" -f 2`
  emkdir -p ec:$arch_path
  ecp $mfile ec:${arch_path}

}

# transfer to RMI
function transfer_output {
  # copy to RMI via ectrans
  local lfile=$1
  local RMIPATH=${2:-../../../mnt/HDS_ALADIN/ESUITE/ECMWF}

  ectrans -gateway moria.oma.be -remote nori@@genericSftp -put \
      -source $lfile  \
      -target ${RMIPATH}/$lfile
}

#################
# LBC retrieval #
#################

function retrieve_lbc {
  # retrieve LYYY-LMM-LDD-LRR (possibly lagged) LBC's
  # NOTE: for now, we assume that we never need to go further than $HOURRANGE,
  #       i.e. only short forecasts have lagged LBC's
  local hdir=$(pwd)
  local lbcdir=$SCRATCH/telecom/$(date -u -d $LYMD +"%Y/%m/%d")/$LRR
  case $COUPLING in
    RMI-ectrans)
      CPL=CPLD
      # LBC retrieval from RMI via ectrans
# CPL_TEMPLATE=$SCRATCH/telecom/YYYY/MM/DD/RR/$(date -u -d $LYMD +"%Y/%m/%d")/imageHH

      local tarfile=telecom-${LYMD}r${LRR}.tar
      local sdir="/mnt/HDS_ALADIN/ALADIN/telecom/$(date -u -d $LYMD +"%Y/%m/%d")"
      if [[ ! -e ${lbcdir}/$tarfile ]] ; then
        module load ecaccess
        mkdir -p $lbcdir
        ectrans -gateway nogrod.oma.be -remote ad_kili@@genericSftp -get \
          -source ../../${sdir}/$tarfile   \
          -target ${lbcdir}/$tarfile
      fi
      cd $lbcdir
      tar xf $tarfile
      cd $hdir
      for hh in $(seq -f%02g 0 $LBC_INC $HOURRANGE) ; do
        local lbc_hh=$(printf %02g $(( 10#$hh + 10#$LBC_LAG )) )
#        ln -sf $lbcdir/image${lbc_hh} ICMSH${CPL}+00$hh
        ln -sf $lbcdir/image${lbc_hh} LBC_$hh
      done
      ;;
    HRES-mars-*)
# FIXME: hard-coded path
      lbcdir=$SCRATCH/LBC/ec/$RR/input
      CPL=E903
      if [[ ! -e $lbcdir/ICMGG${CPL}+000000 ]] ; then
      mkdir -p $lbcdir/mars
      cd $lbcdir/mars
      STEPS=0/to/${HOURRANGE}/by/${LBC_INC}

      # class: ea (era5), od, en, ???be
      # stream: oper , scda (short cutoff), enda (ens da), enfo (ens. forecast)...
      # type: an, fc (ob, ai, im)
      levs=137
      gp_fields=133/203/75/76/246/247/248
      sp_fields=152/138/155/130/135
      # surface:
      # FIXME: at every step? Really?
      sfc_fields=198.128/235.128/10.228/11.228/12.228/13.228/14.228/238.128/34.128/35.128/36.128/37.128/38.128/148.128/8.228/9.228/129.128/31.128/7.228/26.128/139.128/170.128/183.128/236.128/39.128/40.128/41.128/42.128/141.128/32.128/33.128/172.128/66.128/67.128
      # surf fields at step=0
      sfc_00=74/163/43/160/161/162/27/28/16/17/18/30/15/29
      # clim?
      sfc_ct=234/173/174
      # spec OROGRAPHY only at lowest model level: geopotential
      sp_lev1_fields=129.128

      # Some (surface) fields are only in the analysis, not the forecast
      # Should we also retrieve Model Levels from analysis? Or step=0?
      case $LRR in
        00|12) stream=oper ;;
        06|18) stream=scda ;;
      esac

      # NOTE: [date]_[time] could be dropped in the file names
      #       as it is constant anyway
      cat << EOF > mars.req
      retrieve,
        stream=$stream,
        class=od,
        type=fc,
        expver=1,
        date=${LYYYY}-${LMM}-${LDD},
        time=${LRR},
        step=${STEPS},
        levtype=ml,
        levelist=1/to/${levs},
        param=${gp_fields},
        target="fc_atm_pdg_[step]"

      retrieve,
        param=${sp_fields},
        target="fc_atm_spe_[step]"

      # Do I need surface fields for every step? Not for coupling but maybe for c903?
      retrieve,
        levtype=sfc,
        step=${STEPS},
        param=${sfc_fields},
        target="fc_sol_pdg_[step]"

      # SURFACE FIELDS FROM ANALYSIS (not in every step)
      # FIXME: this will be wrong if there is e.g. a 3h lag
      retrieve,
        type=an,
        step=00,
        param=74/163/43/234/173/174/160/161/162/27/28/16/17/18/30/15/29,
        target="ana_sol_pdg_0000"

      #special: spectral orography?  is SP at levl1
      retrieve,
        levtype=ml,
        levelist=1,
        param=129.128,
        grid=off,
        target="ana_oro_spe_0000" 
EOF

      mars mars.req 1> mars_${RUNDATE}.log 2>&1
      # combine into 3 files (GP, SP, SFC) per step
      RR1=$(( 10#$RR ))
      for hh in $(seq -f%02g 0 $LBC_INC $HOURRANGE) ; do
        hh1=$(( 10#$hh ))
        mv fc_atm_pdg_${hh1}  ICMUA${CPL}+0000$hh
        mv fc_sol_pdg_$hh1 ICMGG${CPL}+0000$hh
        cat ana_sol_pdg_0000 >> ICMGG${CPL}+0000$hh
        mv fc_atm_spe_$hh1 ICMSH${CPL}+0000$hh
        cat ana_oro_spe_0000 >> ICMSH${CPL}+0000$hh 
      done
      fi
      for hh in $(seq -f%02g 0 $LBC_INC $HOURRANGE) ; do
        local lbc_hh=$(printf %02g $(( 10#$hh + 10#$LBC_LAG )) )
        ln -sf $lbcdir/mars/ICMUA${CPL}+0000$hh $lbcdir/ICMUA${CPL}+0000${lbc_hh}
        ln -sf $lbcdir/mars/ICMGG${CPL}+0000$hh $lbcdir/ICMGG${CPL}+0000${lbc_hh}
        ln -sf $lbcdir/mars/ICMSH${CPL}+0000$hh $lbcdir/ICMSH${CPL}+0000${lbc_hh}
      done
      cd $hdir
      ;;

    *) echo "Unknown LBC retrieval method."
       exit 1 ;;
  esac
}

# OBS retrieval from RMI
function retrieve_obs {
  local obstype=$1
  local rundate=$2
  local oyyyy=`echo $rundate | cut -c 1-4`
  local omm=`echo $rundate | cut -c 5-6`
  local odd=`echo $rundate | cut -c 7-8`
  local ohh=`echo $rundate | cut -c 9-10`



  if [[ $obstype == radar ]] ; then
    GetRadar
  elif [[ $obstype == modes ]] ; then
    GetModes
  else
    local ofile=${obstype}_${rundate}00.bufr
    local opath=$SCRATCH/OBS/$oyyyy/$omm/$odd
    if [[ ! -e $opath/$ofile ]] ; then
      [[ -d $opath ]] || mkdir -p $opath
      case $obstype in
        synop|amdar)
          rmiopath="/mnt/HDS_ALADIN/ALADIN//OBSERVATIONS/bufr/${oyyyy}/${omm}/${odd}" ;;
        temp)
          rmiopath="/mnt/HDS_ALD_TEAM/ALD_TEAM/idehmous/DASK/bufr/TEMP"  ;;
        gpssol)
          rmiopath="/mnt/HDS_ALD_TEAM/ALD_TEAM/idehmous/DASK/bufr/GPS"   ;;
        *)
          echo "unknown obstype"
          exit 1 ;;
      esac

      module load ecaccess
      ectrans -gateway nogrod.oma.be -remote ad_oper@@genericSftp -get \
        -source ${rmiopath}/${ofile}   \
        -target $opath/$ofile
    fi
  # retrieve local files (real time) from ATOS
  # cp /ec/vol/msbackup/BUFR0001${oyyyy}${omm}${odd}${ohh}.DAT $ofile
  # TODO: reduce file size with bufr_filter (keep only synop)
    cp $opath/$ofile .
  fi

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

#################


