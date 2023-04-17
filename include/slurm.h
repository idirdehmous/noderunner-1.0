#!/bin/bash 
#SBATCH --time=@WALLTIME:00:05:00@
#SBATCH @NODE_SELECT@
#SBATCH --job-name=@TASK@.@ECF_TRYNO@
##SBATCH --qos=@QUEUE:nf@
##SBATCH --mail-type=FAIL
##SBATCH --mail-user=@MAIL_LIST:@
##SBATCH --output=
##SBATCH --nodes=
##SBATCH --ntasks=
##SBATCH --account=bedb
# for sf jobs, the default is 8GB total
# which is often too small:
##SBATCH --mem-per-cpu=1G
