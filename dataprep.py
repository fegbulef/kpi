#!/usr/bin/python3

"""*************************************************************************
Created by:   Fiona Egbulefu (Contractor)

Created date: 16 April 2019

Description:  Functions to filter data, reformat dates and group data 
              - Monthly count of open/closed defects
              - Quarterly (FYQ) count of open/closed defects
              - MTTR calculations

**************************************************************************"""

import sys

try:
    import xlrd
    import pandas as pd
    import numpy as np

except ImportError:
    print("Please make sure the following modules are installed: 'pandas'; 'xlrd'")
    sys.exit(-1)

from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# user defined module
import util
import config   


# set CMM release date
CMM_RELDATE = pd.to_datetime("31/07/2017", format="%d/%m/%Y").date()

kpilog = util.get_logger(config.autokpi["logname"])


#-----------------------------------------------
# Create structure to hold plot months
# - returns DataFrame structure 
#-----------------------------------------------
def get_plot_months(start_dt, end_dt):

    months = util.get_kpi_months(start_dt, end_dt)
    
    # get corresponding fyq for each month
    fyq = util.get_month_fyq(months)
 
    #df = months_df.to_frame()
    months_df = pd.DataFrame(months, columns=["Months"])
    months_df = months_df.assign(FYQ=fyq)

    months_df.reset_index(inplace=True)

    if 'index' in months_df.columns:
        months_df.drop('index', axis=1, inplace=True)    # index column created by assign

    return months_df


#--------------------------------------------------
# Filter data and date - date range set in config
# - returns DataFrame structure 
#--------------------------------------------------
def filter_df_by_date(df, toolcfg, start_dt, end_dt):
   
    df_start = df[toolcfg["open_column"]] >= start_dt
    df_end = df[toolcfg["open_column"]] <= end_dt
    df_filtered = df[df_start & df_end]

    return df_filtered


#-------------------------------------------------
# Formatt Open/Close date columns
# - returns DataFrame structure 
#-------------------------------------------------
def reformat_df_dates(df, toolcfg, importfromxl):

    open_col = toolcfg["open_column"]
    closed_col = toolcfg["closed_column"]
    if importfromxl:
        datefmt = toolcfg["xldatefmt"]
    else:
        datefmt = toolcfg["apidatefmt"]

    cur_dt = pd.datetime.now()

    # format open/closed columns as date
    opendates = pd.to_datetime(df[open_col], format=datefmt)
    df_formatdate1 = df.assign(OpenDate=opendates)                          # new OpenDate column

    closeddates = pd.to_datetime(df_formatdate1[closed_col], format=datefmt, errors='coerce')
    closeddates_fill = closeddates.fillna(cur_dt)
    df_formatdate2 = df_formatdate1.assign(ClosedDate=closeddates_fill)     # new ClosedDate column

    # reformat open/closed dates as MMM-YY
    open_mmmyy = opendates.dt.strftime("%b-%y")
    closed_mmmyy = closeddates_fill.dt.strftime("%b-%y")

    df_reformat = df_formatdate2.assign(ClosedMonth=closed_mmmyy, OpenMonth=open_mmmyy)

    if 'index' in df_reformat.columns:
        df_reformat.drop('index', axis=1, inplace=True)    # index column created by assign
        
    kpilog.debug("Reformat dates.....")
    
    return df_reformat


#----------------------------------------------------------------------------
# MTTR base calculations
# For each issue, work out number of days issue has been open in each month
# - returns DataFrame structure 
#----------------------------------------------------------------------------
def get_mttr_days(df, months_fyq_df, toolcfg):

    id_col = toolcfg["id_column"]
   
    # initialise calcs
    mttr_df = months_fyq_df[["Months","FYQ"]]
    df_calc = [0] * len(months_fyq_df)

    df_data = df[[id_col, "OpenDate", "ClosedDate"]]

    # get open days per month for each issue
    for i in df_data.index:
        
        df_id = df_data[id_col][i]
        dt_open = df_data["OpenDate"][i].date()
        dt_closed = df_data["ClosedDate"][i].date()

        if dt_open == dt_closed: continue    # open/closed same day

        for j in months_fyq_df.index:
            daysopen = 0
            
            month_start, month_end = util.get_month_start_end(months_fyq_df.Months[j])
            
            if (dt_open > month_end) or (dt_closed <= month_start): continue
           
            # calculate days open in month
            if dt_open >= month_start:
                if dt_closed <= month_end:
                    daysopen = (dt_closed - dt_open).days
                else:
                    daysopen = (month_end - dt_open).days
            else:
                if dt_closed <= month_end:
                    daysopen = (dt_closed - month_start).days
                else:
                    daysopen = (month_end - month_start).days

            df_calc[j] += daysopen
            

    mttr_df["MTTR"] = df_calc
    
    
    return mttr_df
            

#---------------------------------------------------------------------------------------
# MTTR product calculations
# Calculations are based on a period of 3 months after the first 2 months calculations
# - returns DataFrame structure
#---------------------------------------------------------------------------------------
def get_mttr_calcs(df, pcode=None):

    mttr_calc = [0] * len(df)

    days = 0
    mttr = 0
    closed_cnt = 0

    mttridx = 0
    
    for i in df.index:
        data = df[df.Months == df.Months[i]]
        if data.empty: continue

        month_start, month_end = util.get_month_start_end(data.iloc[0].Months)

        # for CMM, start mttr calc from release date
        if pcode == 'CMM':
            if month_start < CMM_RELDATE: continue
       
        # sum values rolling forward
        days += (month_end - month_start).days
        closed_cnt += data.iloc[0].ClosedCnt
        mttr += data.iloc[0].MTTR

        # remove calculations of 4th month after each 3 month period
        if i > 2 and mttridx > 2:
            dfx = df.iloc[i-3]
            start, end = util.get_month_start_end(dfx.loc["Months"])
            days -= (end - start).days
            closed_cnt -= dfx.loc["ClosedCnt"]
            mttr -= dfx.loc["MTTR"]

        mttridx += 1
            
        # calculate mttr
        if closed_cnt == 0:
            mttr_calc[i] = round(mttr * days)
        else:
            mttr_calc[i] = round(mttr / closed_cnt)


    # update MTTR column with calculated values
    df_updated = df[["Months","FYQ"]]
    df_updated = df_updated.assign(MTTR=mttr_calc)

    if 'index' in df_updated.columns:
        df_updated.drop('index', axis=1, inplace=True)    # index column created by assign

    
    return df_updated


#---------------------------------------------------------
# Assign mttr values for each FYQ
# - returns DataFrame 
#---------------------------------------------------------
def get_mttr_fyq(df):

    mttr = {}
    mttr_fyq_df = pd.DataFrame(columns=["FYQ","MTTR"])

    for i in df.index:
        if df.FYQ[i] in mttr: continue

        qtr_yr, qtr = df.FYQ[i].split()
        mth, yr = df.Months[i].split('-')

        # find end of quarter mttr value
        if mth.upper() == config.autokpi["fyq"][qtr][2]:
            mttr[df.FYQ[i]] = df.MTTR[i]

    # create dataframe 
    mttr_fyq_df["FYQ"] = list(mttr.keys())
    mttr_fyq_df["MTTR"] = list(mttr.values())

    mttr_fyq_df.set_index("FYQ", inplace=True)

    
    return mttr_fyq_df
            

#---------------------------------------------------------
# Calculate open defects boostrapping open/closed counts
# - returns list of values
#---------------------------------------------------------
def get_open_defects_count(df):

    df_open_defects = [0] * len(df)
    df_current_open = df["OpenCnt"] - df["ClosedCnt"]

    for i, cnt in df_current_open.items():
        if i == 0:
            df_open_defects[i] = cnt
        else:
            df_open_defects[i] = df_open_defects[i-1]+cnt

      
    return df_open_defects
            

#------------------------------------------------------------
# Get data for specified product filtered by dates
# - returns DataFrame structure 
#------------------------------------------------------------
def get_product_data(df, product, toolcfg, kpi):

    # identify product type from first part of column e.g. CLIENT-7456
    pcol = toolcfg["product_column"]
    product_selection = df[pcol].str.split('-').str[0] == product

    df_product = df[product_selection]
    if df_product.empty:
        return None    # no data for product

 
    return df_product
            

#--------------------------------------------------
# Group data to get Open/Closed counts
# - returns DataFrame structure 
#--------------------------------------------------
def get_product_counts(df):

    # group open/closed for project 
    df_open_grp = df[["OpenMonth"]].groupby(["OpenMonth"]).size().reset_index(name='OpenCnt')
    df_open_grp.set_index('OpenMonth', inplace=True)
    df_closed_grp = df[["ClosedMonth"]].groupby(["ClosedMonth"]).size().reset_index(name='ClosedCnt')
    df_closed_grp.set_index('ClosedMonth', inplace=True)


    return df_open_grp, df_closed_grp


#--------------------------------------------------
# Merge MTTR plot data
# - returns DataFrame structure
#--------------------------------------------------
def merge_mttr(df, mttr_df, mttrAll=False):

    if mttrAll:
        df.drop('MTTR', axis=1, inplace=True) 
        
    mttr_df.reset_index(inplace=True)
    mttr_df.set_index('Months', inplace=True)
    
    df_merged = pd.merge(df[["FYQ", "Months", "OpenCnt", "ClosedCnt", "OpenDefects"]],
                            mttr_df["MTTR"],
                            on="Months")

    df_merged.reset_index(inplace=True)


    return df_merged


#--------------------------------------------------
# Merge all data ready for plotting
# - returns DataFrame structure 
#--------------------------------------------------
def get_plot_data(df_open_grp, df_closed_grp, mttr_df, months_fyq_df):

    df_grouped = months_fyq_df

    # merge open/close counts into one DF
    df_grouped = pd.merge(df_grouped[["FYQ", "Months"]],
                            df_open_grp["OpenCnt"],
                            left_on="Months",
                            right_on="OpenMonth",
                            how="outer",
                            indicator=False)
     
    df_grouped = pd.merge(df_grouped[["FYQ", "Months", "OpenCnt"]],
                            df_closed_grp["ClosedCnt"],
                            left_on="Months",
                            right_on="ClosedMonth",
                            how="outer",
                            indicator=False)

    df_grouped.reset_index(inplace=True)
    
    # set open/closed count to zero if null
    df_grouped['OpenCnt'].fillna(0, inplace=True)
    df_grouped['ClosedCnt'].fillna(0, inplace=True)

    # get open defects
    opendefects = get_open_defects_count(df_grouped)
    df_grouped = df_grouped.assign(OpenDefects=opendefects)
   
    # get mttr summary
    df_plot_data = merge_mttr(df_grouped, mttr_df)

    #print("Plot Data:\n", df_plot_data)
    
    return df_plot_data

    
#--------------------------------------------------
# Group plot data by months to plot
# - returns DataFrame structure 
#--------------------------------------------------
def group_counts_by_month(df_plot_data, mttr_calcs, months_to_plot_df):
  
    # assign MTTR calcs
    df_data = df_plot_data.assign(MTTR=mttr_calcs.MTTR)
    if 'index' in df_data.columns:
        df_data.drop('index', axis=1, inplace=True)    # index column created by assign
    
    # merge data into months_to_plot
    df_data.reset_index(inplace=True)
    df_data.set_index('Months', inplace=True)

    df_product_by_month = pd.merge(months_to_plot_df["Months"],
                                    df_data[["FYQ","OpenCnt","ClosedCnt","OpenDefects","MTTR"]],
                                    on="Months")
    # drop all null rows
    df_product_by_month.reset_index(inplace=True)
    df_product_by_month.dropna(inplace=True)

   
    return df_product_by_month
                        

#-------------------------------------------------------
# Group plot data by FYQ
# - returns DataFrame structure 
#-------------------------------------------------------
def group_counts_by_fyq(df_plot_data, mttr_calcs, end_fyq):

    # get raw mttr base calcs
    mttr_fyq = get_mttr_fyq(mttr_calcs)
    
    # sum open/closed counts by FYQ
    df_grouped = df_plot_data.groupby(["FYQ"])["OpenCnt","ClosedCnt"].sum()
    df_grouped.reset_index(inplace=True)

    # recalc open defects
    opendefects = get_open_defects_count(df_grouped)
    df_grouped = df_grouped.assign(OpenDefects=opendefects)

    if 'index' in df_grouped.columns:
        df_grouped.drop('index', axis=1, inplace=True)    # index column created by assign

    # merge mttr calcs for fyq
    df_grouped.set_index("FYQ", inplace=True)
    
    df_product_by_fyq = pd.merge(df_grouped,
                                    mttr_fyq["MTTR"],
                                    left_on="FYQ",
                                    right_on="FYQ",
                                    how='outer',
                                    indicator=False)
    
    df_product_by_fyq['MTTR'].fillna(0, inplace=True)
    df_product_by_fyq.reset_index(inplace=True)
    df_product_by_fyq.dropna(inplace=True)

    # only report current fyq if at end  
    if not end_fyq:
        df_product_by_fyq = df_product_by_fyq.head(-1)

    
    return df_product_by_fyq


#------------------------------------------------------------
# Process ATC data ready for plotting
# - returns DataFrame structure 
#------------------------------------------------------------
def get_atc_plot_data(df, toolcfg):

    # get schedule date from description
    rundate = pd.to_datetime(df.description.str.split('_').str[1], format="%Y-%m-%d", errors='ignore')
    rundate.dropna(inplace=True)        # ignore null rows
    df = df.assign(rundate=rundate) 
   
    # filter data by rundate
    dt = date.today()
    end_dt = util.get_next_date(datetime(dt.year, dt.month, 1), 0, -1)
    mth_filter = config.autokpi["months_to_plot"]+1    # add 1 because dates are inclusive
    start_dt = util.get_next_date(datetime(end_dt.year, end_dt.month, 1), mth_filter, 0)

    end_dt = pd.to_datetime(end_dt, format="%Y-%m-%d")          # put dates in right format to 
    start_dt = pd.to_datetime(start_dt, format="%Y-%m-%d")      # compare with dataframe dates
    kpilog.debug("ATC dates: Start - {0}; End - {1}".format(start_dt, end_dt))
    
    df_atc = filter_df_by_date(df, toolcfg, start_dt, end_dt)

    # setup columns for plot
    rundate_int = rundate.apply(lambda x: xlrd.xldate.xldate_from_date_tuple((x.year, x.month, x.day), 0))
    df_atc_plot = df_atc.assign(rundate_int=rundate_int)

    df_atc_plot["totalfailed"] = df_atc_plot.failed + df_atc_plot.incomplete
    df_atc_plot["%passed"] = (df_atc_plot.passed / df_atc_plot.jobs_count)*100
    df_atc_plot["%failed"] = (df_atc_plot.totalfailed / df_atc_plot.jobs_count)*100

    
    return df_atc_plot
            
