#!/bin/bash 

xppath=$PWD 

exp=$(basename  $xppath )


ecflow_client  --delete  /${exp}
ecflow_client  --load    ${exp}.def
ecflow_client  --begin   ${exp}

