#!/usr/bin/python3

"""********************************************************************
Created by:   Fiona Egbulefu (Contractor)

Created date: 23 April 2019

Description:  Plot KPI charts
             
********************************************************************"""

import os
import sys
import time

# user defined module
import util
import config

try:
    import xlrd
    import numpy as np
    import pandas as pd

    import matplotlib as mpl
    mpl.use('Agg')
    
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker
    
except ImportError:
    print("Please make sure the following modules are installed: 'pandas'; 'matplotlib'")
    sys.exit(-1)


kpilog = util.get_logger(config.autokpi["logname"])


#----------------------------------------------------------------
# Setup Cisco fonts
# - returns Cisco FontProperties
#----------------------------------------------------------------
def get_custom_font():

    cwd = os.getcwd()
    fontpath = os.path.join(cwd, config.autokpi["fontdir"], "CiscoSansTTRegular.ttf")
    fontproperties = mpl.font_manager.FontProperties(fname=fontpath, size=10)

    return fontproperties

    
#----------------------------------------------------------------
# Setup plot: label fonts and fontsize
# return Plot Figure
#----------------------------------------------------------------
def setup_plot(kpi, chart_title, xlim):

    # create plot
    fig, ax1 = plt.subplots(figsize=(8,5))

    if kpi == 'ATC':
        ax1.grid(True, which='major', axis='both', linestyle='--', alpha=0.5)
        #ax1.yaxis.grid('on', which='major', linestyle='--', alpha=0.5)
        ax1.spines['right'].set_visible(False)
        
    else:
        ax1.grid(True, which='major', axis='y', linestyle='--', alpha=0.5)
        plt.xlim(-0.7, xlim)

    ax1.spines['top'].set_visible(False)

     # set custom fonts and label sizes
    custom_font = get_custom_font()

    #if kpi == 'ATC':
    #    plt.title(chart_title, color='black', fontproperties=fontproperties)

    ax1.xaxis.get_label().set_fontproperties(custom_font)
    ax1.yaxis.get_label().set_fontproperties(custom_font)

    for label in (ax1.get_xticklabels() + ax1.get_yticklabels()):
        label.set_fontproperties(custom_font)    
        
    return plt, fig, ax1


#----------------------------------------------------------------
# Convert excel date to datetime.date
# return datetime
#----------------------------------------------------------------
def convert_date(d):
    return xlrd.xldate.xldate_as_datetime(d, 0)


#----------------------------------------------------------------
# Setup date labels for plot
# return list (dates as strings)
#----------------------------------------------------------------
def get_xtick_labels(ax1):

    xticks = ax1.get_xticks().tolist()
    ax1.set_xticklabels(xticks)

    xticklabels = [float(label.get_text()) for label in ax1.get_xticklabels()]

    xlabels = []
    for i in range(len(xticklabels)):
        dt = pd.to_datetime(convert_date(xticklabels[i]), format="%Y-%m-%d")
        dt = dt.strftime("%d-%b-%Y")
        xlabels.append(dt)
            
    return xlabels


#----------------------------------------------------------------
# Get bar labels (xopen/xclosed) and Line plot label (xdefects)  
#----------------------------------------------------------------
def get_chart_labels(kpi):

    axopen = ''

    # JIRA kpis
    if kpi == 'IFD':
        axopen = 'All Defects Opened'
    elif kpi == 'CFPD':
        axopen = 'Customer-Priority Defects Opened'
    elif kpi == 'CFD':
        axopen = 'CFDs Opened'
       
    # CDETS kpis
    elif kpi == 'PSIRT':
        axopen = 'PSIRT Defects Opened'    
    else:
        pass

    axclosed = axopen.replace('Opened', 'Closed')
    axdefects = str.join(' ', ['Current', axopen])
       
    return axopen, axclosed, axdefects


#----------------------------------------------------------------
# Derive chart name
# return string (filename)
#----------------------------------------------------------------
def get_filename(kpi, figname, product, istest):

    ext = '_Test' if istest else ''  # run from test module
    
    if kpi == 'ATC':
        if figname in ['%', '']:
            figname = str.join('', ['ATC_', figname, product, 'Passes', ext, '.png'])
        else:
            figname = str.join('', ['ATC_', product, figname, ext, '.png'])

    else:
        ext = str.join('',['_', figname, ext, '.png'])
        
        if 'All' in figname:
            figname = str.join('', [kpi, ext])
        else:
            figname = str.join('', [kpi, '_', product, ext])
            
    cwd = os.getcwd()
    savedir = config.autokpi["savedir_test"] if istest else config.autokpi["savedir"]
    filename = os.path.join(cwd, savedir, figname)

    if os.path.exists(filename):
        os.remove(filename)
        time.sleep(2)   # make sure file is deleted 

    return filename


#----------------------------------------------------------------
# Plot KPI chart: for JIRA, PSIRT, CDETS 
#----------------------------------------------------------------
def plot_kpi_chart(df, project_code, chart_title, kpi, xaxis_str, istest=False):
    
    if 'Months' in xaxis_str:
        xaxis = 'Months'
    else:
        xaxis = 'FYQ'

    fig = None

    kpilog.info("Plotting chart {0} {1} for {2} ......".format(kpi, project_code, xaxis_str))

    try:
        
        plt, fig, ax1 = setup_plot(kpi, chart_title, len(df))

        # set bar constants
        bar_width = 0.35
        opacity = 0.4

        #************************************
        # plot open/closed defects as bars
        #************************************
        
        index = df.index.values - (bar_width/2)
        axopen, axclosed, axdefects = get_chart_labels(kpi)
        
        opencnt = df["OpenCnt"].values.tolist()
        closedcnt = df["ClosedCnt"].values.tolist()
        opendefects = df["OpenDefects"].values.tolist()
        mttr = df["MTTR"].values.tolist()
        mttrdays = [28]*len(mttr)

        rects1 = ax1.bar(index, opencnt, bar_width,
                        alpha=opacity, color='red',
                        label=axopen)
        
        rects2 = ax1.bar(index+bar_width, closedcnt, bar_width,
                        alpha=opacity, color='green',
                        label=axclosed)

        if kpi == 'PSIRT':
            yplt1 = plt.ylabel("PSIRT Defects")
        else:
            yplt1 = plt.ylabel("Defects")
            
        yplt1.set_bbox(dict(facecolor='black', alpha=0.7))
        yplt1.set_color('white')

        # format xaxis
        ax1.set_xticks(index)   #+bar_width/2)
        ax1.set_xticklabels(df[xaxis], rotation=90)
        
        # format yaxis
        yticks = ax1.get_yticks().tolist()

        if max(yticks) >= max(opendefects):
            ax1_ylim = max(yticks)
        else:
            ax1_ylim = max(opendefects)
       
        ax1.yaxis.set_major_formatter(ticker.FormatStrFormatter("%d"))
        if ax1_ylim <= 10:
            ax1_ylim = round(ax1_ylim)
            ax1.yaxis.set_major_locator(ticker.MultipleLocator(1))

        ax1.set_ylim(bottom=0, top=ax1_ylim)
 
        for t in ax1.yaxis.get_majorticklabels():
            if t == 0:
                t.set_visible(False)

                
        #**********************
        # plot OpenDefects
        #**********************
        
        ax1.plot(df[xaxis], opendefects, label=axdefects, color='black')

        #****************
        # plot MTTR
           #****************

        ax2 = ax1.twinx()
        ax2.spines['top'].set_visible(False)

        yplt2 = plt.ylabel("MTTR(days)")
        yplt2.set_bbox(dict(facecolor='darkblue', alpha=0.7))
        yplt2.set_color('white')
        
        ax2.plot(df[xaxis], mttr, label="MTTR(Days)", color='darkblue')
        ax2.tick_params(axis='y', labelcolor='blue')

        # calibrate MTTR plot
        yticks = ax2.get_yticks().tolist()
        ax2_ylim = max(yticks)

        ax2.yaxis.set_major_formatter(ticker.FormatStrFormatter("%d"))
        if ax2_ylim <= 10:
            ax2_ylim = 10
            ax2.yaxis.set_major_locator(ticker.MultipleLocator(1))

        # calibrate MTTR
        max_mttr = ax2_ylim
        
        if ax1_ylim <= 10:
            if ax2_ylim > 250:
                max_mttr = 250
        else:
            if ax2_ylim > 700:
                max_mttr = 700 if 10*(ax1_ylim) > 700 else 10*(ax1_ylim) 
                
        ax2.set_ylim(bottom=0, top=max_mttr)
 
        for t in ax2.yaxis.get_majorticklabels():
            if t == 0:
                t.set_visible(False)
                

        #*********************
        # plot MTTR target
        #*********************

        mttr_target = ''
        if kpi == 'PSIRT':
            mttr_target = "PSIRT MTTR Target(28 Days)"
        else:
            mttr_target = "MTTR Target(28 Days)"
            
        ax2.plot(df[xaxis], mttrdays, label=mttr_target, linestyle='--', color='darkblue')

        #****************
        # setup legend      NO LONGER REQUIRED
        #****************
        
##        h1, l1 = ax1.get_legend_handles_labels()
##        labels_order = [1,2,0]      # Open, Closed, Open Defects
##
##        h2, l2 = ax2.get_legend_handles_labels()
##
##        # set MTTR labels to 'blue'
##        leg = ax2.legend([h1[i] for i in labels_order]+h2, [l1[i] for i in labels_order]+l2, fontsize=8, loc='upper right')
##        for text in leg.get_texts():
##            if 'MTTR' in text.get_text():
##                text.set_color('darkblue')
            
        #*************
        # save chart
        #*************

        fig.tight_layout()
         
        savefile = get_filename(kpi, xaxis_str, project_code, istest)
        fig.savefig(savefile)

        #plt.show()

    except Exception as e:
        
        kpilog.error("Could not create chart for {0} {1} - {2}".format(kpi, project_code, format(str(e))))
        return None
    

    finally:
        if fig: plt.close(fig)
        

    return savefile


#-------------------------------------
# Plot ATC charts 
#-------------------------------------
def plot_atc_chart(df, product, chart_title, chart_key, istest=False):

    fig = None
    
    kpilog.info("Plotting ATC chart for {0} {1}......".format(product, chart_key))

    try:

        index = df.index.values
        xaxis = df["rundate_int"].values.tolist()

        plt, fig, ax1 = setup_plot('ATC', chart_title, xaxis[-1])  

        #*************#
        # plot tests  #
        #*************#

        plt.xlabel("Test Run Date (and Time)")
 
        if chart_key.upper() == 'MAIN':

            figname = 'Tests'
            color = 'blue'
            yaxis = df["jobs_count"].values.tolist()
            ax1.set_ylabel("ATC Tests Implemented")

            ax1.scatter(xaxis, yaxis, c=color, s=15, marker='o')

        elif '%' in chart_key.upper():      # '%Passes'

            figname = '%'
            color = 'green'
            yaxis = df["%passed"].values.tolist()
            ax1.set_ylabel("% ATC Passes")

            ax1.scatter(xaxis, yaxis, c=color, s=15, marker='o')

        else:                               # 'Passes'

            figname = ''
            yaxis1 = df["passed"].values.tolist()
            yaxis2 = df["jobs_count"].values.tolist()
            ax1.set_ylabel("ATC Passes and Tests Run") 
            
            ax1.scatter(xaxis, yaxis1, label='Pass', color='green', s=10, marker='o')
            ax1.scatter(xaxis, yaxis2, label='Total Run', color='blue', s=10, marker='o')

            plt.legend(loc='upper left')


        # set xaxis intervals
        interval = len(df)//18
        ax1.set_xlim(xaxis[0], xaxis[-1]+1)
        ax1.xaxis.set_major_locator(ticker.MultipleLocator(interval))

        # change xaxis labels to dates
        xlabels = get_xtick_labels(ax1)
        ax1.set_xticklabels(xlabels, rotation=90)

        # format y axis
        yticks = ax1.get_yticks().tolist()
        maxy = max(yticks)
        ax1.set_ylim(bottom=0, top=maxy)

        fig.tight_layout()
         
        savefile = get_filename('ATC', figname, product, istest)
        fig.savefig(savefile)

        #plt.show()

    except Exception as e:

        kpilog.error("Could not create ATC chart for {0} - {1}".format(product, format(str(e))))
        return None


    finally:
        if fig: plt.close(fig)
        

    return savefile

