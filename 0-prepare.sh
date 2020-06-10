#!/bin/bash 

# download code
git clone 

#repalce code 
cp -r nova /lib/python2.7/site-packages/nova
rm -rf nova

#conf file 
cp APSR_CONFIG.txt /etc/nova/APSR_CONFIG.txt


reboot 