#! /usr/bin/env python3
# Create a selection-namelist file by reading the specifications from the *.ini file
# Create the part for the common namelist (fort.4)
# May 2020 Michiel Van Ginderachter
# January 2021 adapted Alex Deckmyn

import os 
import sys
import ast
import numpy as np
try:
  import configparser
except ImportError:
  print("Warning: for python2 you need to install the backported configparser module.")
  print("Standard py2 ConfigParser may not work correctly.")
  import ConfigParser as configparser


# get the init file from command line
# > python createFposNam.py lambert.ini 
nargv = len(sys.argv)
if nargv > 1 :
  ini_file = sys.argv[1]
  prefix   = os.path.splitext(ini_file)[0]
  log_file = os.path.splitext(ini_file)[0] + ".log"
else :
  print("You need to provide a <domaintype>.ini file!\n")
  print("Usage:")
  print("> python pyPosNam.py <domaintype>.ini\n")
  quit()

if nargv > 2 :
  prefix = sys.argv[2]
#else :
  ## better default: take name of ini file and strip the ".ini"
#  prefix = "fp"

#ini_file='lambert.ini'
print("ini_file = " + ini_file)
print("prefix = " + prefix)

if not os.path.exists(ini_file):
  print("ERROR: file " + ini_file + " not found!\n")
  exit()


# - pre-defined dictionaries
configType  = { 'phy':'cfpphy','2d':'cfp2df','cfu':'cfpcfu','xfu':'cfpxfu','3d':'cfp3df' }
nameType    = { 'phy':'CFPPHY(1)=', '2d':'CFP2DF(1)=','cfu':'!00CFPCFU(1)=',
      'xfu':'CFPXFU(1)=','3d':'CFP3DF(1)=' }
configLevel = { 'model' : 'nrfp3s','pressure' : 'rfp3p' ,
      'height' : 'rfp3h' ,'vorticity' : 'rfp3pv' ,'temperature' : 'rfp3i' }
nameLevel   = { 'model' : 'NRFP3S(1)=', 'pressure' : 'RFP3P(1)=',
      'height' : 'RFP3H(1)=', 'vorticity' : 'RFP3PV(1)=', 'temperature' : 'RFP3I(1)=' }


# - prepare dictionaries (needs seperate dictionaries for seperate &NAM*** because in python 2.* the order of the dictionary entries is not maintained.)
phyType = {'phy' : 'CLPHY=', 'cfu' : '!00CLCFU=', 'xfu' : 'CLXFU=' }
nameDom = {'phy' : 'CLDPHY(1', 'cfu' : '!00CLDCFU(1', 'xfu' : 'CLDXFU(1', '2d' : 'CLD2DF(1', '3d' : 'CLD3DF(1' } 
f2dType  = {'2d' : 'CL2DF=' }
f3dType  = {'model' : '&NAMFPDYS\n', 'pressure' : '&NAMFPDYP\n', 'height' : '&NAMFPDYH\n',
      'vorticity' : '&NAMFPDYV\n', 'temperature' : '&NAMFPDYI\n' }

def make_namfpd(config, namelist, domains, latlon) :
  # FIXME: it is not possible to add extra keys to NAMFPD...
  # make sure "domains" is a list, so for lambert grids ['domain'], not 'domain'
  namelist.write('&NAMFPD\n')
# -- accepted keys
  keys=['nlon','nlat','nfplux','nfpgux','rlonc','rlatc','rdelx','rdely','nfpbzong','nfpbzonl']
# - loop over domains to get the domain info
# - NOTE: NFPLUX/NFPGUX can not be written as array(1). Must be scalar
  for idx,domain in enumerate(domains):
    for key in keys:
      if key in config[domain].keys():
        if latlon :
          namelist.write(key.upper() +'('+ str(idx+1) + ')=' + config.get(domain,key) + '\n')
        else :
          namelist.write(key.upper() + '=' + config.get(domain,key) + '\n')
  namelist.write('/\n')

def make_namfpg(config, namelist, domains, latlon) :
  # TODO: make the (A,B)-level list a bit nicer? Now it is an extremely long single line
  nfplev = config.get(domains[0], 'nfplev')

  namelist.write('&NAMFPG\n')
  namelist.write('NFPLEV=' + str(nfplev) + '\n')
  namelist.write('FPVALH(0:' + str(nfplev) + ')='  + ','.join(
    map(str.strip,ast.literal_eval(config.get('General','fpvalh'))[str(nfplev)].split(','))) + '\n')
  namelist.write('FPVBH(0:' + str(nfplev) + ')='  + ','.join(
    map(str.strip,ast.literal_eval(config.get('General','fpvbh'))[str(nfplev)].split(','))) + '\n')
  if not latlon :
    keys=['fplon0','fplat0','nfpmax','nmfpmax']
    for key in keys:
      if key in config[domains[0]].keys():
        namelist.write(key.upper() + '=' + config.get(domains[0],key) + '\n')
  namelist.write('/\n')

def make_namfpc(config, namelist, domains, latlon) :
#  - write general fpos settings
  namelist.write('&NAMFPC\n')
  namelist.write('CFPFMT="' + config.get(domains[0],'cfpfmt') + '"\n')
  for key in config['General'].keys():
    if not (key == 'fpvalh' or key == 'fpvbh' or key == 'cfpfmt'):
      namelist.write(key.upper() + '=' + config.get('General',key) + '\n')
  
  allLevels = { }
  allFields = { }
# - loop over domains adding all required fields and levels to the above lists
  for idx,domain in enumerate(domains):
# - write domain name
    namelist.write('CFPDOM(' + str(idx+1) + ')="' + domain + '"\n')
    for ctype in configType.keys():
      if ctype != '3d':
        fields = list(map(str.strip,config.get(domain,configType[ctype]).split(",")))
        # fields = [ field for field in map(unicode.strip,config.get(domain,configType[ctype]).split(",")) ] 
      else:
        fields = []
# - if 3D fields loop of the type of levels
        for ltype in configLevel.keys():
          # TODO: replace "all" by a full list of model levels?
          # FIXME: allow for missing entries (fallback={}) ??
          levdict = ast.literal_eval(config.get(domain,ltype + '_levels'))
          levels = [ float(item) for sublist in [ a.split(',') for a in levdict.values() ] for item in sublist ]
          fields.extend(list(map(str.strip, levdict.keys( ))))
          if ltype in allLevels:
            allLevels[ltype].extend(levels)
          else:
            allLevels[ltype] = levels
      if ctype in allFields:
        allFields[ctype].extend(fields)
      else:
        allFields[ctype] = fields

  for ctype,values in allFields.items():
    allFields[ctype] = np.unique(np.array(values)).tolist()
    namelist.write(nameType[ctype] + ','.join(list(map(lambda x: '"%s"'%x,allFields[ctype]))) + '\n')
  for ltype,values in allLevels.items():
    temp = np.unique(np.array(values))
    if len(temp) == 0 :
#      print(ltype + " empty\n")
      continue
    if ltype == 'pressure':
      temp[::-1].sort()
    else:
      temp.sort()

    allLevels[ltype] = temp.tolist()
    # in the namelist, we need to multiply pressure levels by 100
    if ltype == 'pressure':
      temp = temp * 100 # temp is an nparray, for list: map(lambda x: 100*x,temp)
    if ltype == 'model':
      namelist.write(nameLevel[ltype] + ','.join(list(map(lambda x: str(int(x)),temp))) + '\n')
    else:
      namelist.write(nameLevel[ltype] + ','.join(list(map(str,temp))) + '\n')

  namelist.write('/\n')
  return(allFields, allLevels)

def make_selection(config, selection_name, domains, allFields, allLevels) :
  selection = open(selection_name, 'w')
  selection.write('&NAMFPPHY\n')
  for ptype,namel in phyType.items():
    selection.write(namel + ','.join(list(map(lambda x: '"%s"'%x,allFields[ptype]))) + '\n')
    seldoms =  [ [domain for domain in domains if field in map(str.strip,config.get(domain,configType[ptype]).split(","))] for field in allFields[ptype] ]
    selection.write(nameDom[ptype] + ')=' + ','.join(list(map(lambda x: '"%s"'%x,[ ':'.join(doms) for doms in seldoms ]))) + '\n')
  selection.write('/\n')
  
  selection.write('&NAMFPDY2\n')
  for ctype,namel in f2dType.items():
    selection.write(namel + ','.join(map(lambda x: '"%s"'%x,allFields[ctype])) + '\n')
    seldoms =  [ [domain for domain in domains if field in map(str.strip,config.get(domain,configType[ctype]).split(","))] for field in allFields[ctype] ]
    selection.write(nameDom[ctype] + ')=' + ','.join(list(map(lambda x: '"%s"'%x,[ ':'.join(doms) for doms in seldoms ]))) + '\n')
  selection.write('/\n')

  ctype = '3d'
  for ltype,namel in f3dType.items():
    selection.write(namel)
    # FIXME: should not crash if e.g. vorticity_levels entry is missing
    # if ltype+'_levels' not in config.items(domain) :
    #   fields = []
    fields = [ ast.literal_eval(config.get(domain,ltype + '_levels')).keys() for domain in domains ]
    fields = np.unique(np.array([item.strip() for sublist in fields for item in sublist])).tolist()
    if len(fields) > 0 :
      selection.write('CL3DF=' + ','.join(map(lambda x: '"%s"'%x,fields)) + '\n')
              # BUG: in the next line, fields contains the stripped field name, so maybe not equal to the actual key
              #      if the key has a " " included, this will NOT work correctly.
      field_domain_levels = [ [ ast.literal_eval(config.get(domain,ltype + '_levels'))[field].split(',') for domain in domains if field in ast.literal_eval(config.get(domain,ltype + '_levels')).keys()] for field in fields ]
      field_levels=[ np.sort(np.unique(np.array(list(map(float,[levels for sublist in domain_levels for levels in sublist ]))))).tolist() for domain_levels in field_domain_levels ]
      for idx,levels in enumerate(field_levels):
        if ltype == 'pressure':
          levels.reverse()
        print("lev")
        print(levels)
        indices = list(map(lambda x: str(allLevels[ltype].index(x)+1), levels))
        selection.write('IL3DF(1:' + str(len(indices)) + ',' + str(idx+1) + ')=' + ','.join(indices) + '\n')
        cld3df = []
        for level in levels:
          temp = []
          for domain in domains:
            if fields[idx] in list(map(str.strip,ast.literal_eval(config.get(domain,ltype + '_levels')).keys())):
              # BUG: in the next line, fields[idx] is the stripped field name, so maybe not equal to the actual key
              #      if the key has a " " included, this will NOT work correctly.
              if level in list(map(float,ast.literal_eval(config.get(domain,ltype + '_levels'))[fields[idx]].split(','))):
                temp.append(domain)
          cld3df.append(":".join(temp))
        selection.write('CLD3DF(1:' + str(len(indices)) + ',' + str(idx+1) +')=' + ','.join(map(lambda x: '"%s"'%x,cld3df)) + '\n')  
    selection.write('/\n')
# - TODO: complete this section
  selection.write('&NAMFPDYT\n')
  selection.write('/\n')
  selection.write('&NAMFPDYF\n')
  selection.write('/\n')
  selection.close()


def make_xxt(domains, nfplev, latlon, prefix="fp") :
  # NOTE: the current version assumes that the same lambert grid is not used
  #       with two different nfplev values.
  if latlon :
    namelist_name = prefix + '_base_latlon_' + str(nfplev) + 'l.nam'
    selection_name = prefix + '_sel_latlon_' + str(nfplev) +'l.nam'
  else :
    # for lambert grid, there is only 1 domain anyway
    namelist_name = prefix + '_base_' + domains[0] + '.nam'
    selection_name = prefix + '_sel_' + domains[0] +'.nam'

  # add to the list of jobs
#  fpjobs=open(prefix + '.jobs','a')
#  fpjobs.write(namelist_name + ' ' + selection_name + '\n')
#  fpjobs.close()

  # write the main namelist
  namelist = open(namelist_name, 'w')
  make_namfpd(config, namelist, domains, latlon)
  make_namfpg(config, namelist, domains, latlon)
  allFields,allLevels = make_namfpc(config, namelist, domains, latlon)
  namelist.close()
 
  # now the selection file
  make_selection(config, selection_name, domains, allFields, allLevels)

############################################################################

#if os.path.exists(prefix + '.jobs'):
#  os.remove(prefix + '.jobs')

config=configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
#keep key names in upper case
config.optionxform = str
config.read(ini_file)
domains=[sect for sect in config.sections() if not sect in ['General', 'Common'] ]

# every section in the ini file is a domain (except General)
# Lambert domains are treated directly
# Latlon domains are first grouped by nfplev
levellist=[]
outlog=open(log_file, "w")
for domain in domains:
  nfplev = config[domain]['nfplev']
  if nfplev not in levellist and config[domain]['cfpfmt'] == 'LALON':
    levellist.append(nfplev)
    outlog.write("LATLON lev " + str(nfplev) + " : " + domain)
  if config[domain]['cfpfmt'] == 'LELAM' :
    outlog.write("LELAM : " + domain)
    make_xxt(domains=[domain], nfplev=nfplev, latlon=False, prefix=prefix)

for nfplev in levellist:
  domainlist=[]
  for domain in domains:
    if config[domain]['nfplev'] == nfplev and config[domain]['cfpfmt'] == 'LALON':
      domainlist.append(domain)
  make_xxt(domains=domainlist, nfplev=nfplev, latlon=True, prefix=prefix)

outlog.close()

