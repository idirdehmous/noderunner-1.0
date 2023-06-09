! Selection file for lat-long large domain
&NAMFPC
CFPDIR='PF', 
LTRACEFP=.F.,
NFPCAPE=5,
RFPCSAB=100., RFPCD2=10.,
CFPDOM(1)={cfpdom}
CFPFMT='LALON', NFPCLI=3,
CFPPHY(1)=
      'SURFIND.TERREMER','SURFGEOPOTENTIEL',
      'SURFTEMPERATURE','PROFTEMPERATURE',
      'SURFRESERV.EAU', 'PROFRESERV.EAU',
      'SURFRESERV.NEIGE',
@CFPCFU(1)= 
@      'SURFPREC.EAU.CON','SURFPREC.NEI.CON',
@      'SURFPREC.EAU.GEC','SURFPREC.NEI.GEC',
@      'ATMONEBUL.BASSE','ATMONEBUL.MOYENN','ATMONEBUL.HAUTE' ,
@      'ATMONEBUL.CONVEC','ATMONEBUL.TOTALE',
@      'SURFRAYT THER DE','SURFRAYT SOLA DE',
@      'SURFTENS.TURB.ZO','SURFTENS.TURB.ME',
@      'ATMOHUMI TOTALE' ,
CFPXFU(1)=
      'SURFNEBUL.BASSE' ,'SURFNEBUL.MOYENN','SURFNEBUL.HAUTE' ,
      'SURFNEBUL.CONVEC','SURFNEBUL.TOTALE',
      'SURFCAPE.MOD.XFU',
      'CLSU.RAF.MOD.XFU','CLSV.RAF.MOD.XFU',                           
      'CLSMINI.TEMPERAT','CLSMAXI.TEMPERAT',
CFP2DF(1)=
         'MSLPRESSURE', 'SURFPRESSION',
         'CLSVENT.ZONAL','CLSVENT.MERIDIEN','CLSTEMPERATURE',
         'CLSHUMI.RELATIVE',
         'SURFCAPE.POS.F00',
CFP3DF(1)=
         'GEOPOTENTIEL' ,'TEMPERATURE'  ,
RFP3H(1)=100.,200., 
RFP3P(1)=100000.,97500.,95000.,
          92500.,90000.,
          85000.,80000., 75000.,
          70000.,60000.,
          50000.,40000.,
          30000., 20000., 10000.,
RFP3I(1)=273.15,
/
