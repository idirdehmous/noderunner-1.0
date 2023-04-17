from ecflow import *
from nr_modules.nr_classes import *
from nr_modules.assimilation import *

def build_suite(suite, suite_config, config) :
  if suite_config.cycle_inc == 24 :
    # FIXME !!!
    print("For a cycle with 1 run per day: set suite_type = forecast_cycle_loop ")
  # What if RR != 00 ??? USE RUNCYCLE
  # single run cycle with a repeat cc=1:ncases
  #  add.(RepeatDate("YMD", case_list))

  if suite_config.forecast_length < suite_config.cycle_inc :
    print("ERROR: forecast_length can not be shorter than cycle_inc.")

# variables are easy to pass to jobs
# but they can not be used in triggers unless they are numeric (no string comparisons!)
# so we define an event to indicate whether we are in real time or delayed mode.
# (exp mode for experiments is, by definition, not real-time)
# ATTENTION: you can not initialise an event to "set" with add_event
#            maybe it can be done another way???
#            maybe using events in this way is not ideal
#            but what else can you use inside a trigger expression?
#suite.add_label("LAST_FINISHED", " ")

  if suite_config.realtime :
    suite.add_variable("REALTIME", "yes")
    if suite_config.delay_mode :
      suite.add_variable("DELAY", "no")
      suite.add_event("DELAY") #.force_event("set")
  else:
    suite.add_variable("REALTIME", "no")
#    suite.add_variable("DELAY", "no") # a bit strange...

# From experience, we know that HPC can get into problems with i/o
# So we must limit the number of post-processing jobs
#   (this is mainly for low resolution models which run very fast,
#    so the post processing lags behind)
# TODO: make this an option in the .ini file [settings]?

###########################################################

## Initialise the suite ###
  suite += nr_init_suite(suite_config)

# some simple tasks for changing the suite mode etc.
  suite += nr_maintenance(suite_config)


########################
# standard main cycle
########################

  suite.add_label("LAST_QUEUED", "")
  suite.add_variable("LAST_QUEUED", "")
  suite.add_label("LAST_RUNNING", "")
# TODO: - for a "single run" suite (e.g. only 00h): no triggering of next cycle possible
#           in that case: use a "repeat". Presumably not with assimilation.
#       - "CaseRunner": repeat over a given set of dates
#           (maybe including assimilation if you have archived FG's)
  cycleMain = suite.add_family("cycle")

  for i in range(suite_config.ncycle) :
    RR = i * suite_config.cycle_inc

    ## add a family for this cycle (e.g. "morning" or "00")
    mhour = cycleMain.add_family(suite_config.this_run(i))
    mhour += Edit(RR="%02d" % RR,
                  YMD="",
                  RUNDATE="@YMD@@RR@",
                  FCLEN=str(suite_config.fclen(i)),
                  THIS_RUN=suite_config.this_run(i),
                  PREV_RUN=suite_config.prev_run(i),
                  NEXT_RUN=suite_config.next_run(i)
                  )
    # ADDED TO AVOID SUITE CRASH WHEN IT S RELOADED (task create_hpc_paths)
    if i == 0: 
       suite.add_variable("THIS_RUN", suite_config.this_run(i) )
       suite.add_variable("PREV_RUN", suite_config.prev_run(i) )
       suite.add_variable("NEXT_RUN", suite_config.next_run(i) )
    mhour += Label("RUNDATE", "")
    mhour += Defstatus("complete")

    if suite_config.has_wait(i) :
      mhour += nr_wait(suite_config, i)

    ## Initialisation
    mhour += nr_initialisation(suite_config, i)

    ## LBC's #
    mhour += nr_lbc(suite_config, suite_config.fclen(i)).add(
                    Trigger("./initialisation == complete"),
                    InLimit("max_postproc"))

    ## assimilation family
    if suite_config.has_assimilation :
      mhour += nr_assimilation(suite_config).add(Trigger("./initialisation == complete"))

    ## the forecast itself #
    fctrigger = "(./lbc == complete or ./lbc:LAUNCH_FC == set)"
    if suite_config.has_assimilation :
      fctrigger += " && ./assimilation == complete "
    if suite_config.has_surfex :
      fctrigger += " && ./lbc/prep_sfx == complete "
    mhour += nr_forecast(suite_config, suite_config.fclen(i)).add(
                 Trigger(fctrigger))

    ## cycle tasks (queue next cycle, save first guess)
    mhour += nr_next_cycle(suite_config, suite_config.fclen(i), suite_config.next_run(i))

    ## post-processing family: hourly fullpos tasks
    if suite_config.has_postproc and suite_config.is_runcycle(i) :
      mhour += nr_postproc(suite_config, config)

    ## "post-processing" tasks that are not hourly full-pos, 
    ## but run once after the forecast is finished
    if suite_config.has_products and suite_config.is_runcycle(i) :
      mhour += nr_products(suite_config, config)

    ## A simple "alert" if the (realtime) forecast cycle takes too long
    if suite_config.realtime :
      mhour += nr_time_alert(suite_config)

    # things that run /after/ the forecast has finished
    mhour += nr_finish(suite_config, suite_config.is_runcycle(i))

