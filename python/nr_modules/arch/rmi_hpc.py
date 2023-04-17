#! /bin/dev python
# architecture: rmi_hpc
import os

class platform :
  def __init__ (self) : 
    self.name = "rmi_hpc"
    self.node_size = 24
    self.header = "pbs.h"
    # the job submission script is inside the suite
    suite_path = os.getcwd()
    schd = suite_path + "/bin/schedule_rmi"
    self.ecf_cmd = {
      "ECF_JOB_CMD":schd+" @SUBMIT_OPT:@ @USER@ @HOST@ @ECF_JOB@ @ECF_JOBOUT@ submit",
      "ECF_KILL_CMD":schd+" @USER@ @HOST@ @ECF_RID@ kill",
      "ECF_STAT_CMD":schd+" @USER@ @HOST@ @ECF_RID@ status"
    }

  def define_topology(self, n_cores) :
  # {0} -> number of nodes (or 1 for serial and partial nodes)
  # {1} -> cores per node (or total cores on partial node)
    template = "-l select={0}:ncpus={1}:mpiprocs={1}:ompthreads=1"
    # FIXME: you may want a smaller number of cores per node (e.g. for memory)
    if n_cores == 1 :
      template += " -l place=shared"
      n_blocks = 1
      block_size = 1
    elif n_cores >= self.node_size :
    # NOTE: we assume n_cores is a multiple of node_size!
      n_blocks = n_cores / self.node_size
      block_size = self.node_size
    else :
      n_blocks = 1
      block_size = n_cores
    return template.format(str(n_blocks), str(block_size))

  def define_queue(self, n_cores) :
    # FIXME: at RMI, this depends on walltime...
    return "short"
