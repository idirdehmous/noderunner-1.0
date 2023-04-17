#! /usr/bin/env python
def build_suite(suite, suite_config) :
  print("Non-cycling suite (case-runner)!")
  case_list = map(str.strip, str(config.get("suite", "case_list")).split(","))
  run = suite.add_family("Run")
  run.add(RepeatString("RUNDATE", case_list),
          Edit(FCLEN=str(suite_config.forecast_length)))
  run += nr_init_caserunner(suite_config)
  run += nr_lbc(suite_config, suite_config.forecast_length)
  run += nr_forecast(suite_config, -1)
  if suite_config.has_postproc :
    run += nr_postproc(suite_config, config)
  if suite_config.has_products :
    run += nr_products(suite_config, config)
# cycle initialisation should find the next case date from a list! 
# run += nr_initialisation(

