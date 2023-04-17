#! /bin/dev python
# architecture: ecmwf_cca
import os

class platform :
  def __init__ (self) : 
    self.name = "ecmwf_cca"
    self.node_size = 36
    self.header = "pbs.h"
    suite_path = os.getcwd()
    schd = suite_path + "/bin/schedule_cca"
    self.ecf_cmd = {
      "ECF_JOB_CMD":schd+" @SUBMIT_OPT:@ @USER@ @HOST@ @ECF_JOB@ @ECF_JOBOUT@ submit",
      "ECF_KILL_CMD":schd+" @USER@ @HOST@ @ECF_RID@ kill",
      "ECF_STAT_CMD":schd+" @USER@ @HOST@ @ECF_RID@ status"
    }


  def define_topology(self, n_cores) :
    template = "-l EC_threads_per_task=1 -l EC_hyperthreads=1 -l EC_total_tasks={0}"
    return template.format(str(n_cores))

  def define_queue(self, n_cores) :
    if n_cores == 1 :
      # FIXME: same tasks are single core but still need MPI bindings!
      #   So we set queue=nf always...
      queue = "nf"
    elif n_cores <= self.node_size/2 :
      queue = "nf"
    else :
      queue = "np"
    return queue
