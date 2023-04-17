#!/bin/bash
#PBS -S /bin/bash
#PBS -l walltime=@WALLTIME:00:05:00@
#PBS @NODE_SELECT@
#PBS -q @QUEUE@
#PBS -j oe
#PBS -W umask=022
#PBS -N @TASK@.@ECF_TRYNO@
##PBS -m a @MAIL_LIST:@
