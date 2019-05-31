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
    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker
    
except ImportError:
    print("Please make sure the following modules are installed: 'pandas'; 'matplotlib'")
    sys.exit(-1)


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


#-------------------------------------
# Plot KPI chart 
#-------------------------------------
def plot_kpi_chart(df, project_code, chart_title, kpi, xaxis_str, istest=False):
    
    if 'Months' in xaxis_str:
        xaxis = 'Months'
    else:
        xaxis = 'FYQ'

    print("\nPlotting chart", kpi, project_code, "for", xaxis_str, "......")

    try:
        fig, ax1 = plt.subplots(figsize=(10,8))

        # set font family and tick label sizes
        plt.rc('font', family='Calibri')
        plt.rc('xtick', labelsize=14)
        plt.rc('ytick', labelsize=14)

        # set constants for chart
        bar_width = 0.35
        opacity = 0.4

        plt.grid('on', linestyle='--', alpha=0.5)

        plt.xlim(left=-0.35)
        plt.xlim(right=len(df))

        plt.title(chart_title, color='black', fontsize=18)

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

        yplt1 = plt.ylabel("Defects", fontsize=16)
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

        yplt2 = plt.ylabel("MTTR(days)", fontsize=16)
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

        ax2.legend([h1[i] for i in labels_order]+h2, [l1[i] for i in labels_order]+l2, fontsize=12, loc='upper right')

        
        fig.tight_layout()

        #*************
        # save chart
        #*************

        ext = ''
        if istest:              # run from test module
            ext = '_Test'

        ext = str.join('',['_', xaxis_str, ext, '.png'])
        
        if 'All' in xaxis_str:
            figname = str.join('', [kpi, ext])
        else:
            figname = str.join('', [kpi, '_', project_code, ext])
            
        cwd = os.getcwd()
        savefile = os.path.join(cwd, config.autokpi["savedir"], figname)

        if os.path.exists(savefile):
            os.remove(savefile)
            time.sleep(2)   # make sure file is deleted 
            
        fig.savefig(savefile)
        plt.close(fig)

        #plt.show()

    except Exception as e:
        print("ERROR - {}".format(str(e)))
        print("ERROR - Could not create chart for", kpi, project_code)
        return None

    return savefile

