from ecflow import *
import datetime
import os

# do all bator runs in parallel or sequentially in 1 script...
#class nr_getobs(Family):
#  def __init__(self, suite_config, obslist):
#    Family.__init__(self, "getobs")
#    for obstype in obslist:
#      self += Task(obstype).add(Edit(OBSTYPE=obstype)) # script= , 
#    self += Task("odbmerge").add(Trigger=....

class nr_assim_sfc(Family):
  def __init__(self, suite_config):
    Family.__init__(self, "surface")
    self.add(Edit(OBSTYPES="@OBSTYPES_SURFACE@", ASSIM_LABEL="surface"))
    self.add(
      Task("get_obs", Edit(ECF_FILES = suite_config.suite_path + "/scr/assimilation")),
      Task("bator").add(
        Edit(ECF_FILES = suite_config.suite_path + "/scr/assimilation", NODE_SELECT="@SELECT_BATOR@", WALLTIME="@WALLTIME_BATOR@"),
        Trigger("./get_obs == complete")),
      Task("odb_merge").add(
        Edit(ECF_FILES = suite_config.suite_path + "/scr/assimilation"),
        Trigger("./bator == complete"))
      )
    da_trigger = "(../../lbc == complete or ../../lbc:LAUNCH_00 == set)"
    if suite_config.has_surfex :
      self.add(
        Task("addfields",
            Trigger(da_trigger),
            Edit(ECF_FILES = suite_config.suite_path + "/scr/assimilation"),
            Edit(suite_config.tasktypes["addfields"])),
# We moved this step to save_first_guess
# then we don't have to access previous _canari analysis anymore
#          Task("cpl_Ts", Trigger("addfields == complete")),
        Task("sst_update", Trigger("addfields == complete")),
        Task("canari").add(
          Trigger("./odb_merge == complete && sst_update == complete"),
          Edit(suite_config.tasktypes["canari"]))
      )
    else : # ISBA scheme
      # FIXME : add ISBA fields, SST update...
      self.add(
#        Task("addfields", Trigger("../check_first_guess == complete"),
#          Edit(ECF_FILES = suite_config.suite_path + "/scr/assimilation")),
#        Task("sst_update", Trigger(da_trigger + " && addfields == complete")),
        Task("sst_update", Trigger(da_trigger )),
        Task("canari").add(
          Trigger("./odb_merge == complete and ./sst_update == complete"),
          Edit(suite_config.tasktypes["canari"]))
        )

class nr_assim_upper(Family):
  def __init__(self, suite_config):
    Family.__init__(self, "upper_air")
    # TODO: you could have separate parallel tasks for every obs type!
    #       followed by a single "merge" task
    if ( suite_config.assim_upper == "blend") :
      self.add( Task("blend"))
    elif (suite_config.assim_upper == "none") :
      if (suite_config.has_surfex) :
        self.add( Task("get_fg"))
      else :
        self.add(Task("copy_soil",
                      Edit(suite_config.tasktypes["addfields"])
                     )
                )
    elif (suite_config.assim_upper == "3dvar") :
      self.add(Edit(OBSTYPES="@OBSTYPES_UPPER@", ASSIM_LABEL="upper"))
      self.add(
        Task("get_obs", Edit(ECF_FILES = suite_config.suite_path + "/scr/assimilation") ))
        # TODO: have parallel tasks for every obs type, or sequential?
        #       if sequential, we can do the "merge" in the same script
#        Task("bator").add(
#          Edit(ECF_FILES = suite_config.suite_path + "/scr/assimilation"),
#          Trigger("./get_obs == complete")),
      bator = self.add_family("bator").add(Trigger("./get_obs == complete"))
      for ot in suite_config.obstypes_upper :
        bator.add(Family(ot, Edit(OBSTYPES=ot),
                          Task("bator",
                               Edit(ECF_FILES = suite_config.suite_path + "/scr/assimilation") )))
      self.add(
            Task("odb_merge", Trigger("./bator == complete"),
                              Edit(ECF_FILES = suite_config.suite_path + "/scr/assimilation") ),
            Task("addfields", Trigger("../check_first_guess == complete"),
                              Edit(ECF_FILES = suite_config.suite_path + "/scr/assimilation") ),
            Task("screening",
              Trigger("./odb_merge == complete && ./addfields == complete"),
              Edit(suite_config.tasktypes["screening"])),
            Task("minimisation", Trigger("screening == complete"),
              Edit(suite_config.tasktypes["minim"] )))


class nr_assimilation(Family):
  def __init__(self, suite_config):
    Family.__init__(self, "assimilation")
    self.add(
      Edit(suite_config.tasktypes["serial"]),
      Task("check_first_guess"),
      nr_assim_sfc(suite_config).add( Trigger("./check_first_guess == complete")),
      nr_assim_upper(suite_config).add( Trigger("./surface == complete")),
          Task("archive_assim", Trigger("./surface == complete && ./upper_air == complete"))
    )
    if suite_config.odb_arch :
      self.add(Task("archive_assim", Trigger("./surface == complete && ./upper_air == complete")))

