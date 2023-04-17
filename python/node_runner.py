#! /usr/bin/env python3
"""
## Node Runner
## Authors: Alex Deckmyn & Idir Dehmous
## TODO:
## ... a lot :-)
"""
from ecflow import * 
import os
import sys
import importlib
import configparser
from nr_modules.suite_config import nr_suite_config

# get init file from command line
# > python node_runner.py oper.ini
nargv = len(sys.argv)
if nargv > 1 :
  ini_file = sys.argv[1]
  if not os.path.exists(ini_file) :
    print("File " + ini_file + " not found.")
    exit(1)
else :
  print("You need to provide a <suite>.ini file!\n")
  print("Usage:")
  print("> python node_runner.py <suite>.ini\n")
  exit(1)


# NOTE: suite_name MUST be equal to the path
#       so you can take "pwd" as suite_path
#       THIS ONLY WORKS IF YOU RUN NODERUNNER FROM THE BASE DIRECTORY!
suite_path = os.getcwd()
suite_name = os.path.basename(suite_path)

print("\n" +
      "NodeRunner               : creating suite "+suite_name+"\n"+
      "definition file location : "+suite_path+"/"+suite_name+".def\n"+
      "ini file used            : "+ini_file+"\n")

###############

# ATTENTION: "configparser" reads unicode by default
#   so this can be problematic with python2 (a lot of str() needed!)
#   but using python2 ConfigParser is less flexible
#   we prefer to use the back-ported configparser from py3
#   When using ConfigParser (py2): no indentation allowed

config=configparser.ConfigParser()
# keep key names in upper case
config.optionxform = str
config.read(ini_file)

####################
# read config file #
####################

suite_config = nr_suite_config(suite_path, config)

##############################
# start the suite definition #
##############################

defs = Defs()
suite = defs.add_suite(suite_name) # we just call the variable "suite"...

#######################
### Suite variables ###
#######################

# main
variables = { 
  "PLATFORM":suite_config.platform.name,
  "HPC_HEADER":suite_config.platform.header,
  "ECF_MICRO":"@",
  "MODE":suite_config.mode,
  "CYCLE_INC":str(suite_config.cycle_inc),

  }
suite.add(Edit(variables))

# JOB SUBMISSION etc. #
# defined in modules/arch/<platform>.py
suite.add(Edit(suite_config.platform.ecf_cmd))

# check HPC_USER, ECF_LOGPORT entries in "settings"
if "HPC_USER" not in config.options("settings") :
  print("Setting HPC_USER=" + suite_config.user_hpc)
  config["settings"]["HPC_USER"] = suite_config.user_hpc
#if "ECF_LOGPORT" not in config.items("settings") :
#  config["settings"]["ECF_LOGPORT"] = "3" + str(userid)

### variables for PBS/user/ecFlow/hpc...
### we should try to fix HPC_USER by "interpolation" in the config file...
directories = {
  "ECF_USER":suite_config.username,
  "ECF_INCLUDE":suite_path + "/include",
  "ECF_FILES":suite_path + "/scr",
  "ECF_HOME":suite_config.local_temp,
  "ECF_BINDIR":suite_config.local_bin,
  "SUITE_DATA":suite_path + "/data"     # this is used for sync'ing them to HPC
  }
suite.add(Edit(directories))

# the default "USER"@"HOST" is the HPC account
suite.add_variable(suite_config.jobs["hpcjob"])
suite.add_variable(suite_config.tasktypes["serial"])

# .ini sections that are directly converted to ecflow variables:
section_list = ["model", "settings", "local", "coupling"]
for section in section_list :
  # TODO: check all entries? default values?
  if section in config.sections() :
    x = config.items(section)
    xd = { str(y[0]):str(y[1]) for y in x }
    suite.add_variable(xd)
# FIXME: such limits should be defined somewhere else (platform?)
suite.add_limit("max_postproc", 18)
# never allow two main "init sync" tasks at the same time!
suite.add_limit("max_init", 1)
# never allow two main "sync scratch" tasks at the same time!
suite.add_limit("max_sync", 1)

# add various HPC "node selection" templates
suite.add(Edit(suite_config.select))
# add various walltime estimates
suite.add(Edit(suite_config.walltime))
# assimilation settings:
suite.add(Edit(suite_config.assim_var))

########################
# BUILD THE FULL SUITE #
########################

suite_def = importlib.import_module("nr_modules.suite.nr_suite_" + suite_config.suite_type)
suite_def.build_suite(suite, suite_config, config)

######################################
# operational use: external triggers #
######################################
# "True" means: remove existing extern definitions first, then scan the suite
defs.auto_add_externs(True)

#######################
### write .def file ###
#######################

defs.save_as_defs(suite.name()+".def")

