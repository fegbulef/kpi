#!/usr/bin/python3

"""************************************************************************************
Created by:   Fiona Egbulefu (Contractor)

Created date: 12 April 2019

Description:  Configuration setup for tools and codes used in KPI automation.
              The config dictionary is loaded as JSON and used in automation scripts.

************************************************************************************"""


autokpi = {"auth": {"user": "kpi.gen", "password": "UXB20-19.genQ1"},       # authorised user

           "logfile": "kpilog.log",
           "logname": "autokpi",

           "wikiLive": r"https://confluence-eng-gpk2.cisco.com/conf/display/UXB/Dashboard+KPIs",
           "wikiTest": r"https://confluence-eng-gpk2.cisco.com/conf/display/UXB/Test+Dashboard+KPIs",
           "wikilogin": r"https://jira-eng-gpk2.cisco.com/jira/login.jsp",
           
           "fyq": {"Q1": ["AUG","SEP","OCT"], "Q2": ["NOV","DEC","JAN"],    # fiscal year qtrs
                   "Q3": ["FEB","MAR","APR"], "Q4": ["MAY","JUN","JUL"]},

           "datadir": "data",       
           "savedir": "pyout",
           "fontdir": "CiscoFonts", 

           "savedir_test": "output",      
             
           "fyq_start": "01/08/2016",       # Start FYQ 

           "fyqs_to_plot": 14,              
           "months_to_plot": -18,           

           # KPI tools: JIRA - [CFPD, AFCD, IFD]
           "tools": {"JIRA": {"apiserver": "https://jira-eng-gpk2.cisco.com/jira/",
                              
                              "products": ["CLIENT","SERVER","CMM"],
                              "product_column": "Issue key",
                              "priority_column": "Priority",
                              "open_column": "Created",          
                              "closed_column": "Resolved",
                              "id_column": "Issue id",
                              "status_column": "Status",
                              
                              "kpi": {"CFPD": {"wikitext": "Customer-Priority Found Defects",
                                               
                                               "kpi_title": "XXX Customer Found Priority Defects by",
                                               "jql": "project in (CMM, SERVER, CLIENT) " \
                                                        "AND issuetype = Bug " \
                                                        "AND labels = Customer_Priority " \
                                                        "AND created >= 2016-08-01"},
                                      
                                      "IFD": {"wikitext": "Internally Found Defects",
                                              
                                              "kpi_title": "Internally-Found XXX Defects per",
                                              "jql": "project in (CMM, SERVER, CLIENT) " \
                                                        "AND issuetype = Bug " \
                                                        "AND (labels = EMPTY OR labels != customer) " \
                                                        "AND created >= 2016-08-01 " \
                                                        "ORDER BY created ASC, priority DESC, cf[10408] ASC, resolved DESC, assignee ASC"},
                                      
                                      "CFD": {"wikitext": "Customer Found Defects",

                                                 "kpi_title": "XXX JIRA CFDs per",
                                                 "jql": "project in (CMM, SERVER, CLIENT) " \
                                                        "AND issuetype = Bug " \
                                                        "AND labels = customer " \
                                                        "AND created >= 2016-08-01 " \
                                                        "ORDER BY created ASC, priority DESC, cf[10408] ASC, resolved DESC, assignee ASC"}},
                              
                              "xlsheetname": "JIRA Engineering GPK2",
                              "xlcolumns": "A:H",
                              "xldatefmt": "%d/%m/%Y %H:%M:%S",
                              "apidatefmt": "%Y-%m-%dT%H:%M:%S"},
                     
                     #  CDETS - [PSIRT]
                     "CDETS": {"apiserver": "http://wwwin-metrics.cisco.com/cgi-bin/ws/ws_ddts_query_new.cgi?",

                               "products": ["meeting_apps","meetingserver","cmm"],
                               "product_column": "Product",
                               "priority_column": "SIR",
                               "open_column": "OPENED",
                               "closed_column": "CLOSED",
                               "id_column": "Identifier",
                               "id_api": "id",
                               "status_column": "Status",

                               "kpi": {"PSIRT": {"wikitext": "PSIRTs",

                                                 "kpi_title": "XXX PSIRT Defects by",
                                                 
                                                 "query": "expert=Project:CSC.general and PSIRT:Y " \
                                                             "and Product:meeting_apps,meetingserver,cmm " \
                                                             "and SIR:Critical,High,Medium,Low and Status:A,H,I,M,N,O,P,Q,R,S,T,V,W",
                                                 
                                                 "type": "&type=XXX",
                                                 
                                                 "fields": "&fields=Status,Priority,SIR,Product,Headline,OPENED,CLOSED",
                                                 
                                                 "bugs": "fileid=XXX&type=incr&start=ZZZ&numrec=100&fields=Product,SIR,Identifier,Status,OPENED,CLOSED"}},

                               "xlsheetname": "PSIRT",
                               "xlcolumns": "A:J",
                               "xldatefmt": "%y%m%d %H%M%S",
                               "apidatefmt": "%y%m%d %H%M%S"},

                     #  ACANO - [ATC]
                     "ACANO": {"apiserver": "https://atc.uxb.ciscolabs.com/api/batch/?",

                               "user": "KPI",
                               "password": "65wEv7u6sB",

                               "schedules": {"Server": "2", "Client": "125", "SecurityVTP": "151"},
                               "columns": ["description", "jobs_count", "jobs_done", "incomplete", "noresult", "passed", "failed", "crashes"],

                               "open_column": "rundate",    # column for date filtering

                               "kpi": {"ATC": {"wikitext": "Test Automation",

                                               "kpi_title": {"main": "ATC XXX Tests Implemented (last 18 months)",
                                                             "passed": "ATC XXX Passes vs Tests Run (last 18 months)",
                                                             "%passed": "% ATC XXX Passes vs Tests Run (last 18 months)"},

                                               "query": "schedule=XXX&sort(-id)"}},
                            
                               "apidatefmt": "%Y-%m-%dT%H:%M:%S.%f"},

##                     #  BEMS - [Escalations]
##                     "BEMS": {"conn_str": "{user}/{pwd}@{host}:{port}/{service}",
##
##                              "conn_parms": {"user": "BEMS_Query", "pwd": "BEMS_query_227", "host": "173.37.249.61", "port": "1541", "service": "RPAPPPRD.cisco.com"},
##
##                              "columns": ["CASE_NUMBER", "ENGAGEMENT_ID", "ENGAGEMENT_STATUS", "PRODUCT", "PRODUCT_FAMILY", "CREATE_DATE", "CLOSED_DATE"],
##
##                              "open_column": "CREATE_DATE",      # columns for date filtering
##                              "closed_column": "CLOSED_DATE",  #
##
##                              "product_column": "PRODUCT",
##
##                              "products": {"CMA": ["ACANO iOS Client","ACANO PC/MAC Client","Acano webRTC client"],
##                                           "CMS": ["Cisco Meeting Server (CMS)"],
##                                           "CMM": ["CMM (Meeting Management)"]},
##
##                              "kpi": {"BEMS": {"wikitext": "Escalations",
##
##                                               "kpi_title": "Infrastructure Service Requests (SRs), by XXX",
##
##                                               "arraysize": 5000,
##
##                                               "query": "SELECT CASE_NUMBER, ENGAGEMENT_ID, ENGAGEMENT_STATUS, PRODUCT, PRODUCT_FAMILY, " \
##                                                               "CREATE_DATE, CLOSED_DATE " \
##                                                        "FROM BEMS_ENGAGEMENT_DETAILS_VW " \
##                                                        "WHERE INSTR(CASE_NUMBER, 'BEMS') > 0 " \
##                                                        "AND (CREATE_DATE > TO_DATE('07/31/2016', 'MM/DD/YYYY') " \
##                                                               "AND CREATE_DATE < TO_DATE('XXX', 'MM/DD/YYYY')) " \
##                                                        "AND (INSTR(PRODUCT_FAMILY, 'CTS - Conferencing') > 0 OR INSTR(PRODUCT_FAMILY, 'Acano') > 0 "  \
##                                                               "OR (INSTR(PRODUCT, 'CMM') > 0 AND INSTR(PRODUCT_FAMILY, 'CTS - Management') > 0)) " \
##                                                        "ORDER BY CREATE_DATE "}},
##                            
##                              "apidatefmt": "%Y-%m-%d %H:%M:%S.%f"}
##                     
                     }
           }

