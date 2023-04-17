#!/bin/bash
#set -x # echo script lines as they are executed
set +x
set -e # stop the shell on first error
set -u # fail when using an undefined variable
set -o pipefail

TASK_START_TIME=`date -u +"%Y-%m-%d %H:%M:%S"`
echo "#################################"
echo "### START : $TASK_START_TIME"
echo "#################################"

# Defines the variables that are needed for any communication with ecFlow
export ECF_PORT=@ECF_PORT@    # The server port number
export ECF_HOST=@ECF_HOST@    # The name of ecf host that issued this task
export ECF_NAME=@ECF_NAME@    # The name of this current task
export ECF_PASS=@ECF_PASS@    # A unique password
export ECF_TRYNO=@ECF_TRYNO@  # Current try number of the task

# record the process id. Also used for zombie detection
# it must be a simple number, so strip the rest! 
if [ ${PBS_JOBID:-""} ] ; then 
  # this is a PBS job
  export ECF_RID=$PBS_JOBID
#  export ECF_RID=`echo $PBS_JOBID | cut -d "." -f 1`
elif [ ${SLURM_JOB_ID:-""} ] ; then
  export ECF_RID=${SLURM_JOB_ID}
else
  # just get process id
  export ECF_RID=$$
fi


#host=`echo ${HOSTNAME,,} | cut -f1 -d'.' `
host=`hostname | tr '[:upper:]' '[:lower:]'`
module load ecflow/@ECF_VERSION@ || echo "no ecflow module found"

# Tell ecFlow we have started and pass the right job_id
ecflow_client --init=${ECF_RID}

# Define an error handler
# NOTE: ECMWF advises NOT to trap 15 (SIGTERM) on atos !
#       On PBS systems, "qdel" actually uses 15 (followed by 9)
#       So on such systems, 15 must be trapped as well.
#       On atos, troika sends 2 (SIGINT) followed by 9 (SIGKILL)

SIGNAL_LIST="1 2 3 4 5 6 7 8 10 11 13 24 $(seq 31 1 64)"

function ERROR {
   set -x
   set +e              # Clear -e flag, so we don't fail
   # Notify ecFlow that something went wrong
   errmsg="$2"
   if [ $1 -eq 0 ] ; then
     errmsg="CANCELLED or TIMED OUT $errmsg"
   fi
   ecflow_client --abort="$errmsg"
   trap - 0 $SIGNAL_LIST                     # Remove the trap
   if [[ @MAIL_LIST:""@ ]] ; then 
     mlist=$(echo @MAIL_LIST:""@ | tr "," " ")
     for mmail in $mlist ; do
       echo "Mailing $mmail"
       echo "Error in suite @SUITE@ : task @ECF_NAME@" \
         | mailx -s "@SUITE@ : Node Runner aborted" $mmail

     done
     echo "All mails are sent. Now I can die in peace."
   fi
   wait                        # wait for background process to stop
#   echo "ENVIRONMENT:"
#   printenv | sort
# End the script
  if [ $1 -eq 0 ] ; then
     exit -1
  else
     exit $1
  fi
}
 
# Trap any signal that may cause the script to fail
# NOTE: "qdel" sends SIGTERM (15) followed by SIGKILL (9) (also on HPC?)
#       you can not trap SIGKILL
#       so for ecflow communication, the delay between 15 & 9 must be enough
# NOTE 2022-12-08 : ECMWF advise NOT to trap 15 (SIGTERM) on atos !

for sig in $SIGNAL_LIST ; do
  trap "ERROR $sig \"Signal $(kill -l $sig) ($sig) received\"" $sig
done

# Trap any calls to exit and errors caught by the -e flag
trap "ERROR \$? \"Exit code \$?\"" 0

#set -x

