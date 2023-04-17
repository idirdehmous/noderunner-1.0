# BMATRIX CREATION in NODE RUNNER

@@__LAST UPDATE : 27-10-2021
@@__R.M.I
@@__I.DEHMOUS 


By setting /suite_type = bmatrix/ node runner is also a tool to compute an estimation of the B matrix using members from ensemble ARPEGE forecast ( EDA method )
* The first stage consists on the estimation of a firt B using ensemble downscaling 
 from the ARPEGE/IFS 
* The second stage is to compute the second B using the local perturbed observations 


# ECFLOW SERVER SIDE .        
USAGE :
STEP 1 :  
Enter in your ecflow home directory ( ~/ECF ) and decompress the file "bxflow.tar"

The directory in ecflow server is orgnized as follows  : 
   bxflow/bin         --->  bash and python scripts needed for jobs submission on HPC  
         /nam         --->  the different namelists
         /etc         --->  extra files ( ioassign , POLYNOMES ISBA ...etc)
         /include     --->  *.h files 
         /ini         --->  Contains the configuration .ini file to be used ( bxflow.ini)   
         /tmp         --->  Temporary jobs to be submitted on the HPC  
         /scr         --->  ecf  files   ( *.ecf )
   
STEP 2 :     
To generate the definition for the B matrix suite definition 
   -Edit the file ini/bxflow.ini  and set the different variables according 
    to your environement 
   -Run the command   
    python  bxflow.py   ini/bxflow.ini   
  
   -Load and start the suite using the script  
    ./reload   SUITE.def    ( by default the suite name is bxflow !)



# HPC SIDE   
Once the suite is loaded, a working environement is created on HPC account. 
It creates a suite called "bxflow" under the root directory ( BASEDIR ) you set in the ".ini" file  
The different "etc file , namelists , binary and clim files" are copied and/or linked ( rsync ! ) in the HPC 

    The HPC running environement is orgnized as follows : 
                   BASEDIR/bin            ---> bash and python scripts needed for jobs submission on HPC
                          /nam            ---> namelists  
                          /inp/           ---> const , clim and ecoclimap files  
                          /packbin        ---> your pack binaries  
                          /lbc            ---> the forecast files comming from coupling model (ALARO/ALADIN).
                                               For this version these files are in a path you can set in ini file 
                                               ALD_PATH variable 
                          /out            ---> the different AROME coupling ,forecast are saved there  
                          /log            ---> log files for ecflow  
                          /work           ---> the working directory contains ( ENS_SU , ENS_DA ) each part has its own workdir

# NOTE ( important !)
The different parts of the global suite are organized as :
bxflow/ENS_SU                     ( 1st B in spin up mode  )
      /member01/rundates  ...     ( members and families     )
      /member02/rundates  ... 
      ...
      /femars                     (femars task )
      /festat                     (festat task )

      /ENS_DA                     (2nd B with EDA        )
      /member01/cycle/runtime     ( members and cycles   )
      /member02/cycle/runtime
      ...

The first tasks ( coupling_atmo and coupling_surf) will look for the lbc ( ALADIN/ALARO files  )
which are assumed to be downscaled from the ARPEGE/IFS  members.

To avoid any crashes during suite start, be sure that the ALADIN/ALARO files are all available following a template like:
/PATH/TO/LBC/@MEMBER@/YYYY/MM/DD/RR/ICMSHARPE+00HH
where @MEMBER@ is an ecFlow macro variable that will be available to the script, and YYYY, MM, DD, RR, HH will be explicitly replaced by the correct run date and leadtime.

