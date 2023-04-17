from ecflow import *
import os
#import pwd
import configparser
import datetime
import importlib

def estimate_walltime(fclen, ncores, factor) :
  # in minutes: fclen (in h) * factor / #ncores
  # this is just a rough estimate based on "perfect scaling"
  # transform to "hh:mm:ss" string
  # add 10' for DFI etc.
  return str(datetime.timedelta(minutes=fclen * factor / ncores + 10))


# ATTENTION: "configparser" reads unicode by default
#   so this can be problematic with python2 (a lot of str() needed!)
#   but using python2 ConfigParser is less flexible
#   we prefer to use the back-ported configparser from py3
#   When using ConfigParser (py2): no indentation allowed

class nr_suite_config :
  def __init__(self, suite_path, config):
    self.name = os.path.basename(suite_path)
    self.suite_path = suite_path
    self.config = config
    self.local_temp = suite_path + "/tmp"
    self.local_bin  = suite_path + "/bin"
    self.userid = os.getuid()
    self.username = os.environ["LOGNAME"]
#    self.username = os.getlogin()   # fails on e.g. ecgate
#    self.username = pwd.getpwuid(self.userid)[0]

    # PLATFORM
    # NOTE: the module path is only OK when running from the root directory.
    pname = str(config.get("platform", "platform"))
    arch = importlib.import_module("nr_modules.arch." + pname)
    self.platform  =  arch.platform()
    if hasattr(self.platform, "localhost") :
      self.localhost = self.platform.localhost
    else :
      self.localhost = "localhost"

    # SUITE
    self.mode = str(config.get("suite", "suite_mode", fallback="exp")).strip()
    self.delay_mode = config.getboolean("suite", "delay_mode", fallback = False)
    self.suite_type = config.get("suite", "suite_type", fallback="forecast_cycle")

    self.host_hpc = str(config.get("settings", "HPC_HOST")).strip()
    self.user_hpc = str(config.get("settings", "HPC_USER", fallback=self.username)).strip()
    self.scratch = str(config.get("settings", "SCRATCH")).strip()
# "mode" can be: "oper" or "exp" for forecast cycles, "bmat" for B-matrix
    if self.suite_type in [ "forecast_cycle" ] :
      self.realtime = config.getboolean("suite", "realtime", fallback="no")
      self.enddate = str(config.get("suite", "enddate", fallback="3000010100"))
      self.has_postproc = ("postproc" in config.sections()) and (len(config.items("postproc")) > 0)
      self.has_products = ("products" in config.sections()) and (len(config.items("products")) > 0)
      self.trigger = str(config.get("suite", "trigger", fallback=""))
      self.has_trigger = self.trigger != ""
      self.has_clock = self.realtime and config.get("cycle", "trigger_time") != ""
      self.has_assimilation = config.getboolean("assimilation", "assimilation")
      self.cycle_inc = config.getint("cycle", "cycle_inc")
      self.forecast_length = config.getint("cycle", "forecast_length")
      if self.forecast_length < self.cycle_inc :
        print("ERROR: forecast length shorter than assimilation cycle!")
      # which cycles are actually doing a forecast (not only DA)
      if self.cycle_inc > 0 :
        self.ncycle = 24 // self.cycle_inc
        self.runlist = list(map(int,map(str.strip, str(config.get("cycle", "runcycles")).split(","))))
      # try to make sure that trigger_labels has the correct length (ncyles)
        self.trigger_labels = list(map(str.strip, str(config.get("cycle", "trigger_labels", fallback=(self.ncycle-1)*"," )).split(",")))
        ## in python3, map() no longer returns a list. Usually OK, but not if you want to use an index
        self.cycle_labels = list(map(str.strip, str(config.get("cycle", "cycle_labels")).split(",")))
        if self.realtime :
          self.cycle_times = list(map(str.strip, str(config.get("cycle", "trigger_time")).split(",")))
    elif self.suite_type in [ 'bmatrix' ] :
      self.cycle_inc = config.getint("cycle", "cycle_inc")
      self.has_assimilation = True

# coupling
    self.lbc_inc = config.getint("coupling", "LBC_INC")
    model_domain = config.get("model", "DOMAIN")
    self.coupling_strategy = config.get("coupling", "COUPLING", fallback = "unknown")
    coupling_domain = config.get("coupling", "COUPLING_DOMAIN", fallback = model_domain)
    self.has_e927 = coupling_domain != model_domain

# model
    self.has_surfex = config.get("model", "SURFACE") == "surfex"
    # NOTE : we use "eval" so we can write the #of cores as <#nodes>*<node_size>
    # FIXME: some suites don't have "post-processing".
    #        and maybe also no pre-processing (if LBC's are ready)
    #        ? should ncores_xxx be in a separate config file?
# PLATFORM
#    self.ncores_forecast = eval(config.get("platform", "ncores_forecast", fallback="0"))
#    self.ncores_pre = eval(config.get("platform", "ncores_pre", fallback="1"))
#    self.ncores_pos = eval(config.get("platform", "ncores_pos", fallback="1"))
    self.walltime_serial = str(datetime.timedelta(minutes=eval(config.get("platform", "walltime_serial", fallback="30"))))
    self.walltime_forecast = str(datetime.timedelta(minutes=eval(config.get("platform", "walltime_fc", fallback="30"))))
    self.walltime_ret = str(datetime.timedelta(minutes=eval(config.get("platform", "walltime_ret", fallback="50"))))
    self.walltime_pre = str(datetime.timedelta(minutes=eval(config.get("platform", "walltime_pre", fallback="10"))))
    self.walltime_pos = str(datetime.timedelta(minutes=eval(config.get("platform", "walltime_pos", fallback="5"))))

    self.tasktypes = {
        "serial":{"NODE_SELECT":"@SELECT_SERIAL@", "WALLTIME":"@WALLTIME_SERIAL@"},
        "forecast":{"NODE_SELECT":"@SELECT_FC@", "WALLTIME":"@WALLTIME_FC@"},
        "ret":{"NODE_SELECT":"@SELECT_RET@", "WALLTIME":"@WALLTIME_RET@"},
        "pre":{"NODE_SELECT":"@SELECT_PRE@", "WALLTIME":"@WALLTIME_PRE@"},
        "pos":{"NODE_SELECT":"@SELECT_POS@", "WALLTIME":"@WALLTIME_POS@"}
      }
    # allow for overriding defaults
    # TROIKA DOESN T ALLOW HEADER SPERATED WITH MORE THAN ONE SPACE
    self.select = {}
    self.select["SELECT_SERIAL"]   = " ".join(config.get("platform", "SELECT_SERIAL").split() )
    self.select["SELECT_RET"]      = " ".join(config.get("platform", "SELECT_RET" , fallback="@SELECT_SERIAL@").split() )
    self.select["SELECT_PRE"]      = " ".join(config.get("platform", "SELECT_PRE" , fallback="@SELECT_SERIAL@").split() )
    self.select["SELECT_POS"]      = " ".join(config.get("platform", "SELECT_POS" , fallback="@SELECT_SERIAL@").split() )
    self.select["SELECT_FC"]       = " ".join(config.get("platform", "SELECT_FC"  , fallback="@SELECT_SERIAL@").split() )

    # FIXME: this should take account over overrides defined above
#    self.tasktypes["serial"]["QUEUE"]   = self.platform.define_queue(1)
#    self.tasktypes["pre"]["QUEUE"]      = self.platform.define_queue(self.ncores_pre)
#    self.tasktypes["pos"]["QUEUE"]      = self.platform.define_queue(self.ncores_pos)
#    self.tasktypes["forecast"]["QUEUE"] = self.platform.define_queue(self.ncores_forecast) 
    self.walltime = {
        "WALLTIME_SERIAL" :self.walltime_serial,
        "WALLTIME_FC"     :self.walltime_forecast,
        "WALLTIME_RET"    :self.walltime_ret , 
        "WALLTIME_PRE"    :self.walltime_pre,
        "WALLTIME_POS"    :self.walltime_pos
        }




    # these variables need fixing for *all* local (non-hpc) jobs
    self.jobs = { "localjob":{ "HOST":self.localhost, "USER":self.username, "ECF_OUT":self.local_temp, "LOCALJOB":"yes"},
    #self.jobs = { "localjob":{ "HOST":"localhost", "USER":self.username, "ECF_OUT":self.local_temp,
    #                           "ECF_JOB_CMD":"@ECF_JOB@ 1>@ECF_JOBOUT@ 2>&1 &"},
    #              "hpcjob":{ "HOST":"@HPC_HOST@", "USER":"@HPC_USER@", "ECF_OUT":"@HPC_LOGPATH@"}
    "hpcjob":{ "HOST":"@HPC_HOST@", "USER":"@HPC_USER@", "ECF_OUT":"@HPC_LOGPATH@", "LOCALJOB":"no"}
                  }

    #########################
    # ASSIMILATION SETTINGS #
    #########################

    if not self.has_assimilation :
      self.assim_var = { "ASSIMILATION":"no" }
    else :
    # TODO: more robustness, fallback values... it's still a bit of a mess
      self.assim_upper   = config.get("assimilation"  , "assim_upper")
      self.assim_surface = config.get("assimilation", "assim_surface")
      self.obs_npool     = config.getint("assimilation" , "obs_npool")
      self.obstypes_surface = list(map(str.strip, str(config.get("assimilation", "obstypes_surface")).split(",")))
      self.obs_source    = config.get("assimilation", "obs_source" )
      self.obs_path      = config.get("assimilation", "obs_path" )
     
       
      self.odb_arch = config.getboolean("assimilation", "odb_arch", fallback=False)
      self.odb_path = config.get("assimilation", "odb_path", fallback=False)

      self.fg_max = config.getint("assimilation", "fg_max", fallback=self.cycle_inc)
      # FIXME: bmatrix suite shouldn't have COLDSTART defined (but no harm...)
      self.coldstart = config.get("assimilation", "coldstart", fallback="1234567890")
      self.assim_var = {
        "ASSIMILATION":"yes",
        "ASSIM_UPPER":str(self.assim_upper),
        "ASSIM_SURFACE":str(self.assim_surface),
        "OBS_NPOOL":str(self.obs_npool),
        "COLDSTART":str(self.coldstart),
        "OBSTYPES_SURFACE":" ".join(self.obstypes_surface),
        "OBS_SOURCE":str(self.obs_source) , 
        "OBS_PATH"  :str(self.obs_path )  , 
        "ODB_ARCH"  :str(self.odb_arch )  , 
        "ODB_PATH"  :str(self.odb_path)   , 
        "FG_MAX":str(self.fg_max),
        }
      if self.assim_upper == "3dvar" :
        self.obstypes_upper   = list(map(str.strip, str(config.get("assimilation", "obstypes_upper")).split(",")))
        self.assim_var["OBSTYPES_UPPER"] = " ".join(self.obstypes_upper)
      # we may want to add robustness by storing a "pre-first guess" for later cycles
      # TODO: "addfields" as "pos"?
      self.tasktypes.update({
          "bator":{"NODE_SELECT":"@SELECT_CANARI@"},
          "canari":{"NODE_SELECT":"@SELECT_CANARI@"},
          "minim":{"NODE_SELECT":"@SELECT_MINIM@", "WALLTIME":"@WALLTIME_MINIM@"},
          "screening":{"NODE_SELECT":"@SELECT_SCREENING@", "WALLTIME":"@WALLTIME_MINIM@"},
          "addfields":{"NODE_SELECT":"@SELECT_POS@", "WALLTIME":"@WALLTIME_POS@"}
          })
      # NOTE: we use "eval", so the fallback value must also be a string!
#      ncores_fc_short = eval(config.get("platform", "ncores_fc_short", fallback=str(self.ncores_forecast)))
#      ncores_minim = eval(config.get("platform", "ncores_minim", fallback=str(self.ncores_forecast)))
      # FIXME: do canari and screening ALWAYS have to be == npool?
#      ncores_canari = config.getint("assimilation", "obs_npool")
#      ncores_screening = eval(config.get("platform", "ncores_screening", fallback=str(ncores_canari)))
      self.select["SELECT_BATOR"]   = config.get("platform", "SELECT_BATOR", fallback=self.platform.define_topology(1))
      self.select["SELECT_CANARI"]   = config.get("platform", "SELECT_CANARI", fallback=self.platform.define_topology(4))
      self.select["SELECT_MINIM"]    = config.get("platform", "SELECT_MINIM", fallback=self.platform.define_topology(12))
      self.select["SELECT_SCREENING"]= config.get("platform", "SELECT_SCREENING", fallback=self.platform.define_topology(12))

#      self.tasktypes["canari"]["QUEUE"] = self.platform.define_queue(ncores_canari)
#      self.tasktypes["minim"]["QUEUE"] = self.platform.define_queue(ncores_minim)
#      self.tasktypes["screening"]["QUEUE"] = self.platform.define_queue(ncores_screening)\
      # TODO: better fallback values?
      walltime_cana  = str(datetime.timedelta(minutes=eval(config.get("platform", "walltime_can", fallback="15"))))
      walltime_minim = str(datetime.timedelta(minutes=eval(config.get("platform", "walltime_minim", fallback="15"))))
      self.walltime.update({
        "WALLTIME_BATOR":walltime_cana , 
        "WALLTIME_CANA": walltime_cana ,   
        "WALLTIME_MINIM":walltime_minim
        })



  def has_wait(self, i):
    w_time = ( self.realtime and self.cycle_times[i] != "" )
    w_trigger = self.has_trigger and self.trigger_labels[i] != ""
    return (w_trigger or w_time)

  def cycle_trigger(self, i):
    if self.trigger_labels[i] == "" :
      return ""
    else :
      return self.cycle_trigger.replace("cycle", self.cycle_labels[i])

  def this_run(self, i):
    return self.cycle_labels[ i ]

  def next_run(self, i):
    return self.cycle_labels[ (i + 1) % self.ncycle]

  def prev_run(self, i):
    return self.cycle_labels[ (i - 1) % self.ncycle]

  def is_runcycle(self, i):
    return (i == -1 or i * self.cycle_inc in self.runlist )

  def is_maincycle(self, i):
    return (i * self.cycle_inc in [0,6,12,18] )

  def fclen(self, i):
    if i == -1 or i * self.cycle_inc in self.runlist :
      return self.forecast_length
    else :
      return self.cycle_inc

  def read_section(self, section, err=False):
    if section in self.config.sections() :
      return { str(y[0]):str(y[1]) for y in self.config.items(section) }
    elif err :
      raise Exception("Section " + section + " not found in config file.")
    else :
      return None

