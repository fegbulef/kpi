#!/usr/local/bin/python

"""*******************************************************************************
Created by:   Fiona Egbulefu (Contractor)

Created date: 12 April 2019

Description:  - Main module that runs the KPI automation process.
              - Input parameters are used to select tool/kpi to process.
              - Config module used to validate and process each tool/kpi selected

*******************************************************************************"""

import os
import sys
import argparse
import time

from datetime import datetime, date

# user defined modules
import config      
import importdata  
import dataprep    
import plotkpi      



#-------------------------------------------------------------
# Clears files from output directory
# - returns None
#-------------------------------------------------------------
def clear_kpi_output():

    print("\nClear output directory...")

    cwd = os.getcwd()
    output_dir = os.path.join(cwd, config.autokpi["savedir"])

    kpis = [f for f in os.listdir(output_dir) if f.endswith(".png")]
    
    for kpi in kpis:
        kpifile = os.path.join(output_dir, kpi)
        
        try:
            print("...deleting", kpifile)
            os.remove(kpifile)
            time.sleep(1)   # make sure file is deleted

        except Exception as e:
            print("\nWARNING - Could not delete", kpifile)

    return


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

    print("\nKPI codes:", out_kpi)
    return out_kpi


#------------------------------------------------------------
# Add value of one datafrom column into another of same name 
# - returns Dataframe 
#------------------------------------------------------------
def sum_df_columns(df_sum, df_add, columnlist):

    for column in columnlist:
        df_sum[column] += df_add[column]

    return df_sum



#---------------#
#   M A I N     #
#---------------#

def main(kpi_dict, importfromxl):

    #if kpi_dict: clear_output_dir()      
    
    print("\nInput Parms:", kpi_dict)
    clear_kpi_output()

    # Setup dates for filters and for plotting
    dt = date.today()
    end_dt = dataprep.get_next_date(datetime(dt.year, dt.month, 1), 2, -1)   # end of next month
    
    filter_mth = config.autokpi["months_to_plot"]
    start_dt = dataprep.get_next_date(datetime(dt.year, dt.month, 1), filter_mth, 0)
    months_to_plot_df = dataprep.get_plot_months(start_dt, end_dt)

    fyq_start = config.autokpi["fyq_start"].split('/')
    start_dt_fyq = datetime(int(fyq_start[2]), int(fyq_start[1]), int(fyq_start[0]))
    months_fyq_df = dataprep.get_plot_fyqs(start_dt_fyq, end_dt)

    # Process each tool/kpi combination
    for tool, kpis in kpi_dict.items():
        import_df = None
        
        toolcfg = config.autokpi["tools"][tool]
        print("\n\nProcessing KPI for:", tool)

        for kpi in kpis:
            print("\nSelected -", kpi)

            plot_fyq = True
            if kpi == 'PSIRT': plot_fyq = False
            
            if importfromxl:    # import data from (saved) excel workbook
                import_df = importdata.import_from_excel(toolcfg, tool, kpi)
            else:               # import data using tool api (??)
                import_df = importdata.import_from_api(toolcfg, tool, kpi)

            if import_df is None:
                print("\nWARNING - Could not import data for {0}: {1}".format(tool, kpi))
                continue

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


                df_product = dataprep.get_product_data(df_reformat, product, toolcfg, kpi)           
                if df_product is None:
                    print("\nWARNING - No data for {0}: {1}".format(kpi, product_code))
                    continue

                print("\nProcessing {0} data for: {1}\n".format(kpi, product_code))

                # get mttr days
                print("\n1. Calculate MTTR days....")
                mttr_df = dataprep.get_mttr_days(df_product, months_fyq_df, toolcfg)
                # get open/closed counts
                print("\n2. Get open/closed counts....")
                df_open_grp, df_closed_grp = dataprep.get_product_counts(df_product)

                # merge open/closed counts
                print("\n3. Merge open/closed/mttr data....")
                df_plot_data = dataprep.get_plot_data(df_open_grp, df_closed_grp, mttr_df, months_fyq_df)
                # perform mttr calc
                print("\n4. Perform MTTR calcs....")
                mttr_calcs = dataprep.get_mttr_calcs(df_plot_data)

                #***********************
                # Monthly Product chart
                #***********************
                
                xaxis = "Months"

                print("\n5. Prepare monthly data and chart....")
                df_product_by_month = dataprep.group_counts_by_month(df_plot_data, mttr_calcs, months_to_plot_df)
                
                chart_title = str.join(' ', [kpi_title.replace('XXX', product_code), 'Month\n'])
                kpi_chart = plotkpi.plot_kpi_chart(df_product_by_month, product_code, chart_title, kpi, xaxis)
                
                if kpi_chart:            
                    print("\nMonthly chart created:", kpi_chart)

                #**********************
                # FYQ Product chart
                #**********************

                if plot_fyq:
                    xaxis = 'FYQ'

                    print("\n6. Prepare FYQ data and chart....")
                    df_product_by_fyq = dataprep.group_counts_by_fyq(df_plot_data, mttr_calcs)

                    chart_title = chart_title.replace('Month', 'Financial Quarter')
                    kpi_chart = plotkpi.plot_kpi_chart(df_product_by_fyq, product_code, chart_title, kpi, xaxis)

                if kpi_chart:            
                    print("\nFYQ chart created:", kpi_chart)
            
                # calculate totals
                if all_products == []:
                    df_all_by_month = df_product_by_month
                    if plot_fyq:
                        df_all_by_fyq = df_product_by_fyq
        
                else:
                    columnlist = ["OpenCnt", "ClosedCnt", "OpenDefects","MTTR"]
                    df_all_by_month = sum_df_columns(df_all_by_month, df_product_by_month, columnlist)
                    if plot_fyq:
                        df_all_by_fyq = sum_df_columns(df_all_by_fyq, df_product_by_fyq, columnlist)
                    
                all_products.append(product_code)


            #***********************
            # Monthly & FYQ Totals
            #***********************
        
            if not all_products == []:
            
                product_str = str.join(', ', all_products)

                #****************************
                # All Products Monthly chart
                #****************************

                print("\n7. Chart All monthly....")
                
                chart_title = str.join(' ', [kpi_title.replace('XXX', product_str), 'Month\n'])
                kpi_chart = plotkpi.plot_kpi_chart(df_all_by_month, product_str, chart_title, kpi, 'AllMonths')
                if kpi_chart:            
                    print("\nAll Months chart created:", kpi_chart)
            
                #****************************
                # All Products FYQ chart
                #****************************

                if plot_fyq:

                    print("\n8. Chart All FYQ....")
                    
                    chart_title = chart_title.replace('Month', 'Financial Quarter')
                    kpi_chart = plotkpi.plot_kpi_chart(df_all_by_fyq, product_str, chart_title, kpi, 'AllFYQ')
                    if kpi_chart:            
                        print("\nAll FYQ chart created:", kpi_chart)

        
    return
            
    

if "__name__" == "__main__":

    parser = argparse.ArgumentParser()

    # Get parameters
    parser.addargument("-kpi", type=string, help="List KPI system or codes separated by comma e.g JIRA,CDETS,..")
    parser.addargument("-fromxl", type=string, help="Import data from Excel? Y/N")
    args = parser.parse_args()

    importfromxl = False
    kpi_list = args.kpi.split()
    kpi_dict = get_kpi_codes(kpi_list)
    
    # Validate - kpi is required
    if not kpi_dict:
        print("kpi codes invalid or not supplied")
        sys.exit(-1)
    
    if args.fromxl:
        if args.fromxl.upper() == 'Y': importfromxl = True

    
    main(kpi_dict, importfromxl)

    print("\n\nFinished")
