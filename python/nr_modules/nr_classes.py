from ecflow import *

# NOTE: actually, we want these funtions to work for all ecflow nodes
#       so they might as well be simple functions...
#       That may even be safer, to avoid attribute overlap
class nr_node :
  def add_trigger(self, depend) :
    self.add_trigger(depend + " == complete")

  def add_node_structure(self, ncores) :
    self.add_variable("NODE_SELECT", self.nr_config.platform.define_topology(ncores))
    self.add_variable("QUEUE", self.nr_config.platform.define_queue(ncores))


# NOTE: we want to have the job output in scratch
#       therefore, path creation of the log directory can not be a submitted task
class nr_init_suite(Family, nr_node):
  def __init__(self, suite_config):
    Family.__init__(self, "init_suite")
    self.nr_config = suite_config
    self.add(Task("create_hpc_paths",
           Edit(suite_config.jobs["localjob"]),
           InLimit("max_init")))

class nr_maintenance(Family, nr_node):
  def __init__(self, suite_config):
    Family.__init__(self, "maintenance")
    self.nr_config = suite_config
    self.add(
      Task("cleanup_cycle", Defstatus("complete"), Label("LAST_RUN","")),
      # switching the scratch must also be a "localhost" job
      # because if the current scratch is down, job submission may fail
      Task("switch_scratch",
           Defstatus("complete"),
           Edit(suite_config.jobs["localjob"]),
           Label("SCRATCH", "@SCRATCH@")))

    if suite_config.delay_mode :
      self += Family("delay", Edit(suite_config.jobs["localjob"])).add(
        Task("detect_delay", Trigger("/{0}:DELAY == set".format(suite_config.name))),
        Task("reset_delay", Trigger("/{0}:DELAY == clear".format(suite_config.name))))

####################################

# a "realtime" suite may have to wait for a certain time or for a trigger
# non-realtime suites don't have this node (there the init family itself waits).
 # we need an actual "task" that can run (so at time X:X it will "complete") 
  # an empty family or dummy task will never be "complete"
  # so we need a task that contains only header and tail
  # but in catchup mode, we don't wait for this task to "run" at time X:X
  # you can also manually set the task to complete without needing catchup mode
  #  

  # In a non-realtime downscaling cycle we never need to "wait"!
  # a job can start as soon as it is queued (which can only happen if the previous day was complete)
  # unless we have a "trigger" suite (e.g. a nesting run)
  # NOTE: if queue_next_cycle waits for first_guess, has_assimilation can be disregarded here

# NOTE: __init__  needs to know which cycle (i)
class nr_wait(Family, nr_node):
  def __init__(self, suite_config, i):
    Family.__init__(self, "wait")
    self.nr_config = suite_config
    if suite_config.delay_mode :
      compl = " /{0}:DELAY == set".format(suite_config.name)
      if suite_config.has_assimilation :
        compl = compl + " && ../{0}/forecast/save_first_guess/{1} == complete".format(suite_config.prev_run(i),
          "%02d"%suite_config.cycle_inc)
      self.add(Complete(compl))

    if ( suite_config.realtime and suite_config.cycle_times[i] != "" ) :
      self += Task("wait_time",
                   Edit(suite_config.jobs["localjob"]),
                   Time(suite_config.cycle_times[i]))

    if suite_config.has_trigger and suite_config.trigger_labels[i] != "" :
      trigger = suite_config.trigger.replace("{cycle}", suite_config.trigger_labels[i])
      self += Task("wait_trigger",
                   Edit(suite_config.jobs["localjob"]),
                   Trigger(trigger))


####################################
##################
# Initialisation #
##################

class nr_init_caserunner(Family, nr_node):
  def __init__(self, suite_config):
    Family.__init__(self, "initialisation")
    self.nr_config = suite_config
    self += Trigger("../init_suite == complete")
    self.add(Task("copy_namelists",
        Edit(suite_config.jobs["localjob"]),
        InLimit("max_init")))
    self.add(Task("sync_data", InLimit("max_init")))
    self.add(Task("init_workpaths"))


class nr_initialisation(Family, nr_node):
  def __init__(self, suite_config, i):
    Family.__init__(self, "initialisation")
    self.nr_config = suite_config

    prev_run = suite_config.cycle_labels[ (i - 1) % suite_config.ncycle]
    next_run = suite_config.cycle_labels[ (i + 1) % suite_config.ncycle]
    this_run = suite_config.cycle_labels[ i ]
    # assimilation needs to wait for first guess
    if suite_config.has_assimilation :
      self += Trigger("../{0}/next_cycle/save_first_guess/{1} == complete ".format(
        prev_run, "%02d" % suite_config.cycle_inc))
    # realtime suites may have a "wait" family
    if suite_config.has_wait(i) :
      self += Trigger("./wait == complete")
    # set some labels and check timeliness
    self += Task("init_forecast", Edit(suite_config.jobs["localjob"]))
    # operational suites may have a "time alert"
    if suite_config.realtime and suite_config.mode == "oper" :  # set the "timer"
      self.add(Task("set_alert", Edit(suite_config.jobs["localjob"])))
    # make sure all data and namelists are available on HPC
    # these are retrieved from the ecflow server side!
    # we run this as a local job, so HPC side does not need an ssh key to connect to the ecflow server
    self.add(Task("copy_namelists",
        Edit(suite_config.jobs["localjob"]),
        InLimit("max_init")))
    # create directories etc
    # make sure all binaries, clim files etc. are available on HPC
    # these are retrieved from HPC side
    self.add(Task("sync_data", InLimit("max_init")))
    self.add(Task("init_workpaths"))
# It would be nice to have "queue_next" here, but alas: this task /may/ not complete immediately
# Unless we decide that is not a real problem (extremely unlikely anyway)
# Maybe it's not a bad idea to have "initialisation" wait until the "next_run" from a day before has finished
#    self.add(Task("queue_next", 
#                   Trigger("./sync_data == complete and /{0}/cycle/{1} == complete".format(
#                        suite_config.name, suite_config.next_run(i))),
#                   Complete("/{0}/cycle/{1}:RUNDATE > @RUNDATE@".format(
#                        suite_config.name, suite_config.next_run(i)),
#                   Edit(suite_config.jobs["localjob"])))


####################################
# TODO:
#       - make this a set of single-lbc tasks (triggered how? by retrieval?)
#       - don't hard-code WALLTIME ?
#       - For a suite that is WAITING for incoming lbc's, you should have:
#             1 retrieve task with a meter OR multiple retrieve task with external trigger
#             multiple prep tasks
#         DILEMMA: if you trigger on e.g. lbc/03, there is no guarantee that 0-2 are already OK...
#                  so maybe trigger on all lbc's 0..3 ? Or just don't bother...
#         ALSO: assimilation and forecast should then trigger on a task, not a meter...
#         EVENT: lbc:LAUNCH_FC is set if enough lbc's are ready... How?
#         NOTE: AO40 /may/ run faster than serial prep_lbc if hourly LBC's are used!
class nr_lbc(Family):
  def __init__(self, suite_config, fclen):
    Family.__init__(self, "lbc")
    self.add(Edit(ECF_FILES = suite_config.suite_path + "/scr/lbc"))
    self.add_event("LAUNCH_FC")
    self.add_event("LAUNCH_00")

    # NOTE: * this is a single task for all LBC's
    #       alternatively, you may want a set of single-lbc tasks
    #       * fclen is passed explicitly, because depending on context, it may be different from
    #         fclen = suite_config.fclen(i)
    #       the actual forecast length (DA cycle, Bmatrix ...)

    # FOR LBC recovery, we should increase fclen to make it a multiple of lbc_inc
    if fclen % suite_config.lbc_inc != 0 :
      fclen = (fclen // suite_config.lbc_inc + 1) * suite_config.lbc_inc
                    
    self.add_task("retrieve_lbc").add(
           Edit(WALLTIME="@WALLTIME_RET@"), # set much higher if you are waiting for telecom files!
           Meter("lbc_counter", -1, fclen))
    self.add_task("prep_lbc").add(
           Edit(WALLTIME="@WALLTIME_PRE@", NODE_SELECT="@SELECT_PRE@"), 
           Meter("lbc_counter", -1, fclen), Trigger("retrieve_lbc == complete"))

    # NOTE: if the LBC's are already on the model grid, no "e927" step is required
    #       BUT: make sure there are no invalid references to it
    #       COULD just be complete by default...
#    if suite_config.has_e927 :
#      self.add_task("prep_lbc").add(
#        Trigger("./retrieve_lbc == complete"),
#        Edit(suite_config.tasktypes["pre"]),
#        Meter("lbc_counter", -1, fclen))




    #  for (i in range(0, fclen+1)) :
    #    self.add(Family("%02d"%i).add(
    #       Task("retrieve_lbc"...
    #       Task("prep_lbc", Trigger("./retrieve_lbc == complete")
  # With surfex you also need to prepare a 00h initial surfex file
  #    either for downscaling mode or for coldstart
  # NOTE: in a DA cycle, this task may be set "complete" by the initialisation task
  # FIXME: in some contexts, it would be better to have a Complete() statement
  # Complete( "ASSIMILATION and @RUNDATE@ != @COLDSTART@")
  #    BUT that needs fixing
  #  OR: you can do this in the script itself, but that is not so nice
  # PROBLEM: in some contexts, RUNDATE is actually YYYYMMDD + RR 
  #          so you can not compare to "COLDSTART"
  # we can at least set the "complete" for all intermediate hours
  # but the rest of any "Complete" would have to be added a posteriori
  #   Is this possible?
    if suite_config.has_surfex :
      # trigger prep if 00h LBC is ready
      if suite_config.has_e927 :
        sfx_trigger = "../lbc:LAUNCH_00 == set"
      else :
        sfx_trigger = "./retrieve_lbc == complete"
      self.add_task("prep_sfx").add(
           Edit(suite_config.tasktypes["pre"]),
           Trigger(sfx_trigger))


####################################

# FIXME:
#   in "case_runner" or a 24h cycle (single run/day), i is undefined...
# MAYBE: just pass fclen, and forget the "fc_short" tasktype...
# MAYBE: have ECF_FILES as part of tasktypes["forecast"]
class nr_integration(Task):
  def __init__(self, suite_config, fclen, tasktype="forecast"):
    Task.__init__(self, "integration")
    self.add(Edit(ECF_FILES = suite_config.suite_path + "/scr/forecast"))
    self.add(Edit(suite_config.tasktypes[tasktype]))
    self.add(Meter("forecast_counter", -1, fclen))



class nr_forecast(Family):
  def __init__(self, suite_config, fclen):
    Family.__init__(self, "forecast")

#    self.add(nr_integration(suite_config, fclen))
    self += Task("integration").add(
                  Edit(ECF_FILES = suite_config.suite_path + "/scr/forecast"),
                  Edit(suite_config.tasktypes["forecast"]))

    self += Task("monitor").add(
                  Edit(suite_config.tasktypes["serial"]),
                  Edit(WALLTIME = "@WALLTIME_FC@"),
                  Trigger("./integration == active || ./integration == complete"),
                  Meter("forecast_counter", -1, fclen))


    # FIXME: this class adds a trigger, so not fully self-contained
    #    NOTE: we now add the trigger in the suite script
    # NOTE: avoid getting ./lbc == complete or (lbc_counter >= 2 and assim == complete)
    # so put brackets here !
    #fc_trigger = "( ./lbc == complete or ./lbc:LAUNCH_FC == set)"
    # 
    # fc_trigger = "./lbc/00 == complete"
    # 
#    if suite_config.has_surfex :
#      fc_trigger += " and ./lbc/prep_sfx == complete"
    # NOTE: don't worry, the cycle initialisation will set prep_sfx complete if it is not needed
    #       in a DA cycle, you only need it for a cold start
#    self.add( Trigger(fc_trigger))

####################################

# CYCLE #

class nr_next_cycle(Family):
  def __init__(self, suite_config, fclen, next_run):
    Family.__init__(self, "next_cycle")
    
    # queue the next cycle (can be done before forecast!)
    # BUT: we could trigger this on save_first_guess
    # then the next job doesn't have to "wait" for it.
    # only small disadvantage: you don't see the job in "waiting" state
    #   it could run as soon as it is queued
    # FIXME: this may fail if the next run is already queued and the current cycle is re-queued
    #        the trigger will not be satisfied and the task will be stalled forever
    #        unless we set the next run to complete
    # FIXME 2: if you drop the trigger "next_run == complete" you /can/ get an error rather than an eternal wait.
    #          if the -24h cycle is still running (e.g. fast downscaling experiment) you can not re-queue it.

    if suite_config.cycle_inc > 0 :
      self += Task("queue_next",
                 Trigger("../initialisation == complete && /{0}/cycle/{1} == complete"\
                     .format(suite_config.name, next_run)),
                 Complete("/{0}/cycle/{1} == active and (100 * /{0}/cycle/{1}:YMD + /{0}/cycle/{1}:RR > 100 * :YMD + :RR)"\
                     .format(suite_config.name, next_run)),
                 Edit(suite_config.jobs["localjob"]))

    # save first guess      
    if suite_config.has_assimilation :
      self.add(nr_save_first_guess(suite_config, fclen))


class nr_save_first_guess(Family):
  # we have the option to save "early" first guesses for later cycles
  # this adds some robustness for emergencies
  # BUT: only when there is a long enough forecast.
  # NOTE: for surfex, we include the copy_Ts task!
  def __init__(self, suite_config, fclen):
    Family.__init__(self, "save_first_guess")
    if fclen < suite_config.cycle_inc :
      raise Exception("fclen is shorter than cycle_inc")
    hhmax=min(fclen, suite_config.fg_max)
    for hh in range(suite_config.cycle_inc, hhmax + 1, suite_config.cycle_inc):
      if suite_config.has_surfex and hh == suite_config.cycle_inc :
        self += Family("%02d" % hh,
                   Trigger("../../forecast/monitor:forecast_counter >= " + str(hh)),
                   Edit(WALLTIME = "00:05:00", ECF_FILES=suite_config.suite_path + "/scr/next_cycle"),
                   Task("copy_Ts"),
                   Task("save_first_guess", Trigger("./copy_Ts == complete")))
      else :
        self += Family("%02d" % hh,
                   Trigger("../../forecast/monitor:forecast_counter >= " + str(hh)),
                   Edit(WALLTIME = "00:05:00", ECF_FILES=suite_config.suite_path + "/scr/next_cycle"),
                   Task("save_first_guess"))


###################
# POST-PROCESSING #
###################

class nr_postproc(Family):
  # here we also pass the original config, because we need to read the products
  # TODO: run for a selected subset of lead times ("at +03", "every 3h", ...)
  # TODO: for "intermediate" cycles (assimilation only), some tasks may still apply
  #       e.g. "gather_io", "save_first_guess"...
  # FIXME: for this, we need to know whether we are in a "forecast" run or not
  # NOTE: "gather_io" only at +3h for assim. run, but every hour at fc runs!!!
  def __init__(self, suite_config, config):
    Family.__init__(self, "post")
    self.add(Trigger("./forecast/integration == complete or ./forecast/integration == active"))
    self.add(Edit(ECF_FILES=suite_config.suite_path + "/scr/post"))
    tasklist = { x[0]:str(x[1]) for x in config.items("postproc") }
    # now we produce a family of post-production tasks for every lead time
    # FIXME: for every lead time, check whether there are any tasks
    for hh in range(1, suite_config.forecast_length+1) :
      pp_node = self.add_family("%02d" % hh).add(
#      Trigger("../forecast == complete or ../forecast:forecast_counter >= "+str(hh)),
        Trigger("../forecast/monitor:forecast_counter >= "+str(hh)),
        Edit(PPHH="%02d" % hh))
      for tt in tasklist.keys() :
        # now we add a task (family) for every post-production task in the ini file
        # but because most tasks will reference the same script "interpolation",
        # we make a family with one task. Not perfect, I know.
        pp_fam = pp_node.add_family(tt)
        # add the local variables defined in .ini file
        # special cases: "script" (alternative script name) "trigger" (wait for other pp tasks)
        script_name="interpolation"
        if len(tasklist[tt]) > 0 :
          for pp_opt in [ p for p in tasklist[tt].replace("\n", ",").split(",") if p.strip() ]:
            zz = list(map(str.strip, pp_opt.split("=")))
            if zz[0] == "script" :
              script_name = zz[1]
#              print("Alternative post-processing script: "+script_name)
            elif zz[0] == "trigger" :
              trigger_list = map(str.strip, zz[1].split())
              trigger = " and ".join(["./" + x + " == complete " for x in trigger_list])
#              print("Trigger: " + trigger)
              pp_fam.add_trigger(trigger)
            else :
              pp_fam.add_variable(zz[0], zz[1])
        # actual interpolation task
        pp_task = pp_fam.add_task(script_name)
        if script_name == "interpolation" :
          pp_task.add(
            InLimit("max_postproc"),
            Edit(NODE_SELECT="@SELECT_POS@", WALLTIME="00:05:00"))

####################################

############
# PRODUCTS #
############

class nr_products(Family):
  # here we also pass the original config, because we need to read the products
  def __init__(self, suite_config, config):
    tasklist = { x[0]:str(x[1]) for x in config.items("products") }
    Family.__init__(self, "products")
    self.add(Edit(ECF_FILES=suite_config.suite_path + "/scr/products"))
    self.add(Trigger("./forecast == complete"))
    if suite_config.has_postproc :
      self += Trigger("./post == complete")

    for tt in tasklist.keys() :
      prod_task = self.add_task(tt)
#      print("Product: " + tt)
      if len(tasklist[tt]) > 0 :
#        print(tasklist[tt])
# to allow for missing "," when there is a \n: er.split(",|\n", tasklist[tt])
#                         OR: tasklist[tt].replace("\n",",").split(",")
# also check for empty strings (e.g. if there is a "," at the end, or "\n," ...
        for prod_opt in [ p for p in tasklist[tt].replace("\n",",").split(",") if p.strip() ] :
          zz = list(map(str.strip, prod_opt.split("=")))
#          print(zz[0] + " : " + zz[1])
          if zz[0] == "local" and zz[1] == "yes" :
            prod_task.add_variable(suite_config.jobs["localjob"])
#          elif zz[0] == "script" :
#            script_name = zz[1]
          elif zz[0] == "trigger" :
            trigger_list = map(str.strip, zz[1].split())
            trigger = " and ".join(["./" + x + " == complete " for x in trigger_list])
            prod_task.add_trigger(trigger)
          else :
            prod_task.add_variable(zz[0], zz[1])

####################################

class nr_time_alert(Task):
  # A simple "alert" if the forecast cycle takes too long
  # But the trigger statement is not so simple
  # We need an alert if time >= alert_time
  # but that /may/ involve a change of date 
  #   If alert_time is 00:10, the alert should NOT be triggered at 23:50!
  #   (or e.g. if alert_time is 23:59, then 00:01 of the /next/ day should trigger the alert)
  #   doing math in the trigger statement is almost impossible
  #   So you can't even have a single integer for YYYYMMDD actual time 
  #   You have the 3 components, or a string YYYY.MM.DD, but that can not be used in trigger
  # so we also need to check the date
  # We could set a "time", but that adds rather a lot of complexity that I would like to avoid
  # Assuming the cycle walltime is less than 24h, we only need to consider the DD variable!
  #   (if this fails, there is something seriously wrong anyway...)
  def __init__(self, suite_config):
    Task.__init__(self, "time_alert")
    compl = "./finish == complete "
    if suite_config.delay_mode :
      compl = compl + " || /{0}:DELAY == set".format(suite_config.name)

    self.add(
      Edit(suite_config.jobs["localjob"]),
      Edit(ECF_TRIES = 1, ALERT_YYYY=0, ALERT_MM=0, ALERT_DD=0,
                      ALERT_TIME = 0000), 
      Complete(compl),
      Trigger("./initialisation == complete && \
            ( (:ALERT_TIME <= /{0}:TIME && :ALERT_DD == /{0}:DD) ||\
            (:ALERT_TIME >= /{0}:TIME && :ALERT_DD != /{0}:DD)  )".format(suite_config.name)),
      Label("ALERT_TIME", "00000000 00:00"))

####################################

class nr_finish(Family):
  # TODO: is_runcycle is only used for the trigger
  #       so that could be added elsewhere.
  def __init__(self, suite_config, is_runcycle):
    Family.__init__(self, "finish")
    self.add(
      Trigger("./forecast == complete"),
      Task("cleanup"), # clean up scratch (a and b) and work directories
      Task("set_defstatus", Edit(suite_config.jobs["localjob"])) # set family to "complete by default"
      )
    if suite_config.has_assimilation :
      self.add(
#        Trigger("./save_first_guess == complete"),
        Task("cycle_data_update", InLimit("max_sync"))) # remove old first_guesses and sync to secondary scratch

    if is_runcycle :
      if suite_config.has_postproc :
        self.add(Trigger("./post == complete"))
      if suite_config.has_products :
        self.add(Trigger("./products == complete"))
#    self.add(
#      Task("check_next", 
#        Complete("../queue_next == complete"), 
#        Edit(suite_config.jobs["localjob"])))


