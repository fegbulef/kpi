#!/usr/bin/python3

"""************************************************************************************
Created by:   Fiona Egbulefu (Contractor)

Created date: 12 April 2019

Description:  Configuration setup for tools and codes used in KPI automation.
              The config dictionary is loaded as JSON and used in automation scripts.

************************************************************************************"""


autokpi = {"auth": {"user": "fegbulef", "password": "cscApr2019?"},         # authorised user

           "logfile": "kpilog.log",
           "logname": "autokpi",

           "wikiLive": r"https://confluence-eng-gpk2.cisco.com/conf/display/UXB",
           "wikiTest": r"https://confluence-eng-gpk2.cisco.com/conf/display/UXB/Test+KPIs+Page",
           "wikilogin": r"https://jira-eng-gpk2.cisco.com/jira/login.jsp",
           
           "fyq": {"Q1": ["AUG","SEP","OCT"], "Q2": ["NOV","DEC","JAN"],    # fiscal year qtrs
                   "Q3": ["FEB","MAR","APR"], "Q4": ["MAY","JUN","JUL"]},

           "datadir": "data",       
           "savedir": "pyout",
           "fontdir": "CiscoFonts", 

           "savedir_test": "output",      
             
           "fyq_start": "01/08/2016",       # Start FYQ 

           "fyqs_to_plot": 14,              
           "months_to_plot": -19,           

           # KPI tools: JIRA - [CFPD, AFCD, AIFD]
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
                                               "jql": '''project in (CMM, SERVER, CLIENT)
                                                        AND issuetype = Bug
                                                        AND labels = Customer_Priority
                                                        AND created >= 2016-08-01'''},
                                      
                                      "IFD": {"wikitext": "Internally Found Defects",
                                              
                                              "kpi_title": "Internally-Found XXX Defects per",
                                              "jql": '''project in (CMM, SERVER, CLIENT)
                                                        AND issuetype = Bug
                                                        AND (labels = EMPTY OR labels != customer)
                                                        AND created >= 2016-08-01
                                                        ORDER BY created ASC, priority DESC, cf[10408] ASC, resolved DESC, assignee ASC'''},
                                      
                                      "AllCFD": {"wikitext": "Customer Found Defects",

                                                 "kpi_title": "XXX JIRA CFDs per",
                                                 "jql": '''project in (CMM, SERVER, CLIENT)
                                                            AND issuetype = Bug
                                                            AND labels = customer
                                                            AND created >= 2016-08-01
                                                            ORDER BY created ASC, priority DESC, cf[10408] ASC, resolved DESC, assignee ASC'''}},
                              
                              "xlsheetname": "JIRA Engineering GPK2",
                              "xlcolumns": "A:H",
                              "xldatefmt": "%d/%m/%Y %H:%M:%S",
                              "apidatefmt": "%Y-%m-%dT%H:%M:%S"},
                     
                     #  CDETS - [PSIRTS]
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
                                                 
                                                 "query": "expert=Project:CSC.general and PSIRT:Y and Product:meeting_apps,meetingserver,cmm and SIR:Critical,High,Medium,Low and Status:A,H,I,M,N,O,P,Q,R,S,T,V,W",
                                                 
                                                 "type": "&type=XXX",
                                                 
                                                 "fields": "&fields=Status,Priority,SIR,Product,Headline,OPENED,CLOSED",
                                                 
                                                 "bugs": '''fileid=XXX&type=incr&start=ZZZ&numrec=100&fields=Product,SIR,Identifier,Status,OPENED,CLOSED'''}},

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
                            
                               "apidatefmt": "%Y-%m-%dT%H:%M:%S.%f"}
                     
                     }
           }

