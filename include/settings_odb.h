
# OpenMP tuning
export OMP_NUM_THREADS=1
export MP_SINGLE_THREAD="yes"
export OMP_DYNAMIC="false"
export OMP_STACKSIZE='1G'
export DR_HOOK=-1
export DR_HOOK_IGNORE_SIGNALS=-1
#export NPROC=1
export KMP_AFFINITY=disabled
export KMP_STACKSIZE=1g
export MPI_MEMMAP_OFF=true
export MPI_XPMEM_ENABLED=false
export MP_SHARED_MEMORY=no
export DR_HOOK_NOT_MPI=""
export MPI_XPMEM_ENABLED=disabled
export MPI_SHEPHERD=true

# SETTINGS FOR ODB 
#---------------------------------
export EC_PROFILE_HEAP=0
export TO_ODB_ECMWF=0
export TO_ODB_SWAPOUT=0
export ODB_DEBUG=0
export ODB_CTX_DEBUG=0
export ODB_REPRODUCIBLE_SEQNO=2
export ODB_STATIC_LINKING=1
export ODB_IO_METHOD=1
export ODB_ANALYSIS_DATE=${YYYY}${MM}${DD}
export ODB_ANALYSIS_TIME=${RR}0000
export TIME_INIT_YYYYMMDD=${YYYY}${MM}${DD}
export TIME_INIT_HHMMSS=${RR}0000


export MERGE_IOASSIGN=${BASEDIR}/etc/ioassign/merge_ioassign.43t2
export CREATE_IOASSIGN=${BASEDIR}/etc/ioassign/create_ioassign.43t2

