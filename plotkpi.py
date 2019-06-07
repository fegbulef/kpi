#!/usr/local/bin/python

"""********************************************************************
Created by:   Fiona Egbulefu (Contractor)

Created date: 23 April 2019

Description:  Plot KPI charts
             
********************************************************************"""

import os
import sys
import time

import config   # user defined module

try:
    import xlrd
    import numpy as np
    import pandas as pd

    import matplotlib 
    matplotlib.use('Agg')
    
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker
    
except ImportError:
    print("Please make sure the following modules are installed: 'pandas'; 'matplotlib'")
    sys.exit(-1)



#----------------------------------------------------------------
# Setup Cisco fonts
# return fontproperties
#----------------------------------------------------------------
def get_font():

    cwd = os.getcwd()
    fontpath = os.path.join(cwd, config.autokpi["fontdir"], "CiscoSansTTRegular.ttf")
    fontproperties = matplotlib.font_manager.FontProperties(fname=fontpath)
    
    return fontproperties

    
#----------------------------------------------------------------
# Setup plot: label font and fontsize
# return Plot Figure
#----------------------------------------------------------------
def setup_plot(kpi, chart_title, xlim):

    fig, ax1 = plt.subplots(figsize=(9,7))

    plt.grid('on', linestyle='--', alpha=0.5)
        
    # set title and label sizes
    #plt.rc('font', family='Calibri')
    fontproperties = get_font()

    plt.title(chart_title, color='black', fontproperties=fontproperties, size=14)
    
    plt.rc('xtick', labelsize=10)
    plt.rc('ytick', labelsize=10)
    
    if not kpi == 'ATC':
        plt.xlim(-0.35, xlim)
        
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
    elif kpi == 'AllCFD':
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
        figname = str.join('', [kpi, '_', product, figname, ext, '.png'])

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

    print("\nPlotting chart", kpi, project_code, "for", xaxis_str, "......")

    try:
        
        plt, fig, ax1 = setup_plot(kpi, chart_title, len(df))

        # set bar constants
        bar_width = 0.35
        opacity = 0.4

        #************************************
        # plot open/closed defects as bars
        #************************************
        
        index = df.index.values
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

        yplt1 = plt.ylabel("Defects", fontsize=12)
        yplt1.set_bbox(dict(facecolor='black', alpha=0.7))
        yplt1.set_color('white')
 
        ax1.set_xticks(index+bar_width/2)

        if 'Months' in xaxis_str:
            ax1.set_xticklabels(df[xaxis], rotation=90)
        else:
            ax1.set_xticklabels(df[xaxis])

        ax1.set_ylim(bottom=0)
        
        ax1bottom, ax1top = ax1.get_ylim()
        if ax1top <= 10:
            ax1.yaxis.set_major_locator(ticker.MultipleLocator(1))
        else:
            ax1.yaxis.set_major_formatter(ticker.FormatStrFormatter("%d"))
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

        yplt2 = plt.ylabel("MTTR(days)", fontsize=12)
        yplt2.set_bbox(dict(facecolor='darkblue', alpha=0.7))
        yplt2.set_color('white')
        
        ax2.plot(df[xaxis], mttr, label="MTTR(Days)", color='darkblue')
        ax2.tick_params(axis='y', labelcolor='darkblue')

        #ax1bottom, ax1top = ax1.get_ylim()
        ax2.set_ylim(bottom=0, top=500)

        #*********************
        # plot MTTR target
        #*********************
        
        ax2.plot(df[xaxis], mttrdays, label="MTTR Target(28 Days)", linestyle='--', color='darkblue')

        #****************
        # setup legend
        #****************
        
        h1, l1 = ax1.get_legend_handles_labels()
        labels_order = [1,2,0]  # Open, Closed, Open Defects

        h2, l2 = ax2.get_legend_handles_labels()

        ax2.legend([h1[i] for i in labels_order]+h2, [l1[i] for i in labels_order]+l2, fontsize=10, loc='upper right')

        #*************
        # save chart
        #*************

        fig.tight_layout()
         
        savefile = get_filename(kpi, xaxis_str, project_code, istest)
        
        fig.savefig(savefile)
        plt.close(fig)

        #plt.show()

    except Exception as e:
        print("ERROR - {}".format(str(e)))
        print("ERROR - Could not create chart for", kpi, project_code)
        return None

    return savefile


#-------------------------------------
# Plot ATC charts 
#-------------------------------------
def plot_atc_chart(df, product, chart_title, chart_key, istest=False):
    
    print("\nPlotting ATC chart for", product, chart_key, "......")

    try:

        max_xlim = df["rundate_int"].max()

        index = df.index.values
        xaxis = df["rundate_int"].values.tolist()

        plt, fig, ax1 = setup_plot('ATC', chart_title, max_xlim)  

        #*************#
        # plot tests  #
        #*************#

        plt.xlabel("Test Run Date (and Time)", fontsize=12)
 
        if chart_key.upper() == 'MAIN':

            figname = 'AllTests'
            color = 'blue'
            yaxis = df["jobs_count"].values.tolist()
            ax1.set_ylabel("ATC Tests Implemented", fontsize=12)

            ax1.scatter(xaxis, yaxis, c=color, s=15, marker='o')

        elif '%' in chart_key.upper():      # '%Passes'

            figname = '%Passes'
            color = 'green'
            yaxis = df["%passed"].values.tolist()
            ax1.set_ylabel("% ATC Passes", fontsize=12)

            ax1.scatter(xaxis, yaxis, c=color, s=15, marker='o')

        else:                               # 'Passes'

            figname = 'Passes'
            yaxis1 = df["passed"].values.tolist()
            yaxis2 = df["jobs_count"].values.tolist()
            ax1.set_ylabel("ATC Passes and Tests Run", fontsize=12) 
            
            ax1.scatter(xaxis, yaxis1, label='Pass', color='green', s=10, marker='o')
            ax1.scatter(xaxis, yaxis2, label='Total Run', color='blue', s=10, marker='o')

            plt.legend(fontsize=10, loc='upper left')


        # set xaxis intervals
        interval = len(df)//18
        ax1.set_xlim(xaxis[0], xaxis[-1]+1)
        ax1.xaxis.set_major_locator(ticker.MultipleLocator(interval))

        # change labels to dates
        xlabels = get_xtick_labels(ax1)
        ax1.set_xticklabels(xlabels, rotation=90)

        fig.tight_layout()
         
        savefile = get_filename('ATC', figname, product, istest)
        fig.savefig(savefile)
        plt.close(fig)

        #plt.show()

    except Exception as e:
        print("ERROR - {}".format(str(e)))
        print("ERROR - Could not create ATC chart for", product, figname)
        return None

    return savefile

