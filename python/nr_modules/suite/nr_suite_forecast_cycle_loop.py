from ecflow import *
from nr_modules.nr_classes import *
from nr_modules.assimilation import *

def build_suite(suite, suite_config, config) :
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
  cycleMain.add(RepeatDate("YYYYMMDD", int(bdate), int(edate)))

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
      mhour += nr_assimilation(suite_config)

    ## the forecast itself #
    mhour += nr_forecast(suite_config, suite_config.fclen(i))

    ## post-processing family: hourly fullpos tasks
    if suite_config.has_postproc and suite_config.is_runcycle(i) :
      mhour += nr_postproc(suite_config, config)

    ## "post-processing" tasks that are not hourly full-pos, 
    ## but run once after the forecast is finished
    if suite_config.has_products and suite_config.is_runcycle(i) :
      mhour += nr_products(suite_config, config)

    ## A simple "alert" if the forecast cycle takes too long
    if suite_config.realtime and suite_config.mode == "oper" :
      mhour += nr_time_alert(suite_config)

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
      mhour += Task("queue_next",
                 Trigger("./initialisation == complete && /{0}/cycle/{1} == complete"\
                     .format(suite_config.name, suite_config.next_run(i))),
                 Complete("/{0}/cycle/{1} == active and (100 * /{0}/cycle/{1}:YMD + /{0}/cycle/{1}:RR > 100 * :YMD + :RR)"\
                     .format(suite_config.name, suite_config.next_run(i))),
                 Edit(suite_config.jobs["localjob"]))
# things that run /after/ the forecast has finished
      mhour += nr_finish(suite_config, suite_config.is_runcycle(i))

