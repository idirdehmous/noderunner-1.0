# Node Runner

## Introduction

Node Runner is a project for a quite generic ecFlow script for model runs and B-matrix creation.
The basic ingredients are a python file for generating the suite definition, a set of scripts and a few configuration files (some for suite generation, some for the actual runtime application).

The design philosophy has a few points worth of notice:

* Avoid "hidden" code: the ecflow scripts are not just wrappers for a script running on the HPC side.
* Easy configurability: most suite configuration is in a single <suite>.ini file.
* Efficient cycling: in experimental mode (non-realtime) allow a next cycle to start as soon as the first guess is available. Several cycles can be active at once.
* Portability: all parts that depend on the local platform (HPC topology etc.) are grouped in a very limited number of files, to make it as easy as possible to configure.


## Installation

Installation of Node Runner itself happens at the side of the ECflow server. On the HPC side, the working directories etc. will be created automatically, but a number of files need to be installed on the HPC side before you can run Node Runner.

### HPC side
* MASTERODB (and other executables for data assimilation like BATOR etc.)
* CLIM files
* Some runtime data and smaller 

In experimental mode, Node Runner will merely link to these files. In operational mode, a hard copy is made on scratch to avoid any latency.

### ECflow server side
The Node Runner package is in a git repository. At ECMWF, it may be cloned from ~cv6/NodeRunner .

* Node Runner requires python, preferably python3. If python2 is used, make sure to install configparser (a backport of the python3 standard module), because the python2 module ConfigParser (note the capital letters) misses some important features. You may also need numpy (but only for special features).

* The installation of the suite (i.e. where you clone the git repository) must correspond to the name of your suite, e.g.  
git clone ~cv6/NodeRunner MyNewSuite

* If space in the home directory is limited, you may want to redirect MyNewSuite/tmp to $TEMP or such, e.g.  
> mkdir -p /tmp/<user>/ECF/<suite>  
> ln -s /tmp/<user>/ECF/<suite> $HOME/ECF/<suite>/tmp
This tmp subdirectory is used for the job files (i.e. the .ecf scritps after macro-expansion) and also the output of local tasks (i.e. tasks running on the ecflow server, not the HPC).

### Local configuration

A number of files may have to modified (or created) when installing Node Runner an a new platform:

* modules/arch/<platform>.py small python files that describes the basic HPC topology (cores per node, queue names...)
* include/settings_local_<platform>.h : local settings, for instance (at RMI) where and how or retrieve LBCs.
* bin/schedule_<platform> : a bash script that makes sure a job is launched on the HPC (or another server). Needs to know about queueing system (PBS, slurm...) etc. In the case of RMI, this required some special treatment for "reservations".
* The namelists (which are on the ecflow server side) may need to be adapted depending on e.g. the model version or local tuning. It is possible to create new subdirectories with different namelist versions.
* include/head.h : may need some changes (path, module...) to make ecflow available.

## What is in the package?

The base directory contains a number of executable scripts (bash and python):

* node_runner.py : the basic tool to create the actual suite definition. This will be discussed in further chapters.
* init_suite, replace_all : initialise and start the suite in ECflow, replace the .def file (after changes in e.g. the ini file)
* restart : this is the easiest way to actually start the suite (it can also be don from the ecflow_ui interface).

When you install Node Runner, you get a number of subdirectories:

* *include* : contains various files with settings that will be included in the ecf files. This includes the header file(s), but also a number of other settings and runtime environment.
* *data* : this contains some subdirectories that will be copied to the HPC side at the start of every run (using rsync). 
  + name : various subdirectoriies with versions of namelists. A suite shold use only one subdirectory.
  + bin : some simple tools (mostly python) that are also used at the HPC side.
    - dateincr : simple date/time manipulations (same interface as ECMWF dateincr)
    - fa_checkdate : check rundate & leadtime of a FA file
    - fa_checksize : check whether a FA file is complete (declared file size must correspond to actual size)
* *ini* : contains various examples (from RMI) of suite ini files
* *doc* : documentation
* *modules* : contains most of the python code for Node Runner, in particular all the classes data. It also contains nr_topology.nr which defines some basic aspects of the local HPC platform.
* *scr* : this is where all the ecflow scripts are.
* *tmp* : this is where job files etc. are created. As mentioned before, you may want to make this a link to /tmp if space on the home directory is limited.



## Platform configuration

To run on a new platform (local server, ...), some files will have to be adapted (see above). More detailed documentation in the future.

* modules/arch/<platform>.py : describes e.g. the scheduler, queues and node topology. Is needed for having the correct HPC headers (PBS, SLURM etc)

## Suite configuration: suite.ini

Once you have cloned the git repository, you will need to configure the suite.
First stop: the <suite>.ini file. While you may give it any name, the default is to place it in the root directory and call it <suite_name>.ini . There are some examples in the *ini* sub-directory.

The .ini file has a very simple structure:
* various sections start with [<section>]
* inside a section, there are variable declarations using "=" (or ":").

**Some warnings: **

* Indented lines are interpreted as continuations from the previous line. So make sure only to use indentation when you really need to.
* Especially in python2 wrong intentation can give errors.
* Don\'t put comments (#...) after an entry. Always use a new line.
* Don\'t use quotes for string values.
* All ini sections should be in the file, even if the section is empty.
* In Node Runner, the ECflow macro variable is "@" (not "&").
* Some sections are simply parsed and the variables exported to the whole suite. Therefore, e.g. all options in [local] would work just as well in [settings].

## [suite]
Basic suite definitions:

* suite_mode = oper | exp 
* realtime = yes | no
* *trigger* (to define an *external* trigger for the cycles)

## [platform]
Define the HPC platform:

* platform = <name> 
  + used in modules/<arch>/<platform>.py
  + requires include/settings_local_<platform>.h
* ncores_forecast , _pre , _pos , _screening, _minim , : number of cores by various tasks.
  + These *may* be written with some multiplications (e.g. <n_nodes> * <cores/node>)
* walltime_forecast, _pre, _pos : expected walltime


## [cycle]
Main cycle structure

* cycle_inc : cycle increment in hours (usually 3 or 6). Sub-hourly values not (yet) supported.
* forecast_length : max. lead time in hours
* runcycles : in some cases (e.g. RMI) only some cycles do full forecasts, while others are just part of the assimilation cycle. This variable lists the actual forecast runs as a comma-separated list.
* trigger_time : comma separated list of (UTC) times when cycles should start. Only used in "realtime" suites.
* cycle_labels : a coma separated list with alternatives names for the cycles (default is just "00", but some may prefer "midnight")
* trigger_labels : the labels that may be added in the exterior trigger defined above.


## [assimilation]
This section defines all aspects of assimilation. If there is no assimilation, only the first entry is required.
The options for observation types (comma separated) are not yet fully developped.

* assimilation = yes | no
* assim_upper = none | 3dvar
* assim_surface = canari
* obs_npool
* obstypes_upper = amdar , temp  ,gpssol,  radar
* obstypes_surface = synop
* coldstart = <yyyymmddrr>

## [model]
I know, some of these settings are just part of the namelist. But this helps Node Runner to define a default namelist name.

* MODEL = alaro | arome
* SURFACE = isba | surfex
* HYDROSTATIC = yes | no
* DFI = yes | no
* TIMESTEP : timestep in seconds
* NLEVELS
* CNMEXP
* DOMAIN:
  + monthly CLIM files are expected to be called <DOMAIN>_MM
* LBC_INC : coupling frequency in hours (usually 1 or 3)
* ENV_ALADIN : name of an include file with runtime environment
* NAMELIST_VERSION : the sub-directory with namelists to be sync\'ed to HPC
* NAMELIST_FORECAST, NAMELIST_PREPROC : default is formed from model specification, but you can also give a (space separated) list with partial namelist files.

[coupling]
* COUPLING = direct | <cnmexp> : either direct to incoming LBC\'s or nested into another suite.
* COUPLING_DOMAIN : defines the CLIM files
* LBC_INC : LBC increment in hours (often 3 or 1)
* LBC_LAG : LBC lag. Defaults to 0. At intermediate hours (3, 9, ...) an extra 3h lag may be added.
* COUPLING_MODEL (alaro, arome, arpege, ecmwf) Necessary to know how the LBC creation is done. NOT YET IMPLEMENTED!
* COUPLING_TEMPLATE : a template for finding coupling files. If not provided, a specialissed function /retrieve_coupling/ is expected. You can use YYYY, MM, DD, RR as patterns.


## [settings]

Some of these variables might also be defined in e.g. settings_local.h. But defining them in the .ini file gives you the possibility to have various alternative suites with the same 

* HPC_HOST : the name of your HPC server (e.g. cca)
* HPC_USER : default is to have the same user as on the ecflow server, but it can be different.
* SCRATCH
* SYNC_SCRATCH = yes | no  : this should be moved to [local], I guess.
* ECF_LOGHOST, ECF_LOGPORT : if you want to use an ECflow logserver on the HPC.
* MAIL_LIST : comma separated list of e-mail addresses. **NOTE** use a double "@@" symbol!
* BASEDIR = /@SCRATCH@/@HPC_USER@/ECF/@SUITE@ : location of the working directory on HPC. Note that you can use other ecflow macro values.
* HPC_HOMEBASE = /home/@HPC_USER@/ECF
* PACKDIR : path to the ALADIN "(root)pack". Must have a sub-directory "bin" with all executables.
* ECF_TRIES : this is in fact a standard ecflow macro. It may be useful to redefine it here.
* DATA_PATH : location (on HPC side) of climate files, Jb etc.
* DPATH_CLIM = @DATA_PATH@/clim
* DPATH_JB=@DATA_PATH@/JB : path to climate files (on HPC)
* DPATH_const
* DPATH_etc

## [local]
Local variables that should be defined for all tasks (e.g. if required by settings_local.h). Any variable mentioned here, will be defined. Some can have special importance.

* SUBMIT_OPT : if your schedule functions allows it, this can be used to add certain submit options. At RMI, the option "-r" is used for operational tasks, which are submitted to reserved nodes.

## [postproc]
This contains the post-processing tasks that will be run hourly, such as off-line FullPos or GRIB conversion.
Every non-indented entry defines a new post-processing task. The "value" assigned to it (here it is advised to use ":" rather than "=") is in fact a comma-seperated list of the local variables that need to be passed. You can use multiple lines for this, but then indentation is necessary.

As most of these tasks are fullpos tasks, the default script is supposed to be "interpolation.ecf", unless it is given explicitly. A task may also be required to wait for other to finish first.

* latlon : pp_domain=mylalo
* export : script=export, trigger=latlon, domain_list=mylalo, ARCH_PATH="where/to/export/"

## [products]
This contains tasks that are run when the forecast and post-processing are completed. This may include simply copying certain files (forecast output, cycle data...) to archive. The format is similar to [postproc].

# Loading the suite

Before running an experiment, you have to start the suite itself.

* Make sure you have an ecflow server running (ecflow_start)
* The script ./init_suite will do three things:
  1. compile the suite definition file <suite>.def from node_runner.py and <suite>.ini
  2. load the suite into ecflow_server (ecflow_client --load ...)
  3. start the suite (ecflow_client --begin ...)
  Note that the suite will not yet start running, because you haven't set a start date yet.

# First run

After installation, all cycles have "defstatus==complete". So they won\'t start running automatically.

To run a certain cycle (e.g. midnight):
The simplest way is to use the "restart" script. 

> ./restart 2020052700

will start the "midnight" cycle of 25 January 2020.

This little script does 3 things:
1. Set the date variable to a string 20200527 (exactly 8 characters, no space!)
2. set defstatus to queued
3. requeue the 00 cycle

If you have a "cycling" suite (cycle_inc > 0) the next cycle will be queued automatically. If you don't want that, you can add the option "-s" (before the date) for a single run. Actually, this option will (re-)define ENDDATE to stop the suite after just one cycle.

This assumes that first guess etc. are already in place (unless it's a downscaling suite). If you need a cold start, make sure the coldstart date is set correctly.


