from ecflow import *
from nr_modules.nr_classes import *
from nr_modules.assimilation import *

def build_suite(suite, suite_config, config) :
  # GET SOME SUITE CONFIG VARIABLES 
  basedir = str(config.get("settings", "BASEDIR"))
  Nmemb   = int(config.get("bmatrix", "NMEMBERS"))
  Nperiod = 2

  # femars:
  DiffLen= config.getint("bmatrix", "DIFF_LEN")

  # "model", "settings"
  section_list = [ "bmatrix", "festat" ]
  for section in section_list :
  # TODO: check all entries? default values?
    if section in config.sections() :
      x = config.items(section)
      xd = { str(y[0]):str(y[1]) for y in x }
      suite.add_variable(xd)

  # BEGIN AND END DATE OF WINTER AND SUMMER PERIODS 
  bdates   = [x for x in str(config.get("bmatrix", "BDATES_P1")).replace(","," ").split(" ") if x ]
  edates   = [x for x in str(config.get("bmatrix", "EDATES_P1")).replace(","," ").split(" ") if x ]
  runtimes = [x for x in str(config.get("bmatrix", "RUNTIMES_P1")).replace(","," ").split(" ") if x ] 
  Nperiod  = len(bdates)
  if Nperiod != len(edates) or Nperiod != len(runtimes) : raise Exception("Inconsistent P1 variables")

  # COMMON FAMILIES AND TASKS
  init = nr_init_suite(suite_config)
  init += Task( "sync_data"  ,
               Trigger ( "create_hpc_paths == complete"),
               Edit(ECF_FILES=suite_config.suite_path+"/scr/initialisation"))
  init += Task("copy_namelists",
               Trigger ( "create_hpc_paths == complete"),
               Edit(suite_config.jobs["localjob"],
                    ECF_FILES=suite_config.suite_path+"/scr/initialisation"))
  suite += init
#  suite.add ( Task( "get_aearp_files" ,
#    Edit (ECF_FILES=suite_config.suite_path + "/scr/bmatrix" ,
#          RUNDATE=FirstDate)))
  # TODO: femars is a serial job -> SLOW
  #       can we run multiple // verions?
  #        * If we organise the forecasts by rundate (all members //), we can trigger femars by step
  #        * OR: can we use MPI placement to run on all separate cores of a node at once? I think not.
  ncores_femars = 1 # eval(config.get("platform", "ncores_femars", fallback="1"))
  ncores_festat = 1
  select_femars = suite_config.platform.define_topology(ncores_femars)
  select_festat = suite_config.platform.define_topology(ncores_festat)
  queue_femars = suite_config.platform.define_queue(ncores_femars)
  queue_festat = suite_config.platform.define_queue(ncores_festat)
  walltime_femars = "3:00:00"
  walltime_festat = "1:00:00"

  ##########
  # ENS_SU #
  ##########

  # FIRST PART OF B MATRIX ( DOWNSCALING MODE )
  # ens_su IS ITS FAMILY OBJECT
  ens_su = suite.add_family ("ENS_SU").add(
      Trigger("init_suite == complete"),
      Edit(B_PART="ENS_SU", ASSIMILATION="no", d_OUT="@BASEDIR@/output"))


  # CREATE MEMBER AND RUNDATE FAMILIES
  MemberList = ["member{:02}".format(m+1) for m in range(Nmemb)]
  PeriodList = ["period{:1}".format(p+1)  for p in range(Nperiod)]

  # NOTE: if we re-order such that the ensemble members run together
  #       we can then split femars into separate tasks per date
  #       BUT: if there are multiple parallel periods,
  #            it may be hard to make sure the gribdiff's are correctly numbered

  # LOOP OVER MEMBERS & PERIODS ; REPEAT DATES
  for m in range(Nmemb):
    MemberName = MemberList[m]
    Member = ens_su.add_family(MemberName)
    Member += Edit(MEMBER="{:02}".format(m+1), FCLEN="@DIFF_LEN@")
    for p in range(Nperiod) :
      per = Member.add_family(PeriodList[p])
      per.add(RepeatDate("YYYYMMDD", int(bdates[p]), int(edates[p])),
              Edit(WORKDIR="@BASEDIR@/work/@B_PART@/@MEMBER@/@PERIOD@",
                   RUNTIME="{:02}".format(int(runtimes[p])),
                   PERIOD=PeriodList[p],
                   RUNDATE="@YYYYMMDD@@RUNTIME@"))
      per += Task("init_workpaths", Edit(ECF_FILES=suite_config.suite_path+"/scr/initialisation"))
      per += nr_lbc(suite_config, fclen=DiffLen).add(
                    Trigger("./init_workpaths == complete"),
                    InLimit("max_postproc"))
      per += nr_integration(suite_config, fclen=DiffLen).add(
               Trigger("./lbc == complete or (./lbc/prep_sfx == complete && ./lbc/prep_lbc:lbc_counter >= 3 )"))
      per += Task("save_for_femars",
                  Trigger("./integration == complete"),
                  Edit(ECF_FILES=suite_config.suite_path+"/scr/bmatrix"))

  # FIXME: potential small bug: if e.g. /output/01 does not yet exist
  #        and 2 period tasks create it simultaneously -> very small risk, but NFS latency can interfere

  # FEMARS TASK -------------------------
  # PREPARE A TRIGGER FOR THE femars TASK ( according to the number of members)
  mtrig=" && ".join([ "member{:02} == complete".format(m+1) for m in range(Nmemb)])

  # NGRIB NEEDED FOR ECFLOW COUNTER
  #   length of all periods (in days) + Nmemb
  ngrib = sum([ (datetime.datetime.strptime(edates[p], "%Y%m%d") - 
                 datetime.datetime.strptime(bdates[p], "%Y%m%d")).days + 1 
                 for p in range(Nperiod) ]) * Nmemb

  femars = Task("femars",
      Trigger(mtrig),
      Meter("N_differences", 0, ngrib, ngrib/2),
      Edit(ECF_FILES=suite_config.suite_path+"/scr/bmatrix",
           WORKDIR="@BASEDIR@/work/@B_PART@",
           NODE_SELECT=select_femars, QUEUE=queue_femars, WALLTIME=walltime_femars))
  ens_su += femars

  # FESTAT TASK-------------------------
  festat = Task("festat",
      Trigger("./femars == complete"),
      Edit(ECF_FILES=suite_config.suite_path+"/scr/bmatrix",
           WORKDIR="@BASEDIR@/work/@B_PART@",
           NODE_SELECT=select_festat, QUEUE=queue_festat, WALLTIME=walltime_festat))
  ens_su += festat
# TODO: send JB output to "@d_OUT@/JB1" OR just set d_JB=...ENS_SU/festat
  # END OF THE "ENS_SU" PART !

##########
# ENS_DA #
##########
  # SECOND PART OF B MATRIX ( DA MODE )
  # ens_da IS ITS FAMILY OBJECT
  ens_da = suite.add_family ("ENS_DA").add(
      Trigger("./ENS_SU == complete"),
      Edit(B_PART="ENS_DA", d_OUT="@BASEDIR@/output", d_JB="@d_OUT@/JB1"))

  # LOOP OVER MEMBERS & PERIODS ; REPEAT DATES
  # TODO: currently, we suppose that the periods and run times are the same as in the ENS_SU part
  for m in range(Nmemb):
    MemberName = MemberList[m]
    Member = ens_da.add_family(MemberName)
    Member += Edit(MEMBER="{:02}".format(m+1), FCLEN="@DIFF_LEN@")
    for p in range(Nperiod) :
      per = Member.add_family(PeriodList[p])
      per.add(RepeatDate("YYYYMMDD", int(bdates[p]), int(edates[p])),
              Edit(WORKDIR="@BASEDIR@/work/@B_PART@/@MEMBER@/@PERIOD@",
                   RUNTIME="{:02}".format(int(runtimes[p])),
                   PERIOD=PeriodList[p]))
      rr_list = map(lambda x:"{:02}".format(x), range(0,24,suite_config.cycle_inc))
      cycle = per.add_family("cycle")
      # FIXME: ideally, we want FCLEN=CYCLE_INC except for 1 run where =DIFF_LEN
      #        of course, if both are ==3, it's simple.
      #        ? can we have FCLEN "dynamic"? Without modifying scripts?
      cycle.add(RepeatString("RR", rr_list),
                Edit(RUNDATE="@YYYYMMDD@@RR@",
                     d_CYCLE="@BASEDIR@/cycle/@MEMBER@/@PERIOD@",
                     COLDSTART=bdates[p]+"00"))
      cycle += Task("init_workpaths", Edit(ECF_FILES=suite_config.suite_path+"/scr/initialisation"))
      cycle += nr_lbc(suite_config, fclen=DiffLen).add(
                    Trigger("./init_workpaths == complete"),
                    InLimit("max_postproc"))
      cycle.lbc.prep_sfx.add(
          Complete(":YYYYMMDD != " + bdates[p] + " or :RR != 0"))
      cycle += nr_assimilation(suite_config).add(Trigger("./init_workpaths == complete")).add(
          Complete(":YYYYMMDD == " + bdates[p] + " && :RR == 0"))
      cycle += nr_integration(suite_config, fclen=DiffLen).add( 
          Trigger("(./lbc/prep_lbc:lbc_counter >= 3 or ./lbc/prep_lbc == complete) && ./assimilation == complete "))
      cycle += nr_save_first_guess(suite_config, fclen=DiffLen)
      cycle += Task("save_for_femars",
                  Complete(":RR != "+str(runtimes[p])),
                  Trigger("./integration == complete"),
                  Edit(ECF_FILES=suite_config.suite_path+"/scr/bmatrix"))
      cycle += Task("cycle_cleanup").add(
                  Edit(ECF_FILES=suite_config.suite_path+"/scr/finish"))

 
  femars = Task("femars",
      Trigger(mtrig),
      Meter("N_differences", 0, ngrib, ngrib/2),
      Edit(ECF_FILES=suite_config.suite_path+"/scr/bmatrix",
           WORKDIR="@BASEDIR@/work/@B_PART@",
           NODE_SELECT=select_femars, QUEUE=queue_femars, WALLTIME=walltime_femars))
  ens_da += femars

  festat = Task("festat",
      Trigger("./femars == complete"),
      Edit(ECF_FILES=suite_config.suite_path+"/scr/bmatrix",
           WORKDIR="@BASEDIR@/work/@B_PART@",
           NODE_SELECT=select_festat, QUEUE=queue_festat, WALLTIME=walltime_festat))
  ens_da += festat

  # END OF THE "ENS_DA" PART !


