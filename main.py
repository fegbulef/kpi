#!/usr/bin/python3

"""*******************************************************************************
Created by:   Fiona Egbulefu (Contractor)

Created date: 12 April 2019

Description:  Main module that runs the KPI automation process.
              - Validate and setup input parameters
              - Calls autokpi module to process each KPI

*******************************************************************************"""

import argparse
import autokpi  # user defined modules


#*************#
#   M A I N   #
#*************#
    
parser = argparse.ArgumentParser()

# Get parameters
parser.add_argument("-kpi", type=str, help="List KPI system or codes separated by comma e.g JIRA,CDETS,..")
parser.add_argument("-fromxl", type=str, help="Import data from Excel? Y/N")
args = parser.parse_args()

importfromxl = False
kpi_list = args.kpi.split(',')
kpi_dict = autokpi.get_kpi_codes(kpi_list)
    
# Validate - kpi is required
if kpi_dict:

    if args.fromxl:
        if args.fromxl.upper() == 'Y': importfromxl = True

    autokpi.run_autokpi(kpi_dict, importfromxl)
    
else:
    
    print("\nERROR - KPI codes invalid or not supplied")
        

print("\nAll Done!\n")
