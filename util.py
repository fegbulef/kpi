#!/usr/bin/python3

"""*******************************************************************************
Created by:   Fiona Egbulefu (Contractor)

Created date: 25 June 2019

Description:  Generic script to store common modules:

              - setup_logger (logname, logfile)
              - get_logger (logname)
              - get_next_date (date, months, days)
              - get_month_start_end (month)

*******************************************************************************"""

import os
import time
import logging

try:
    import numpy as np
    import pandas as pd
    
except ImportError:
    print("Please install the python 'pandas' and 'xlrd' modules")
    sys.exit(-1)

from dateutil.relativedelta import relativedelta


#------------------------------------------------------------------------
# Return a date given start date and number of months and/or days to add 
# - returns date 
#------------------------------------------------------------------------
def get_next_date(dt, months, days):
    next_dt = dt
    
    if abs(months) != 0:
        next_dt += relativedelta(months=months)
    if abs(days) != 0:
        next_dt += relativedelta(days=days)

    return next_dt


#----------------------------------------------------------------------------
# Calculate start/end dates of a given month in MMM-YY format
# - returns start date (end of prev. month), end date (end of current month) 
#----------------------------------------------------------------------------
def get_month_start_end(month):

    month_dt_str = '-'.join(['1', month[:3], month[4:]]) 
    month_dt = pd.to_datetime(month_dt_str, format="%d-%b-%y")
                
    month_start = get_next_date(month_dt, 0, -1).date()    # end of previous month
    month_end = get_next_date(month_dt, 1, -1).date()      # end current month

    return month_start, month_end


#-------------------------------------------------------------
# Get logger
# - returns log handler 
#-------------------------------------------------------------
def get_logger(logname):

    return logging.getLogger(logname)


#-------------------------------------------------------------
# Setup logging
# - returns log handler 
#-------------------------------------------------------------
def setup_logger(logname, logfile):

    # delete existing log file
    log = os.path.join(os.getcwd(), logfile)
    if os.path.exists(log):
        os.remove(log)
        time.sleep(1)

    # setup log file
    logger = logging.getLogger(logname)
    logger.setLevel(logging.DEBUG)
    
    formatter = "%(asctime)s - %(levelname)s - %(filename)s - %(funcName)s: %(message)s"
    log_format = logging.Formatter(formatter, datefmt="%d-%b-%y %H:%M:%S")

    # setup file handler
    log_hndlr = logging.FileHandler(logfile, 'a')
    log_hndlr.setLevel(logging.DEBUG)
    log_hndlr.setFormatter(log_format)

    logger.addHandler(log_hndlr)

    return logger
    
