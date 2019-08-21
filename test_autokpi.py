#!/usr/bin/python3

"""*******************************************************************************
Created by:   Fiona Egbulefu (Contractor)

Created date: 25 April 2019

Description:  AutoKPI test module 
     
*******************************************************************************"""

import os
import numpy as np
import pandas as pd

import pytest

from jira import JIRA
from datetime import datetime

# user defined modules
import util
import config
import importdata
import dataprep
import swdlprep
import plotkpi


#******************
# global constants
#******************

JIRAconfig = config.autokpi["tools"]["JIRA"]
CDETSconfig = config.autokpi["tools"]["CDETS"]
ACANOconfig = config.autokpi["tools"]["ACANO"]
BEMSconfig = config.autokpi["tools"]["BEMS"]
SWDLconfig = config.autokpi["tools"]["SWDL"]

USER = config.autokpi["auth"]["user"]
PWD = config.autokpi["auth"]["password"]

START_DT = pd.to_datetime('01/08/2016', format="%d/%m/%Y")      # plot months
END_DT = pd.to_datetime('01/08/2017', format="%d/%m/%Y")        #

#**************
# test data
#**************

test_months = {'Months': ['Aug-16','Sep-16','Oct-16','Nov-16','Dec-16','Jan-17',
                         'Feb-17','Mar-17','Apr-17','May-17','Jun-17','Jul-17'],          
              'FYQ': ['FY17 Q1','FY17 Q1','FY17 Q1','FY17 Q2','FY17 Q2','FY17 Q2',
                      'FY17 Q3','FY17 Q3','FY17 Q3','FY17 Q4','FY17 Q4','FY17 Q4']}

CWD = os.getcwd()

CFPD_raw = os.path.join(CWD, "test_data", "CFPD_raw.csv")
CFPD_reformat = os.path.join(CWD, "test_data", "CFPD_reformat.csv")

CFPD_open = os.path.join(CWD, "test_data", "CFPD_open.csv")
CFPD_closed = os.path.join(CWD, "test_data", "CFPD_closed.csv")

CFPD_mttr_calcs = os.path.join(CWD, "test_data", "CFPD_mttr_calcs.csv")
CFPD_mttr_days = os.path.join(CWD, "test_data", "CFPD_mttr_days.csv")
CFPD_plot_data = os.path.join(CWD, "test_data", "CFPD_plot_data.csv")


#---------------------------------------------------------
# 1. Validate kpi codes input 
def test_get_kpi_codes():
#---------------------------------------------------------
    kpi_dict = util.get_kpi_codes(['IFD','PSIRT','CDETS','CFD', 'ACANO'])
    assert kpi_dict == {'JIRA': ['IFD','CFD'], 'CDETS': ['PSIRT'], 'ACANO': ['ATC']}
    

#---------------------------------------------------------
# 2.1 Check Excel file import: JIRA
@pytest.mark.skip(reason="Not required for Production")
def test_jira_import_from_excel():
#---------------------------------------------------------
    excel_df = importdata.import_from_excel(JIRAconfig, 'JIRA', 'CFPD')
    assert isinstance(excel_df, pd.DataFrame)
    assert excel_df.columns.values.tolist() == ['Issue id','Status','Priority','Issue key','Created','Resolved']
    

#---------------------------------------------------------
# 2.2 Check Excel file import: CDETS
@pytest.mark.skip(reason="Not required for Production")
def test_cdets_import_from_excel():
#---------------------------------------------------------
    excel_df = importdata.import_from_excel(CDETSconfig, 'CDETS', 'PSIRT')
    assert isinstance(excel_df, pd.DataFrame)
    assert excel_df.columns.values.tolist() == ['Identifier','Status','SIR','Product','OPENED','CLOSED']


#---------------------------------------------------------
# 2.3 Check Excel file import: SWDL
def test_swdl_import_from_excel():
#---------------------------------------------------------
    excel_df = importdata.import_from_excel(SWDLconfig, 'SWDL', 'SWDL')
    assert isinstance(excel_df, pd.DataFrame)

    assert 'Download Date and Time'  in excel_df.columns.values.tolist()
    assert 'Full File Name' in excel_df.columns.values.tolist()
    assert 'Access Level Name' in excel_df.columns.values.tolist()

    
#---------------------------------------------------------
# 2.4 Check API import: JIRA
#@pytest.mark.skip(reason="Tested")
def test_import_from_jira_api():
#---------------------------------------------------------
    jira_api = importdata.get_jira_client(JIRAconfig, 'CFPD')
    if jira_api:
        jira_df = importdata.get_jira_issues(JIRAconfig, jira_api, 'CFPD')
        assert len(jira_df) > 0
            

#---------------------------------------------------------
# 2.5 Check API import: CDETS (QDDTS)
#@pytest.mark.skip(reason="Tested")
def test_import_from_qddts_webserver():
#---------------------------------------------------------
    qddts_json = importdata.get_api_data(CDETSconfig, 'PSIRT')
    if qddts_json:
        results = importdata.import_qddts_results(CDETSconfig, qddts_json)
        assert len(results) > 0
    

#---------------------------------------------------------
# 2.6 Check API import: ACANO
#@pytest.mark.skip(reason="Tested")
def test_import_from_acano_api():
#---------------------------------------------------------
    parms = '2'     # VM Server
    acano_json = importdata.get_api_data(ACANOconfig, 'ATC', parms)

    if acano_json:
        results = importdata.import_acano_results(ACANOconfig, acano_json)
        assert len(results) > 0

    
#---------------------------------------------------------
# 2.7 Check DB import: BEMS
#@pytest.mark.skip(reason="Tested")
def test_bems_import():
#---------------------------------------------------------
    bems = importdata.OracleDB(BEMSconfig)
    # Oracle connection check
    assert isinstance(bems, importdata.OracleDB)
    
    bems_data = importdata.import_from_db(BEMSconfig, 'BEMS')
    # Oracle data extract check
    assert len(bems_data) > 0

        
#---------------------------------------------------------
# 3.1 Reformat import dates 
def test_reformat_import_dates():
#---------------------------------------------------------
    import_df = pd.read_csv(CFPD_raw)   
    reformat_df = dataprep.reformat_df_dates(import_df, JIRAconfig, False)
    assert len(reformat_df) > 0

    # Test date formats
    for i in reformat_df.index:
        assert datetime.strptime(reformat_df['OpenMonth'][i], "%b-%y")
        assert datetime.strptime(reformat_df['ClosedMonth'][i], "%b-%y")


#---------------------------------------------------------
# 3.2 Get Open/closed counts
def test_open_closed_counts():
#---------------------------------------------------------

    import_df = pd.read_csv(CFPD_raw)     
    reformat_df = dataprep.reformat_df_dates(import_df, JIRAconfig, False)
    # test mttr for 'CLIENT' product
    product_df = dataprep.get_product_data(reformat_df, 'CLIENT', JIRAconfig, 'CFPD')
     
    # get open/closed counts for CLIENT
    df_open, df_closed = dataprep.get_product_counts(product_df)

    test_open_df = pd.read_csv(CFPD_open)
    df_open.reset_index(inplace=True)
    assert df_open.equals(test_open_df)

    test_closed_df = pd.read_csv(CFPD_closed)
    df_closed.reset_index(inplace=True)
    assert df_closed.equals(test_closed_df)
    

#---------------------------------------------------------
# 3.3 Calculate MTTR days
#@pytest.mark.skip(reason="Tested")
def test_mttr_days():
#---------------------------------------------------------
    fyq_df = pd.DataFrame(test_months)

    import_df = pd.read_csv(CFPD_raw)     
    reformat_df = dataprep.reformat_df_dates(import_df, JIRAconfig, False)
    # test mttr for 'CLIENT' product
    product_df = dataprep.get_product_data(reformat_df, 'CLIENT', JIRAconfig, 'CFPD')
     
    # check mttr days
    mttr_days_df = dataprep.get_mttr_days(product_df, fyq_df, JIRAconfig)
    test_mttr_df = pd.read_csv(CFPD_mttr_days)
    assert mttr_days_df["MTTR"].equals(test_mttr_df["MTTR"])


#---------------------------------------------------------
# 3.4 MTTR calculations
#@pytest.mark.skip(reason="Tested")
def test_mttr_calc():
#---------------------------------------------------------
    plot_df = pd.read_csv(CFPD_plot_data)
    test_mttr_calcs = pd.read_csv(CFPD_mttr_calcs)    
    mttr_calcs = dataprep.get_mttr_calcs(plot_df)
    
    assert mttr_calcs["MTTR"].equals(test_mttr_calcs["MTTR"])
    

#---------------------------------------------------------
# 3.5 Get plot months
#@pytest.mark.skip(reason="Tested")
def test_get_plot_months():
#---------------------------------------------------------
    months_df = dataprep.get_plot_months(START_DT, END_DT)
    
    if isinstance(months_df, pd.DataFrame):
        test_months_df = pd.DataFrame(test_months)
        assert months_df.equals(test_months_df)
    else:
        pytest.fail()


#---------------------------------------------------------
# 3.6 Get plot FYQs
#@pytest.mark.skip(reason="Tested")
def test_get_plot_fyqs():
#---------------------------------------------------------
    start_dt = None

    dt = datetime.today()
    end_dt = util.get_next_date(datetime(dt.year, dt.month, 1), 2, -1) # end of next month

    fyq_start, fyq_end = util.get_kpi_fyq_start_end(start_dt, end_dt)
    fyq_df = dataprep.get_plot_months(fyq_start, fyq_end)
    
    if isinstance(fyq_df, pd.DataFrame):
        assert 'FYQ' in fyq_df.columns.values.tolist()
        unique_fyq = fyq_df.FYQ
    
        # Test number of fyqs against max 
        max_fyq = config.autokpi["fyqs_to_plot"]
        unique, counts = np.unique(unique_fyq, return_counts=True)
        assert len(unique) <= max_fyq
        
    else:
        pytest.fail()


#---------------------------------------------------------
# 3.7 Get filtered SWDL data
#@pytest.mark.skip(reason="Tested")
def test_filter_swdl():
#---------------------------------------------------------
    excel_df = importdata.import_from_excel(SWDLconfig, 'SWDL', 'SWDL')
    assert isinstance(excel_df, pd.DataFrame)
    
    if isinstance(excel_df, pd.DataFrame):
        filtered_df = swdlprep.filter_swdl(excel_df)

        # check additional columns added during filter function
        assert 'DownloadFile' in filtered_df.columns
        assert 'Product' in filtered_df.columns
        assert 'DownloadMonth' in filtered_df.columns
    
        # check export file created
        exportfile = os.path.join(os.getcwd(), config.autokpi["savedir"], "exportswdl.csv")
        assert os.path.exists(exportfile)
        
    else:
        pytest.fail()


#---------------------------------------------------------
# 3.8 Get SWDL data by product
#@pytest.mark.skip(reason="Tested")
def test_get_swdl_product():
#---------------------------------------------------------
    excel_df = importdata.import_from_excel(SWDLconfig, 'SWDL', 'SWDL')
    assert isinstance(excel_df, pd.DataFrame)
    
    if isinstance(excel_df, pd.DataFrame):
        filtered_df = swdlprep.filter_swdl(excel_df)

        # filter for 'CMM'
        cmm1 = filtered_df[filtered_df.Product == 'CMM']
        cmm2 = swdlprep.get_swdl_product(filtered_df, "CMM")

        assert len(cmm1) == len(cmm2)
        
    else:
        pytest.fail()

                
#---------------------------------------------------------
# 3.9 Get SWDL grouped data by date
#@pytest.mark.skip(reason="Tested")
def test_get_swdl_grouped_data_by_date():
#---------------------------------------------------------
    excel_df = importdata.import_from_excel(SWDLconfig, 'SWDL', 'SWDL')
    assert isinstance(excel_df, pd.DataFrame)
    
    if isinstance(excel_df, pd.DataFrame):
        filtered_df = swdlprep.filter_swdl(excel_df)

        # check for 'CMA' 18M
        cma = swdlprep.get_swdl_product(filtered_df, "CMA")
        cma_grp = swdlprep.group_data_by_date(cma, '18M', 'CMA')

        # check column names for CMA releases
        for c in cma_grp.columns.values.tolist():
            assert 'CMA' in c

        # check min/max dates are 18M apart (incl.)
        min_mth = cma_grp.index.values.tolist()[0]
        max_mth = cma_grp.index.values.tolist()[-1]

        start_dt = datetime.strptime("01-" + min_mth, "%d-%b-%Y")
        dt = util.get_next_date(datetime(start_dt.year, start_dt.month, start_dt.day), 17, 0)

        assert dt.strftime("%b-%Y") == max_mth

    else:
        pytest.fail()

                
#---------------------------------------------------------
# 4.1 Plot Monthly KPI chart
#@pytest.mark.skip(reason="Tested")
def test_monthly_kpi_chart():
#---------------------------------------------------------
    chart_title = JIRAconfig["kpi"]['CFPD']["kpi_title"].replace('XXX', 'CMA')
    mth_title = str.join(' ', [chart_title, 'Month\n'])

    # import plot data and mttr calculations
    plot_df = pd.read_csv(CFPD_plot_data)
    mttr_calcs = pd.read_csv(CFPD_mttr_calcs)    
    months_df = pd.DataFrame(test_months)

    plot_by_month = dataprep.group_counts_by_month(plot_df, mttr_calcs, months_df)

    if isinstance(plot_by_month, pd.DataFrame):
        assert(len(plot_by_month) > 0)

        kpi_chart = plotkpi.plot_kpi_chart(plot_by_month, 'CMA', chart_title, 'CFPD', "Months", True)
 
        assert 'png' in kpi_chart     # assert kpi_chart is a picture file
        assert os.path.exists(kpi_chart)


#---------------------------------------------------------
# 4.2 Plot FYQ KPI chart
#@pytest.mark.skip(reason="Tested")
def test_fyq_kpi_chart():
#---------------------------------------------------------
    chart_title = JIRAconfig["kpi"]['CFPD']["kpi_title"].replace('XXX', 'CMA')
    fyq_title = str.join(' ', [chart_title, 'Financial Quarter\n'])

    # import plot data and mttr calculations
    plot_df = pd.read_csv(CFPD_plot_data)
    mttr_calcs = pd.read_csv(CFPD_mttr_calcs)    
    months_df = pd.DataFrame(test_months)

    # only report current fyq if at end  
    end_fyq = util.is_fyq_start(END_DT)
    plot_by_fyq = dataprep.group_counts_by_fyq(plot_df, mttr_calcs, end_fyq)

    if isinstance(plot_by_fyq, pd.DataFrame):
        assert(len(plot_by_fyq) > 0)

        kpi_chart = plotkpi.plot_kpi_chart(plot_by_fyq, 'CMA', chart_title, 'CFPD', "FYQ", True)
 
        assert 'png' in kpi_chart     # assert kpi_chart is a picture file
        assert os.path.exists(kpi_chart)


#---------------------------------------------------------
# 4.3 Plot SWDL KPI chart for CMS
#@pytest.mark.skip(reason="Tested")
def test_cms_swdl_kpi_chart():
#---------------------------------------------------------
    excel_df = importdata.import_from_excel(SWDLconfig, 'SWDL', 'SWDL')
    assert isinstance(excel_df, pd.DataFrame)
    
    if isinstance(excel_df, pd.DataFrame):
        filtered_df = swdlprep.filter_swdl(excel_df)
        CMS = swdlprep.get_swdl_product(filtered_df, "CMS")

        # plot data
        df_plot = swdlprep.group_data_by_date(CMS, "allW", "CMS")
        kpi_chart = plotkpi.plot_swdl_chart(df_plot, "CMS", "allW", True)

        assert 'png' in kpi_chart     # assert kpi_chart is a picture file
        assert os.path.exists(kpi_chart)
        
    else:
        pytest.fail()
        
