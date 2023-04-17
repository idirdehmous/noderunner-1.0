#####################
# namelist settings #
#####################

# namelist subdirectory
NAMELIST_VERSION=@NAMELIST_VERSION:default@

#CPLFREQ=$(( 10#$LBC_INC * 3600 ))
#TSRANGE=$(( (10#$HOURRANGE * 3600) / TIMESTEP ))
#LEVELS=$(seq -s"," 1 1 $NLEVELS)

namelist_tag="@NAMELIST_TAG:cy43@"
if [[ $MODEL = 'arome' ]] ; then
  namelist_flags="arom_nhsx"
elif [[ $MODEL = 'alaro' ]] ; then
  if [[ $SURFACE = "surfex" ]] ; then
    surf_flag="sx"
  else 
    surf_flag="is"
  fi
  if [[ $HYDROSTATIC = "yes" ]] ; then
    hydr_flag="hs"
  else 
    hydr_flag="nh"
  fi
  namelist_flags=alro_${hydr_flag}${surf_flag}
fi

# default namelists: [NOTE: we assume that inline fullpos is in main namelist]
NAMELIST_FC="@NAMELIST_FC:${namelist_flags}_fcst_${namelist_tag}.nam@"
NAMELIST_PRE="@NAMELIST_PRE:${namelist_flags}_prep_${namelist_tag}.nam ${DOMAIN}.${NLEVELS}@"
NAMELIST_POS="@NAMELIST_POS:${namelist_flags}_post_${namelist_tag}.nam@" # some parts to be added in task
NAMELIST_CANARI="@NAMELIST_CANARI:${namelist_flags}_cana_${namelist_tag}.nam@"

#NAMELIST_BLEND="@NAMELIST_BLEND:${namelist_flags}_isba_${namelist_tag}.nam@"
#NAMELIST_BATOR="@NAMELIST_BATOR:namel_bator@"
#NAMELIST_LAMFLAG="@NAMELIST_LAMFLAG:namel_lamflag_$DOMAIN@"

NAMELIST_MINIM="@NAMELIST_MINIM:${namelist_flags}_mini_${namelist_tag}.nam@"
NAMELIST_SCREENING="@NAMELIST_SCREENING:${namelist_flags}_scre_${namelist_tag}.nam@"
NAMELIST_SCREENING_ADDSURF="@NAMELIST_SCREENING_ADDSURF:${namelist_flags}_scre_addsurf@"

if [[ $SURFACE == surfex ]] ; then
  NAMELIST_FC_SFX="@NAMELIST_FC_SFX:EXSEG1_e001_$MODEL@"
  NAMELIST_CANARI_SFX="@NAMELIST_CANARI_SFX:EXSEG1_canari_${MODEL}@"
# for cold start or surfex in downscaling mode: run prep "prep" inline in fullpos
  NAMELIST_PREP_SFX="@NAMELIST_PREP_SFX:${namelist_flags}_psfx_${namelist_tag}.nam ${DOMAIN}.$NLEVELS@"
fi

