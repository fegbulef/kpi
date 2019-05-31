#!/usr/local/bin/python

"""*************************************************************************
Created by:   Fiona Egbulefu (Contractor)

Created date: 16 April 2019

Description:  Functions to filter data, reformat dates and group data 
              - Monthly count of open/closed defects
              - Quarterly (FYQ) count of open/closed defects
              - MTTR calculations

**************************************************************************"""

import sys
import config   # user defined module

try:
    import pandas as pd
    import numpy as np

except ImportError:
    print("Please make sure the following modules are installed: 'pandas'; 'xlrd'")
    sys.exit(-1)

from datetime import datetime, date
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

            
#-----------------------------------------------
# Get month range from dates
# - returns DataFrame structure 
#-----------------------------------------------
def get_plot_months(start_dt, end_dt):

    months = np.arange(start_dt, end_dt, np.timedelta64(1, 'M'), dtype='datetime64[M]')
    months_df = pd.DataFrame(months, columns=["Months"])
    months_df = months_df["Months"].dt.strftime("%b-%y")    # format: MMM-YY

    # setup financial quarter for each month
    fyq = ['']* len(months_df)
    
    for i, month in months_df.items():
        mth, yr = month.split('-')      # into MMM and YY
        
        for qtr, qtr_months in config.autokpi["fyq"].items():
            if mth.upper() in qtr_months:
                int_yr = int(yr)
            
                if qtr == 'Q1' or (qtr == 'Q2' and mth.upper() != 'JAN'):
                    int_yr += 1

                fyq_str = str.join('', ['FY', str(int_yr), ' ', qtr])
                fyq[i] = fyq_str
                break

    df = months_df.to_frame()
    months_df = df.assign(FYQ=fyq)

    return months_df


#-----------------------------------------------
# Get FYQ range from dates
# - returns DataFrame structure 
#-----------------------------------------------
def get_plot_fyqs(start_dt, end_dt):

    max_fyq = config.autokpi["fyqs_to_plot"]

    # work out number of fyqs between start and end dates
    t = relativedelta(end_dt, start_dt)
    t_mths = (t.years*12) + t.months
    qtrs = (t_mths/3) - max_fyq

    if qtrs > 0:
        months_to_add = 3 * (qtrs if qtrs >= 1 else 1)
        start_dt = get_next_date(datetime(start_dt.year, start_dt.month, start_dt.day), months_to_add, 0)
        
    fyq_df = get_plot_months(start_dt, end_dt)

    return fyq_df


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

    print("\nReformat dates....")
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
            
            month_start, month_end = get_month_start_end(months_fyq_df.Months[j])
            
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

    print("\nMttr:\n", mttr_df)  
    return mttr_df
            

#---------------------------------------------------------------------------------------
# MTTR product calculations
# Calculations are based on a period of 3 months after the first 2 months calculations
# - returns DataFrame structure
#---------------------------------------------------------------------------------------
def get_mttr_calcs(df):

    mttr_calc = [0] * len(df)

    days = 0
    mttr = 0
    closed_cnt = 0
    
    for i in df.index:
        data = df[df.Months == df.Months[i]]
        if data.empty: continue

        month_start, month_end = get_month_start_end(data.iloc[0].Months)

        # sum values rolling forward
        days += (month_end - month_start).days
        closed_cnt += data.iloc[0].ClosedCnt
        mttr += data.iloc[0].MTTR

        # remove calculations of 4th month after each 3 month period
        if i > 2:
            dfx = df.iloc[i-3]
            start, end = get_month_start_end(dfx.loc["Months"])
            days -= (end - start).days
            closed_cnt -= dfx.loc["ClosedCnt"]
            mttr -= dfx.loc["MTTR"]

        # calculate mttr
        if closed_cnt == 0:
            mttr_calc[i] = round(mttr * days)
        else:
            mttr_calc[i] = round(mttr / closed_cnt)

    # update MTTR column with calculated values
    df_updated = df[["Months","FYQ"]]
    df_updated = df_updated.assign(MTTR=mttr_calc)

    print("\nMTTR Calcs:\n", df_updated)
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
    
    # get mttr summary
    mttr_df.reset_index(inplace=True)
    mttr_df.set_index('Months', inplace=True)
    
    df_plot_data = pd.merge(df_grouped[["FYQ", "Months", "OpenCnt", "ClosedCnt"]],
                            mttr_df["MTTR"],
                            on="Months")

    df_plot_data.reset_index(inplace=True)
   
    print("\nPlot Data:\n", df_plot_data.info())
    return df_plot_data

    
#--------------------------------------------------
# Group plot data by months to plot
# - returns DataFrame structure 
#--------------------------------------------------
def group_counts_by_month(df_plot_data, mttr_calcs, months_to_plot_df):
  
    # get open defects
    opendefects = get_open_defects_count(df_plot_data)
    df_data = df_plot_data.assign(OpenDefects=opendefects)

    df_data = df_data.assign(MTTR=mttr_calcs.MTTR)
    
    # merge data into months_to_plot
    df_data.reset_index(inplace=True)
    df_data.set_index('Months', inplace=True)

    df_product_by_month = pd.merge(months_to_plot_df["Months"],
                                    df_data[["FYQ","OpenCnt","ClosedCnt","OpenDefects","MTTR"]],
                                    on="Months")
    # drop all null rows
    df_product_by_month.reset_index(inplace=True)
    df_product_by_month.dropna(inplace=True)
   
    #print("\nMonths group:\n", df_product_by_month)
    return df_product_by_month
                        

#-------------------------------------------------------
# Group plot data by FYQ
# - returns DataFrame structure 
#-------------------------------------------------------
def group_counts_by_fyq(df_plot_data, mttr_calcs):

    # get raw mttr base calcs
    mttr_fyq = get_mttr_fyq(mttr_calcs)
    
    # sum open/closed counts by FYQ
    df_grouped = df_plot_data.groupby(["FYQ"])["OpenCnt","ClosedCnt"].sum()
    df_grouped.reset_index(inplace=True)

    # get open defects
    opendefects = get_open_defects_count(df_grouped)
    df_grouped = df_grouped.assign(OpenDefects=opendefects)

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
    
    #print("\nFYQ group:\n", df_product_by_fyq)
    return df_product_by_fyq
