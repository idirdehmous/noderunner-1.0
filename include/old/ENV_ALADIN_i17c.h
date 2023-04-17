# make output accessible to others
umask 0022
# Memory settings
ulimit -s unlimited
ulimit -c unlimited

# Load modules
. ${MODULESHOME}/init/bash
module purge
module use /home/ald_team/modules
module load aladin/2018b

NPROC=`wc -l < ${PBS_NODEFILE}`
export MPIRUN="mpiexec_mpt -np $NPROC"
export MPIRUN1="mpiexec_mpt -np 1"

# settings from SGI benchmark report
export KMP_AFFINITY=disabled
export KMP_STACKSIZE=1g

# Drhook settings
export DR_HOOK=0 # 1 to turn drhook profiling on
export DR_HOOK_IGNORE_SIGNALS=-1
##export DR_HOOK_SILENT=1
export DR_HOOK_OPT=prof
export decfort_dump_flag=Y

# Avoid XPMEM
export MPI_MEMMAP_OFF=true
export MPI_XPMEM_ENABLED=false

#
export MP_SHARED_MEMORY=no
export DR_HOOK_NOT_MPI=""

# HPC TOPOLOGY
# depends on number of nodes
case $NPROC in
 768) NPRGPNS=32 ; NPRTRV=6 ;; # 32 nodes
 672) NPRGPNS=28 ; NPRTRV=6 ;; # 28 nodes
 624) NPRGPNS=26 ; NPRTRV=6 ;; # 26 nodes
 576) NPRGPNS=24 ; NPRTRV=3 ;; # 24 nodes
 384) NPRGPNS=24 ; NPRTRV=2 ;; # 16 nodes
 192) NPRGPNS=16 ; NPRTRV=3 ;; # 8 nodes
  96) NPRGPNS=12 ; NPRTRV=1 ;; # 4 nodes
  48) NPRGPNS=8  ; NPRTRV=1 ;; # 2 nodes
  24) NPRGPNS=6  ; NPRTRV=1 ;; # 1 node
  12) NPRGPNS=4  ; NPRTRV=1 ;; # 1/2 node
   1) NPRGPNS=1  ; NPRTRV=1 ;; # single core
 720) NPRGPNS=30 ; NPRTRV=6 ;; # cca 20
  36) NPRGPNS=6  ; NPRTRV=1 ;; # cca 1 node
  18) NPRGPNS=6  ; NPRTRV=1 ;; # cca 1/2 node
   *) NPRGPNS=$NPROC ; NPRTRV=1 ;; # generic
esac
NPRGPEW=$(( NPROC / NPRGPNS ))
NPRTRW=$(( NPROC / NPRTRV ))
TOPOLOGY="NPROC=$NPROC,NPRGPNS=$NPRGPNS,NPRGPEW=$NPRGPEW,NPRTRW=$NPRTRW,NPRTRV=$NPRTRV"

# ODB BUFR tables (for bator)
export BUFR_TABLES=/home/ald_team/software/auxlibs/3.1_i17c/lib/bufrtables.383MF/mf_bufrtables/

