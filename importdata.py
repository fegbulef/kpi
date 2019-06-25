#!/usr/bin/python3

"""********************************************************************
Created by:   Fiona Egbulefu (Contractor)

Created date: 12 April 2019

Description:  Import raw data for KPI automation process.
              - Imports from specified Excel sheets
              - Import data using tool API

********************************************************************"""

import os
import sys
import json
import requests
import warnings

# user defined module
import util
import config

from jira import JIRA
from jira.exceptions import JIRAError

from datetime import datetime

try:
    import pandas as pd
    
except ImportError:
    print("Please install the python 'pandas' and 'xlrd' modules")
    sys.exit(-1)

# get log
kpilog = util.get_logger(config.autokpi["logname"])


#------------------------------------------------------------
# Get list of column names from config
# - returns list of column names 
#------------------------------------------------------------
def get_column_names(toolcfg):

    id_col = toolcfg["id_column"]
    status_col = toolcfg["status_column"]
    priority_col = toolcfg["priority_column"]
    product_col = toolcfg["product_column"]
    open_col = toolcfg["open_column"]
    closed_col = toolcfg["closed_column"]

    columns = [id_col, status_col, priority_col, product_col, open_col, closed_col]

    return columns

    
#------------------------------------------------------------
# Construct filename from config using tool/kpi
# - returns filename (string) 
#------------------------------------------------------------
def get_config_filename(tool, kpi):

    cwd = os.getcwd()
    
    filename = ''.join([tool, "-", kpi, "s.xlsx"])
    filename = os.path.join(cwd, config.autokpi["datadir"], filename)
    
    if os.path.exists(filename):
        kpilog.debug("Found: {}".format(filename))
    else:
        kpilog.debug("{} does not exist - check config setup".format(filename))
        return None

    return filename


#-------------------------------------------------------------
# Setup data structure for loading API data
# - returns dictionary
#-------------------------------------------------------------
def get_api_data_structure(toolcfg, kpi=None):

    api_data = {}

    if kpi == 'ATC':
        columns = toolcfg["columns"]
    else:
        columns = get_column_names(toolcfg)
    
    for c in columns:
        api_data[c] = []

    return api_data


#------------------------------------------------------------
# Get API status code description
# - returns string 
#------------------------------------------------------------
def api_status_code_desc(api):

    status_desc = ''

    if api.status_code == 200:
        status_desc = "OK"
    elif api.status_code == 204:
        status_desc = "No Content"
    elif api.status_code == 400:
        status_desc = "Bad Request"
    elif api.status_code == 401:
        status_desc = "Unauthorized User/Password"
    elif api.status_code == 403:
        status_desc = "No permission to make this request"
    elif api.status_code == 404:
        status_desc = "Source Not found"
    elif api.status_code == 405:
        status_desc = "Method Not Allowed"
    elif api.status_code == 429:
        status_desc = "Too Many Requests"
    elif api.status_code == 500:
        status_desc = "Internal Server Error"
    elif api.status_code == 503:
        status_desc = "Service Unavailable"
    else:
        status_desc = "Request Unsuccessfull"
            
    return status_desc

    
#-------------------------------------------------------------
# Import data from a defined sheet in a given Excel workbook
# - returns DataFrame structure 
#-------------------------------------------------------------
def import_from_excel(toolcfg, tool, kpi):

    import_df = None

    xlfile = get_config_filename(tool, kpi)
    if not xlfile: return None
    
    # import defined columns
    xlsheetname = toolcfg["xlsheetname"]
    columns = get_column_names(toolcfg)
    #xlcolumns = cfg["xlcolumns"]  

    try:
        # import Excel data from specific workbook and sheet; ignore xlrd warnings
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            xldf = pd.read_excel(xlfile, sheet_name=xlsheetname)
            import_df = xldf[columns]
            
    except Exception as e:
        kpilog.error("{}".format(str(e)))

    if not import_df is None:
        kpilog.info("Imported records: {0}".format(len(import_df)))

    return import_df


#-------------------------------------------------------------
# Connect to JIRA client 
# - returns JIRA client object 
#-------------------------------------------------------------
def get_jira_client(toolcfg, user, pwd, kpi):

    jra = None
    
    server = toolcfg["apiserver"]
    option = {"server": server}

    try:
        jra = JIRA(options=option, auth=(user, pwd))
        if not jra:
            kpi.error("JIRA API Unsuccessful for {0}".format(kpi))
            return None
            
    except JIRAError as e:
        kpilog.error("JIRA API ERROR - {0}".format(api_status_code_desc(e.status_code)))

    kpilog.info("JIRA Connection Status: OK\n")
    
    return jra


#-------------------------------------------------------------
# Import JIRA issues
# - returns DataFrame structure 
#-------------------------------------------------------------
def get_jira_issues(toolcfg, jra, kpi):

    # get JQL query from config
    kpi_jql = toolcfg["kpi"][kpi]["jql"]

    # set limits on records to retrieve (500 at a time)
    # (NB: JIRA pulls max of 1000 records in one call)
    size = 1000   
    size_cnt  = 0

    id_col = toolcfg["id_column"]
    status = toolcfg["status_column"]
    priority = toolcfg["priority_column"]
    product = toolcfg["product_column"]
    open_col = toolcfg["open_column"]
    closed_col = toolcfg["closed_column"]

    api_data = get_api_data_structure(toolcfg)
    
    while True:
        start = size_cnt * size

        try:
            issues = jra.search_issues(kpi_jql, start, size)
            if len(issues) == 0: break     # no more issues to retrieve

            size_cnt += 1
            
            for issue in issues:
                # build dataframe
                api_data[id_col].append(str(issue.key))
                api_data[product].append(str(issue.fields.project))
                api_data[status].append(str(issue.fields.status.name))
                api_data[priority].append(str(issue.fields.priority.name))
                # reformat dates
                str_date = str(issue.fields.created)
                api_data[open_col].append(str_date.split('+')[0])

                # check if date closed available                
                if issue.fields.status.name in ['Resolved', 'Closed', 'Verified']:      
                    str_date = str(issue.fields.resolutiondate)
                    api_data[closed_col].append(str_date.split('+')[0])
                else:
                    api_data[closed_col].append(None)
                
        except Exception as e:
            kpilog.error("JIRA ERROR - {0}".format(str(e)))

    api_df = pd.DataFrame(api_data)

    return api_df


#-------------------------------------------------------------
# Build url from config
# - returns string
#-------------------------------------------------------------
def get_url(toolcfg, kpi, parms=None):
    
    query = ""
    fields = ""
    return_type = ""
    
    webservice = toolcfg["apiserver"]
    
    if "query" in toolcfg["kpi"][kpi]:
        query = toolcfg["kpi"][kpi]["query"].replace(' ', '%20')
        
        if kpi == 'ATC':
            query = query.replace('XXX', parms)

            
    if "type" in toolcfg["kpi"][kpi]:
        return_type = toolcfg["kpi"][kpi]["type"].replace('XXX', 'json')
        
    if "fields" in toolcfg["kpi"][kpi]:
        fields = toolcfg["kpi"][kpi]["fields"]

    url = str.join('',[webservice, query, return_type, fields])
    kpilog.info("URL: {}".format(url))
    
    return url


#-------------------------------------------------------------
# Connect to webservice 
# - returns json 
#-------------------------------------------------------------
def get_qddts_data(toolcfg, kpi):
    
    url = get_url(toolcfg, kpi)    

    try:
        req = requests.get(url)
        
        if not req.status_code == requests.codes.ok:
            req_msg = api_status_code_desc(req)
            kpilog.error("QDDTS Webservice ERROR - {0}".format(req_msg))
            return None
        
    except Exception as e:
        kpilog.error("QDDTS Webservice ERROR - {0}".format(str(e)))

    kpilog.info("QDDTS Connection: OK")
    return req.json()


#-------------------------------------------------------------
# Import Webserver results
# - returns Dataframe structure
#-------------------------------------------------------------
def process_qddts_results(toolcfg, qddts_json):

    api_data = get_api_data_structure(toolcfg)

    # id from api differs from excel
    id_col = toolcfg["id_api"]
    id_column = toolcfg["id_column"]

    for i in range(len(qddts_json)):
        bug = qddts_json[i]

        # build dataframe
        for column in api_data.keys():
            if column in bug:
                api_data[column].append(str(bug[column]))

        if not id_column in bug:
            api_data[id_column].append(bug[id_col])    # record identifier

        # update closed date to None if not available                
        if api_data["CLOSED"] in ['', ' ', None]:      
            api_data[closed_col] = None


    # format DF
    api_df = pd.DataFrame(api_data)

    return api_df


#-------------------------------------------------------------
# Process ACANO schedules
# - returns DataFrame structure 
#-------------------------------------------------------------
def import_acano_schedule(toolcfg, acano_json):

    curr_dt = datetime.today()
    
    api_data = get_api_data_structure(toolcfg, 'ATC')
   
    for idx in range(len(acano_json)):

        # exclude data where 'No Result' is zero
        if acano_json[idx]["noresult"] == 0:            
            continue

        # only retrieve up to 2yrs worth of data
        tmstp = acano_json[idx]["timestamp"]
        if tmstp:
            if (curr_dt.year - int(tmstp[:4])) > 2:      
                break

        for column, data in acano_json[idx].items():
            if column in api_data:
                api_data[column].append(data)


    # create dataframe          
    api_df = pd.DataFrame(api_data)

    return api_df


#-------------------------------------------------------------
# Connect to ACANO 
# - returns json object 
#-------------------------------------------------------------
def get_acano_schedule(toolcfg, user, pwd, kpi, parms):

    req = None
    url = get_url(toolcfg, kpi, parms)
    
    try:
        req = requests.get(url, auth=(user, pwd))

        if not req.status_code == requests.codes.ok:
            req_msg = api_status_code_desc(req)
            kpilog.error("ACANO API ERROR - {0}".format(req_msg))
            return None
            
    except Exception as e:
        kpilog.error("ACANO API ERROR - {0}".format(api_status_code_desc(e.status_code)))

    kpilog.info("ACANO Connection Status: OK")
    
    return req.json()


#-------------------------------------------------------------
# Import raw data using API for given tool 
# - returns DataFrame structure 
#-------------------------------------------------------------
def import_from_api(toolcfg, tool, kpi, parms=None):

    import_df = None

    user = config.autokpi["auth"]["user"]
    pwd = config.autokpi["auth"]["password"]

    if tool == 'JIRA':
        jra = get_jira_client(toolcfg, user, pwd, kpi)
        if jra:
            import_df = get_jira_issues(toolcfg, jra, kpi)
        
    elif tool == 'CDETS':
        qddts_json = get_qddts_data(toolcfg, kpi)
        if qddts_json:
            import_df = process_qddts_results(toolcfg, qddts_json)

    elif tool == 'ACANO':
        if not parms:
            kpilog.error("ACANO API ERROR - No schedule input for data retrieval")
        
        user = toolcfg["user"]
        pwd = toolcfg["password"]
        
        acano_json = get_acano_schedule(toolcfg, user, pwd, kpi, parms)
        if acano_json:
            import_df = import_acano_schedule(toolcfg, acano_json)


    #savecsv = str.join('',[kpi, '_raw.csv'])
    #import_df.to_csv(savecsv, sep=',')

    if len(import_df) > 0:
        kpilog.info("Imported records: {}".format(len(import_df)))

    return import_df
