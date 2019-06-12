#!/usr/bin/python3

"""*******************************************************************************
Created by:   Fiona Egbulefu (Contractor)

Created date: 12 June 2019

Description:  Generic script to setup and create log with FileHandler

*******************************************************************************"""

import os
import time
import logging


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
    log_hndlr = logging.FileHandler(logfile)
    log_hndlr.setLevel(logging.DEBUG)
    log_hndlr.setFormatter(log_format)

    logger.addHandler(log_hndlr)

    return logger
    
