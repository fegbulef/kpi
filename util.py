#!/usr/bin/python3

"""*******************************************************************************
Created by:   Fiona Egbulefu (Contractor)

Created date: 25 June 2019

Description:  Generic script to store common modules:

              - is_fyq_start(date)
              - get_next_date(date, +/-monthstoadd, +/-daystoadd)
              - get_month_start_end(monthyear)
              - get_kpi_months(start_dt, end_dt)
              - get_kpi_fyq_start_end(start_dt, end_dt)
              - get_month_fyq(months_df)
              - get_df_start_end_dates(df, datecol)
              - get_kpi_codes(kpi_list)
              - group_data_by_week(df, datecolumn, wkstart, wkend, keycolumn, countcolumn)
              - group_data_by_day_month(df, datecolumn, keycolumn, countcolumn)
              - sort_df_by_date(df, column, datefmt)
              - setup_logger(logname, logfile)
              - get_logger(logname)
              - get_xl_df(xlfile, xlsheetname=None)

*******************************************************************************"""

import os
import time
import logging
import warnings

import config   # user defined

try:
    import numpy as np
    import pandas as pd
    
except ImportError:
    print("Please install the python 'pandas' and 'xlrd' modules")
    sys.exit(-1)

from datetime import datetime, date
from dateutil.relativedelta import relativedelta


#------------------------------------------------------------------------
# Return True/False if reporting end of FYQ 
#------------------------------------------------------------------------
def is_fyq_start(dt):

    fyqs = config.autokpi["fyq"]

    dt_month = datetime.strftime(dt, format="%b")

    # if end date is in first quarter month
    if dt_month.upper() in [fyqs["Q1"][0], fyqs["Q2"][0], fyqs["Q3"][0], fyqs["Q4"][0]]:
        return True
    
    return False


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


#----------------------------------------------------------------------------
# Get range of months (dates) for given start/end dates
# - returns list (dates) 
#----------------------------------------------------------------------------
def get_kpi_months(start_dt, end_dt):

    if end_dt is None:      # default to end of next month
        dt = date.today()
        end_dt = get_next_date(datetime(dt.year, dt.month, 1), 1, -1)
    
    if start_dt is None:    # default from config
        filter_mth = config.autokpi["months_to_plot"]
        start_dt = get_next_date(datetime(end_dt.year, end_dt.month, 1), filter_mth, 0)

    months = np.arange(start_dt, end_dt, np.timedelta64(1, 'M'), dtype='datetime64[M]')    

    # convert to df and reformat: MMM-YY
    months_df = pd.DataFrame(months, columns=["Months"])
    months_df["Months"] = pd.to_datetime(months_df["Months"]).dt.strftime("%b-%y")

    months = [m[0] for m in months_df.values.tolist()]

    return months

    
#----------------------------------------------------------------------------
# Get start end of FYQs to plot
# - returns start_fyq, end_fyq 
#----------------------------------------------------------------------------
def get_kpi_fyq_start_end(start_dt, end_dt):

    if end_dt is None:      # default to end of next month
        dt = date.today()
        end_dt = get_next_date(datetime(dt.year, dt.month, 1), 1, -1)

    if start_dt is None:    # default from config
        fyq_start = config.autokpi["fyq_start"].split('/')
        start_dt = datetime(int(fyq_start[2]), int(fyq_start[1]), int(fyq_start[0]))

    max_fyq = config.autokpi["fyqs_to_plot"]

    # work out number of fyqs between start and end dates
    t = relativedelta(end_dt, start_dt)
    t_mths = (t.years*12) + t.months
    qtrs = (t_mths/3) - max_fyq

    if qtrs > 0:
        months_to_add = 3 * (qtrs if qtrs >= 1 else 1)
        start_dt = get_next_date(datetime(start_dt.year, start_dt.month, start_dt.day), months_to_add, 0)


    return start_dt, end_dt


#----------------------------------------------------------------------------
# Setup financial quarter for each corresponding month
# - returns list (FYQs) 
#----------------------------------------------------------------------------
def get_month_fyq(months):

    fyq = ['']* len(months)
    
    for i, month in enumerate(months):
        
        mth, yr = month.split('-')      # separate into MMM and YY 
        
        for qtr, qtr_months in config.autokpi["fyq"].items():
            if mth.upper() in qtr_months:
                int_yr = int(yr)
            
                if qtr == 'Q1' or (qtr == 'Q2' and mth.upper() != 'JAN'):
                    int_yr += 1

                fyq_str = str.join('', ['FY', str(int_yr), ' ', qtr])
                fyq[i] = fyq_str
                break
            
    return fyq

#-------------------------------------------------------------
# Return start/end dates of DataFrame date column 
#-------------------------------------------------------------
def get_df_start_end_dates(df, datecol):

    # convert df dates to datetime
    dt = pd.to_datetime(str(min(list(df[datecol].values))))
    start_dt = datetime.strptime(dt.strftime("%d/%m/%Y"), "%d/%m/%Y")
    dt = pd.to_datetime(str(max(list(df[datecol].values))))
    end_dt = datetime.strptime(dt.strftime("%d/%m/%Y"), "%d/%m/%Y")

    return start_dt, end_dt


#-------------------------------------------------------------
# Parse kpi list and return tool with selected kpi codes
# - returns tool/kpi (dict) 
#-------------------------------------------------------------
def get_kpi_codes(kpi_list):

    out_kpi = {}
    tooldict = config.autokpi["tools"]

    for code in kpi_list:
        if code in out_kpi.keys(): continue

        # tool selected - add tool and all associated kpi codes
        if code in tooldict:
            out_kpi[code] = []      
            for k in tooldict[code]["kpi"].keys():      
                out_kpi[code].append(k)

        # kpi code input - get associated tool and add kpi
        else:      
            for tool in tooldict:
                 if code in tooldict[tool]["kpi"].keys():
                    if out_kpi.get(tool):
                        if not code in out_kpi[tool]:   # kpi already saved
                            out_kpi[tool].append(code)
                    else:
                        out_kpi[tool] = []
                        out_kpi[tool].append(code)
                    break
    
    return out_kpi


#-------------------------------------------------------------
# Group data by day/month
# - returns dict
#-------------------------------------------------------------
def group_data_by_day_month(df, keydate, keycol, keycnt):

    grp_data = {}

    for i in df.index:
        dt = df[keydate][i]
        key = df[keycol][i]

        # check for valid releaseno's
        if keycol == "ReleaseNo":
            if not key.replace('.','').isdigit() \
               or key.split('.')[0] == '0':         # not a valid number
                continue

        if not dt in grp_data:          # by day/month
            grp_data[dt] = {}
        if not key in grp_data[dt]:     # by product / releaseno
            grp_data[dt][key] = 0
                
        grp_data[dt][key] += df[keycnt][i]

              
    return grp_data


#-------------------------------------------------------------
# Grroup data by week
# - returns Dataframe structure
#-------------------------------------------------------------
def group_data_by_week(df, keydate, wkstart, wkend, keycol, keycnt):

    grp_data = {}
   
    for idx, wk in enumerate(wkstart):      # by week
        if not wk in grp_data:
            grp_data[wk] = {}

        for i in df.index:
            dt = df[keydate][i].date()
            key = df[keycol][i]

            if keycol == "ReleaseNo":
                if not key.replace('.','').isdigit() \
                   or key.split('.')[0] == '0':         # not a valid number
                    continue
            
            if not key in grp_data[wk]:    # by Product / ReleaseNo
                grp_data[wk][key] = 0
        
            if (dt >= wk.date()) and (dt <= wkend[idx].date()):
                grp_data[wk][key] += df[keycnt][i]


    return grp_data


#-------------------------------------------------------------
# Returned sorted dataframe by date column
#-------------------------------------------------------------
def sort_df_by_date(df, column, datefmt):

    dates = pd.to_datetime(df[column], format=datefmt, errors='coerce')
    df_sorted = df.assign(dates=dates)
    df_sorted.sort_values("dates", ascending=True, inplace=True)
    
    df_sorted.drop("dates", axis=1, inplace=True)

    return df_sorted


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
        try:
            os.remove(log)
            time.sleep(2)
        except Exception as e:
            print("WARNING - Could not delete {}; Log will be appended.".format(logfile))

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


#-------------------------------------------------------------
# Create Dataframe from Excel
# - returns Dataframe 
#-------------------------------------------------------------
def get_xl_df(xlfile, xlsheetname=None):

    xldf = None

    # import Excel data from specific workbook and sheet; ignore xlrd warnings
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
        warnings.filterwarnings("ignore", category=DeprecationWarning)

        if xlsheetname:
            xldf = pd.read_excel(xlfile, sheet_name=xlsheetname)
        else:
            xldf = pd.read_excel(xlfile)
            
    return xldf
