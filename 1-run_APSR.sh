#!/bin/bash 

#autentication
source openrc.sh
#move to apsr_controller dir
cd /lib/python2.7/site-packages/nova/scheduler

#delete existing files 
rm -r shard_current_s.csv >  /dev/null 2>&1
rm -r shard_s.csv >  /dev/null 2>&1
rm -r shard_flavor_info.csv >  /dev/null 2>&1
rm -r shard_d.csv >  /dev/null 2>&1

#create relavent files 
touch shard_current_s.csv >  /dev/null 2>&1
touch shard_s.csv >  /dev/null 2>&1
touch shard_flavor_info.csv >  /dev/null 2>&1
touch shard_d.csv >  /dev/null 2>&1

#initialize files
echo "0" > shard_current_s.csv 
echo "1" > shard_s.csv 


#run apsr_controller 
python -c 'import apsr_controller ; apsr_controller.periodic_task() ' &