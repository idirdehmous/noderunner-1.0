#! /bin/dev python
# architecture: ecmwf_atos

class platform :
  localhost="hpc" # even "ecflow server" tasks should be run there
  def __init__ (self) : 
    self.name = "ecmwf_atos"
    self.node_size = 128
    self.header = "slurm.h"
    schd = "troika"
    self.ecf_cmd = {
      "ECF_JOB_CMD":schd+" submit -o @ECF_JOBOUT@ @HOST@ @ECF_JOB@ ",
      "ECF_KILL_CMD":schd+" kill @HOST@ @ECF_JOB@",
      "ECF_STAT_CMD":schd+" monitor @HOST@ @ECF_JOB@"
    }



  def define_topology(self, n_cores) :
    template = "--ntasks={0} --cpus-per-task=1 --threads-per-core=1"
    # small (nf) jobs get 8GB by default
    # but that may be too little for e.g. e927
    if n_cores > 8 and n_cores < 128 :
      template += " --mem-per-cpu=1G"
    return template.format(str(n_cores))

  def define_queue(self, n_cores) :
    if n_cores <= self.node_size/2 :
      queue = "nf"
    else :
      queue = "np"
    return queue

