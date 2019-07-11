#!/usr/bin/python3

"""*******************************************************************************
Created by:   Fiona Egbulefu (Contractor)

Created date: 12 April 2019

Description:  - Main module that runs the KPI automation process.
              - Input parameters are used to select tool/kpi to process.
              - Config module used to validate and process each tool/kpi selected

*******************************************************************************"""

import os
import sys
import time
import logging
import argparse

from datetime import datetime, date

# user defined modules
import util
import config
import importdata  
import dataprep    
import plotkpi      


kpilog = util.setup_logger(config.autokpi["logname"], config.autokpi["logfile"])


#-------------------------------------------------------------
# Clears files from output directory
# - returns None
#-------------------------------------------------------------
def clear_kpi_output():

    kpilog.info("Clear output directory...")

    cwd = os.getcwd()
    output_dir = os.path.join(cwd, config.autokpi["savedir"])

    kpis = [f for f in os.listdir(output_dir) if f.endswith(".png")]
    
    for kpi in kpis:
        kpifile = os.path.join(output_dir, kpi)
        
        try:
            kpilog.debug("...deleting {}".format(kpifile))
            os.remove(kpifile)
            time.sleep(1)   # make sure file is deleted

        except Exception as e:
            kpilog.warning("Could not delete {}".format(kpifile))

    return


#------------------------------------------------------------
# Add value of one datafrom column into another of same name 
# - returns Dataframe 
#------------------------------------------------------------
def sum_df_columns(df_sum, df_add, columnlist):

    for column in columnlist:
        df_sum[column] += df_add[column]

    return df_sum


#------------------------------------------------------------
# Import ATC data by schedule and plot charts
# - returns None 
#------------------------------------------------------------
def process_atc_schedules(toolcfg, tool, kpi):

    for sched_nm, sched_id in toolcfg["schedules"].items():
        kpilog.info("...processing ATC schedules for {}".format(sched_nm))
        
        import_df = importdata.import_from_api(toolcfg, tool, kpi, sched_id)

        if import_df is None:
            kpilog.warning("Could not import data for {0} - {1}".format(kpi, sched_nm))
            continue

        if len(import_df) < 7:      # ?? less than a weeks data ??
            kpilog.warning("Insufficient data to plot {} - {}".format(kpi, sched_nm))
            continue
        
        # get plot data
        df_atc_plot = dataprep.get_atc_plot_data(import_df, toolcfg)
        df_atc_plot.sort_values('rundate_int', ascending=True, inplace=True)

        # plot charts
        for chart_key, chart_title in toolcfg["kpi"][kpi]["kpi_title"].items():

            chart_title = chart_title.replace('XXX', sched_nm)
            kpi_chart = plotkpi.plot_atc_chart(df_atc_plot, sched_nm, chart_title, chart_key)

            if kpi_chart:
                kpilog.info("{0} {1} chart created for {2}".format(sched_nm, chart_key, kpi_chart))


    return None


#-------------------------------------------------------------------
# For each KPI code, import, filter and format data to plot charts
# - returns None 
#-------------------------------------------------------------------
def main(kpi_dict, importfromxl):

    kpilog.debug("Input Parms: {}".format(kpi_dict))
    
    clear_kpi_output()

    # Setup dates for filters and for plotting
    months_to_plot_df = dataprep.get_plot_months(None, None)    # use default dates 

    fyq_start, fyq_end = util.get_kpi_fyq_start_end(None, None) # use default dates
    months_fyq_df = dataprep.get_plot_months(fyq_start, fyq_end)

    # set var to determine if at end of current fyq
    end_fyq = False
    if util.is_fyq_start(fyq_end):
        end_fyq = True

    # Process each tool/kpi combination
    for tool, kpis in kpi_dict.items():
        import_df = None
        
        toolcfg = config.autokpi["tools"][tool]
        kpilog.info("Processing KPI for: {}".format(tool))

        for kpi in kpis:
            kpilog.debug("Selected - {}".format(kpi))
            plot_fyq = True

            if kpi == 'ATC':
                process_atc_schedules(toolcfg, tool, kpi)
                continue

            if importfromxl:        # import data from (saved) excel workbook
                import_df = importdata.import_from_excel(toolcfg, tool, kpi)
            else:                   # import data using tool api
                import_df = importdata.import_from_api(toolcfg, tool, kpi)

            if import_df is None:
                kpilog.warning("Could not import data for {0}: {1}".format(tool, kpi))
                continue

            if kpi == 'PSIRT': plot_fyq = False

            # reformat dates
            df_reformat = dataprep.reformat_df_dates(import_df, toolcfg, importfromxl)
                
            # Set kpi chart text
            kpi_title = toolcfg["kpi"][kpi]["kpi_title"]

            # process data by project
            all_products = []
            df_all_by_month = None
            df_all_by_fyq = None
            
            for product in toolcfg["products"]:

                # get project code
                if product in ['CLIENT', 'meeting_apps']:
                    product_code = 'CMA'
                elif product in ['SERVER', 'meetingserver']:
                    product_code = 'CMS'
                else:       # management
                    product_code = 'CMM'

                if kpi == 'CFPD' and product_code == 'CMM':     # ignore CMM for CFPD ??
                    continue

                df_product = dataprep.get_product_data(df_reformat, product, toolcfg, kpi)           
                if df_product is None:
                    kpilog.warning("No data for {0}: {1}".format(kpi, product_code))
                    continue

                kpilog.info("Processing {0} data for: {1}".format(kpi, product_code))

                # get mttr days
                kpilog.debug("1. Calculate MTTR days....")
                mttr_df = dataprep.get_mttr_days(df_product, months_fyq_df, toolcfg)

                # get open/closed counts
                kpilog.debug("2. Get open/closed counts....")
                df_open_grp, df_closed_grp = dataprep.get_product_counts(df_product)

                # merge open/closed counts
                kpilog.debug("3. Merge open/closed/mttr data....")
                df_plot_data = dataprep.get_plot_data(df_open_grp, df_closed_grp, mttr_df, months_fyq_df)
    
                # perform mttr calc
                kpilog.debug("4. Perform MTTR calcs....")
                mttr_calcs = dataprep.get_mttr_calcs(df_plot_data, product_code)

                #***********************
                # Monthly Product chart
                #***********************
                
                xaxis = "Months"

                kpilog.debug("5. Prepare monthly data and chart....")
                df_product_by_month = dataprep.group_counts_by_month(df_plot_data, mttr_calcs, months_to_plot_df)

                chart_title = str.join(' ', [kpi_title.replace('XXX', product_code), 'Month\n'])
                kpi_chart = plotkpi.plot_kpi_chart(df_product_by_month, product_code, chart_title, kpi, xaxis)

                if kpi_chart:            
                    kpilog.info("Monthly chart created: {}".format(kpi_chart))

                #**********************
                # FYQ Product chart
                #**********************

                if plot_fyq:
                    xaxis = 'FYQ'

                    kpilog.debug("6. Prepare FYQ data and chart....")
                    df_product_by_fyq = dataprep.group_counts_by_fyq(df_plot_data, mttr_calcs, end_fyq)

                    chart_title = chart_title.replace('Month', 'Financial Quarter')
                    kpi_chart = plotkpi.plot_kpi_chart(df_product_by_fyq, product_code, chart_title, kpi, xaxis)

                    if kpi_chart:            
                        kpilog.info("FYQ chart created: {}".format(kpi_chart))

            
                # store totals
                if all_products == []:
                    
                    df_all_mttr = mttr_df
                    df_all_months = df_plot_data
            
                else:

                    columnlist = ["OpenCnt", "ClosedCnt", "OpenDefects"]

                    df_all_months = sum_df_columns(df_all_months, df_plot_data, columnlist)
                    df_all_mttr.MTTR += mttr_df.MTTR
                    

                all_products.append(product_code)


            #***********************
            # Monthly & FYQ Totals
            #***********************
        
            if not all_products == []:
            
                # perform mttr calc for al months
                kpilog.debug("7. Perform All MTTR calcs....")
                df_all_months = dataprep.merge_mttr(df_all_months, df_all_mttr, True)
                mttr_calcs = dataprep.get_mttr_calcs(df_all_months)

                product_str = str.join(', ', all_products)


                #****************************
                # All Products Monthly chart
                #****************************

                kpilog.debug("8. Group all by month....")
                df_all_by_month = dataprep.group_counts_by_month(df_all_months, mttr_calcs, months_to_plot_df)
               
                kpilog.debug("9. Chart All monthly....")
                
                chart_title = str.join(' ', [kpi_title.replace('XXX', product_str), 'Month\n'])

                kpi_chart = plotkpi.plot_kpi_chart(df_all_by_month, product_str, chart_title, kpi, 'AllMonths')
                if kpi_chart:            
                    kpilog.info("All Months chart created: {}".format(kpi_chart))

                
                #****************************
                # All Products FYQ chart
                #****************************

                if plot_fyq:
                    kpilog.debug("10. Group all by FYQ....")
                    df_all_by_fyq = dataprep.group_counts_by_fyq(df_all_months, mttr_calcs, end_fyq)

                    kpilog.debug("11. Chart All FYQ....")
                    
                    chart_title = chart_title.replace('Month', 'Financial Quarter')

                    kpi_chart = plotkpi.plot_kpi_chart(df_all_by_fyq, product_str, chart_title, kpi, 'AllFYQ')
                    if kpi_chart:            
                        kpilog.info("All FYQ chart created: {}".format(kpi_chart))
            
        
    return None



#*************#
#   M A I N   #
#*************#


if __name__ == "__main__":
    
    parser = argparse.ArgumentParser()

    # Get parameters
    parser.add_argument("-kpi", type=str, help="List KPI tools/codes separated by comma e.g JIRA,CDETS,..")
    parser.add_argument("-fromxl", type=str, help="Import data from Excel? Y/N")
    args = parser.parse_args()

    importfromxl = False
    kpi_list = args.kpi.upper().split(',')
    kpi_dict = util.get_kpi_codes(kpi_list)
    
    # Validate - kpi is required
    if not kpi_dict:
        print("KPI codes invalid or not supplied")

    else:
        if args.fromxl:
            if args.fromxl.upper() == 'Y': importfromxl = True

        kpilog.info("Starting AutoKPI run.....")

        main(kpi_dict, importfromxl)

        kpilog.info("")
        kpilog.info("Finished!")
