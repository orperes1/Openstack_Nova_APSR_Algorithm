==============
OpenStack Nova - APSR Algorithm
==============

.. Change things from this point on


OpenStack Nova provides a cloud computing fabric controller, supporting a wide variety of compute technologies. 
APSR – an efficient parallel random resource management algorithm that requires information only from a small number of hosts and dynamically adjusts the degree of parallelism to provide provable decline ratio guarantees

Implementation copywriter: Or Peres - pereo@post.bgu.ac.il ,Liron Cohen- cohenlir@post.bgu.ac.il

This is implementation of article "Parallel Virtual Machine Placement with Provable Guarantees" Supervisors:	Dr. Scalosub Gabriel Dr. Einziger Gil

Note: APSR scheduler replace the filter schedulers

Get Started:
---------

1. Start by cloning this project.
2. Run scripts 
 0-prepare.sh
  This command is to prepare the installed OpenStack environment before the 1st benchmarking. It replace the nova code to support         the APSR vertion. The scrip also create the configuration file.
 1-run_APSR.sh
  This start the APSR controller 

Configuration File:
---------
You can find all APSR configuration at - /etc/nova/APSR_CONFIG.txt

 [DEFAULT]
 
 #determine how often the APSR controller will work
 
 INTERVAL_SIZE = 10


 # parameters for APSR algorithm estimate K factor
 
 ALPHA = 0.1

 # APSR's target decline ratio (0.1)
 
 EPSILON = 0.1


 # Set the APSR type, 0 - APSR , 1- APSR AVG

 TYPE = 0


 #Budget for overall number of queries

 BUDGET_SIZE = 100


 #APSR is allow to open up to MAX_SCHDULERS schedulers

 MAX_SCHDULERS = 100


Debug:
---------
In order to debug the project you can use-

* APSR log file -  /lib/python2.7/site-packages/nova/APSR_CONTROLLER.log

* Nova logs - /var/log/nova/*
README.rst
