#!/usr/bin/python3

"""********************************************************************
Created by:   Fiona Egbulefu (Contractor)

Created date: 07 May 2019

Description:  Export KPI charts to Confluence (Wiki) page

********************************************************************"""

import os
import sys
import time
import argparse

import util   # user defined
import config # 

from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

from xvfbwrapper import Xvfb


# setup log
wikilog = util.setup_logger("wikilog", "pyout/wikilog.log")


#-----------------------------------------------
# Startup browser (Firefox)
# - returns browser object
#-----------------------------------------------
def start_browser():
    
    ff_browser = webdriver.Firefox()
    ff_browser.implicitly_wait(10)
    ff_browser.maximize_window()

    return ff_browser


#-----------------------------------------------
# Get Wiki page
# - returns Webpage object
#-----------------------------------------------
def get_wikipage(url):

    browser = None

    try:                       
        browser = start_browser()
        browser.get(url)

    except Exception as e:                         
        wikilog.error("Unable to access Confluence: {}".format(str(e)))
        if not browser is None:
            browser.quit()

    return browser


#-----------------------------------------------
# Access Wiki page  
# - returns True/False (logged in)
#-----------------------------------------------
def log_into_wiki(browser, auth_user, auth_pwd):

    if not browser.find_element_by_name("login"):                   # test for login page
        return True

    try:
        # access login elements
        username_txt = browser.find_element_by_name("os_username")
        password_txt = browser.find_element_by_name("os_password")
        login_btn = browser.find_element_by_name("login")

        # send login details
        username_txt.send_keys(auth_user)
        password_txt.send_keys(auth_pwd)
        login_btn.click()

        time.sleep(3)

        # check login successful
        loggedin = browser.find_element_by_name("ajs-page-title")   # Expecting KPIs 
        
        if loggedin:
            if "KPI" in loggedin.get_attribute("content"):
                wikilog.info("User {0} Login: OK".format(auth_user))
                return True
            
            else:
                wikilog.error("Unable to access Confluence; Check user credentials")
                
            
    except Exception as e:
        wikilog.error("Unable to access Confluence {}".format(str(e)))

    return False


#-------------------------------------------------------------
# Get partial link text from config 
# - returns dict (kpi: wikilink text)  
#-------------------------------------------------------------
def get_config_linktext():

    kpilinks = {}
    
    for tool in config.autokpi["tools"]:
        kpis = config.autokpi["tools"][tool]["kpi"]

        for kpi in kpis:
            if kpi == 'SWDL':       # assign wikitext by product
                for product in kpis[kpi]["wikitext"]:
                    kpilinks[kpi + '_' + product] = kpis[kpi]["wikitext"][product]
            else:
                kpilinks[kpi] = kpis[kpi].get("wikitext", None)
            

    return kpilinks


#--------------------------------------------------------------------------
# Construct line of text for the current run 
# - returns strings: monthly_run_desc, quarterly_run_desc, last_run_month
#--------------------------------------------------------------------------
def get_kpi_text_update():

    # construct 'by month' text 
    months = util.get_kpi_months(None, None)                    # default to current run months

    firstmth = datetime.strptime(months[0], "%b-%y")
    firstdt = firstmth.strftime("%B %Y")
    lastmth = datetime.strptime(months[-1], "%b-%y")
    lastdt = lastmth.strftime("%B %Y") 
        
    by_month_text = ' '.join(['from', firstdt, 'to', lastdt])

    # construct 'by fyq' text
    start_dt, end_dt = util.get_kpi_fyq_start_end(None, None)   # default to current run dates
    months = util.get_kpi_months(start_dt, end_dt)
    fyq = util.get_month_fyq(months)

    fyq = list(set(fyq))                # get distinct values
    fyq.sort()
    if not util.is_fyq_start(end_dt):   # not reporting at start of fyq
        fyq = fyq[:-1]

    first_fyq, last_fyq = fyq[0], fyq[-1]

    by_fyq_text = ' '.join(['from', first_fyq, 'to', last_fyq])
    
        
    return by_month_text, by_fyq_text, lastdt


#--------------------------------------------------------------------------
# Get SWDL kpi text 
# - returns dictionary of texts
#--------------------------------------------------------------------------
def get_swdl_kpi_text():

    swdl_kpi_text = {}

    # import swdl data
    swdl = config.autokpi["tools"]["SWDL"]
    xlfile = os.path.join(config.autokpi["datadir"], swdl["swdlfile"])
    xlsheetname = swdl["xlsheetname"]
    
    swdl_df = util.get_xl_df(xlfile, xlsheetname)

    if swdl_df is None:
        wikilog.error("Unable to access SWDL data")
        return None

    # get df dates
    start_dt, end_dt = util.get_df_start_end_dates(swdl_df, "Download Date and Time")
   
    # set period dates
    mth = datetime.strftime(end_dt, "%B %Y")
    swdl_kpi_text["End"] = mth   # End month
    swdl_kpi_text["All"] = ''.join([" from August 2016 to ", swdl_kpi_text["End"], "."])    # All months from August 2016

    dt = util.get_next_date(datetime(end_dt.year, end_dt.month, 1), -17, 0)
    mth = datetime.strftime(dt, "%B %Y")
    swdl_kpi_text["18"] = ''.join([" from ", mth, " to ", swdl_kpi_text["End"], "."])     # 18 months

    dt = util.get_next_date(datetime(end_dt.year, end_dt.month, 1), -11, 0)
    mth = datetime.strftime(dt, "%B %Y")
    swdl_kpi_text["12"] = ''.join([" from ", mth, " to ", swdl_kpi_text["End"], "."])     # 12 months
    
        
    return swdl_kpi_text


#-------------------------------------------------------------
# For given kpi/link, parse HTML images and update 
# - returns True/False (images updated)  
#-------------------------------------------------------------
def navigate_to_kpi(browser, linktext, wikitype):

    try:
        kpipage = None
        
        # go to kpi page link
        linkpages = browser.find_elements_by_partial_link_text(linktext)

        for linkpage in linkpages:
            if wikitype == 'Test' and not linkpage.text[:4] == 'Test':
                continue

            if linkpage.text[:3] == 'Old':      # ignore 'original' kpi wikipages
                continue

            kpipage = linkpage
            wikilog.info("Navigate to {} ....".format(kpipage.text))    

            browser.execute_script("arguments[0].click();", kpipage)    # click link
            time.sleep(3)
            break
            
        # validate page details
        if not kpipage or not linktext in browser.title:
            wikilog.error("Unable to navigate to {}".format(linktext))
            return False
        
    except Exception as e:
        wikilog.error("Unable to navigate to {0}: {1}".format(linktext, str(e)))
        return False


    return True

    
#-------------------------------------------------------------
# Get full path name of chart to replace image 
# - returns string (full path of chart)
#-------------------------------------------------------------
def get_kpifile(kpi, img_name):

    kpifile = None

    # access folder of saved charts
    cwd = os.getcwd()
    kpisavedir = os.path.join(cwd, config.autokpi["savedir"])

    for file in os.listdir(kpisavedir):
        if not kpi in file and not kpi == "Dashboard": continue     # allow update of 'KPI Dashboard'
        
        if (img_name in "CMSA-Month.PNG" and file == "CPFD_AllMonths.png") \
           or (img_name in "CMSA-Quarter.PNG" and file == "CPFD_AllFYQ.png") \
           or (img_name in "CMS-Month.PNG" and file == "CPFD_CMS_Months.png") \
           or (img_name in "CMS-Quarter.PNG" and file == "CPFD_CMS_FYQ.png") \
           or (img_name in "CMA-Month.PNG" and file == "CPFD_CMA_Months.png") \
           or (img_name in "CMA-Quarter.PNG" and file == "CPFD_CMA_FYQ.png") \
           or (img_name in "All-CFDs-Month.PNG" and file == "CFD_AllMonths.png") \
           or (img_name in "All-CFDs-Qtr.PNG" and file == "CFD_AllFYQ.png") \
           or (img_name in "CMS-CFDs-Month.PNG" and file == "CFD_CMS_Months.png") \
           or (img_name in "CMS-CFDs-Qtr.PNG" and file == "CFD_CMS_FYQ.png") \
           or (img_name in "CMA-CFDs-Month.PNG" and file == "CFD_CMA_Months.png") \
           or (img_name in "CMA-CFDs-Qtr.PNG" and file == "CFD_CMA_FYQ.png") \
           or (img_name in "CMM-CFDs-Month.PNG" and file == "CFD_CMM_Months.png") \
           or (img_name in "CMM-CFDs-Qtr.PNG" and file == "CFD_CMM_FYQ.png") \
           or (img_name in "CMSAM-PSIRT.PNG" and file == "PSIRT_AllMonths.png") \
           or (img_name in "CMS-PSIRT.PNG" and file == "PSIRT_CMS_Months.png") \
           or (img_name in "CMA-PSIRT.PNG" and file == "PSIRT_CMA_Months.png") \
           or (img_name in "CMM-PSIRT.PNG" and file == "PSIRT_CMM_Months.png") \
           or (img_name in "All-Month.PNG" and file == "IFD_AllMonths.png") \
           or (img_name in "All-Qtr.PNG" and file == "IFD_AllFYQ.png") \
           or (img_name in "CMS-IFD-Month.PNG" and file == "IFD_CMS_Months.png") \
           or (img_name in "CMS-IFD-Qtr.PNG" and file == "IFD_CMS_FYQ.png") \
           or (img_name in "CMA-IFD-Month.PNG" and file == "IFD_CMA_Months.png") \
           or (img_name in "CMA-IFD-Qtr.PNG" and file == "IFD_CMA_FYQ.png") \
           or (img_name in "CMM-IFD-Month.PNG" and file == "IFD_CMM_Months.png") \
           or (img_name in "CMM-IFD-Qtr.PNG" and file == "IFD_CMM_FYQ.png") \
           or (img_name in "CMA-1D.PNG" and file == "SWDL_CMA_1D.png") \
           or (img_name in "CMA-18M.PNG" and file == "SWDL_CMA_18M.png") \
           or (img_name in "CMA-12W.PNG" and file == "SWDL_CMA_12W.png") \
           or (img_name in "CMA-AllW.PNG" and file == "SWDL_CMA_allW.png") \
           or (img_name in "CMS-1D.PNG" and file == "SWDL_CMS_1D.png") \
           or (img_name in "CMS-18M.PNG" and file == "SWDL_CMS_18M.png") \
           or (img_name in "CMS-12W.PNG" and file == "SWDL_CMS_12W.png") \
           or (img_name in "CMS-AllW.PNG" and file == "SWDL_CMS_allW.png") \
           or (img_name in "CMM-1D.PNG" and file == "SWDL_CMM_1D.png") \
           or (img_name in "CMM-18M.PNG" and file == "SWDL_CMM_18M.png") \
           or (img_name in "CMM-12W.PNG" and file == "SWDL_CMM_12W.png") \
           or (img_name in "CMM-AllW.PNG" and file == "SWDL_CMM_allW.png") \
           or (img_name in ["ATC-ServerTests.PNG", "ATC-Tests.PNG"] and file == "ATC_ServerTests.png") \
           or (img_name in ["ATC-ServerPasses.PNG", "ATC.PNG"] and file == "ATC_ServerPasses.png") \
           or (img_name in ["ATC-%ServerPasses.PNG", "%ATC.PNG"] and file == "ATC_%ServerPasses.png") \
           or (img_name in ["ATC-ClientTests.PNG", "ATC-Tests-All.PNG"] and file == "ATC_ClientTests.png") \
           or (img_name in ["ATC-ClientPasses.PNG", "ATC-All.PNG"] and file == "ATC_ClientPasses.png") \
           or (img_name in ["ATC-%ClientPasses.PNG", "%ATC-All.PNG", "image2019-7-4_17-2-40.png"] \
               and file == "ATC_%ClientPasses.png"):

           
            kpifile = os.path.join(kpisavedir, file).replace('\\', '\\\\')  # escape backslashes
            wikilog.debug("Chart exists: {}".format(kpifile))
                           
            break
        
    return kpifile


#-------------------------------------------------------------
# Find all images on the page and link to corresponding kpi
# - returns dict (image: new kpi)
#-------------------------------------------------------------
def get_image_kpis(browser, kpi):     

    img_kpi = {}
    
    imgs = browser.find_elements_by_class_name("confluence-embedded-image")

    for img in imgs:
        # get image name from 'title' if it exists 
        if img.get_attribute("title"):      
            img_name = img.get_attribute("title")
        else:
            img_name = img.get_attribute("data-linked-resource-default-alias")

        # find corresponding chart
        kpifile = get_kpifile(kpi, img_name)
        if kpifile:
            img_id = img.get_attribute("data-linked-resource-id")       # unique to each image
            img_kpi[img_id] = (img_name, kpifile)

    return img_kpi


#-------------------------------------------------------------
# Find text descriptions corresponding to all kpi images
# - returns list (web elements)
#-------------------------------------------------------------
def get_kpi_text(browser, linktext, wikitype):     

    kpitext = []
    linktextid = linktext.replace(' ', '')

    xpath = ''.join(["//*[contains(@id, '", linktextid, "')]"])
    imgtxt = browser.find_elements_by_xpath(xpath)

    for txt in imgtxt:
        # get image name from 'title' if it exists
        txtid = txt.get_attribute("id")
        if wikitype == 'Test' and not 'Test' in txtid: continue
        kpitext.append(txtid)
        
    return kpitext


#-------------------------------------------------------------
# Publish Wiki changes
# - returns True/False (updates published)
#-------------------------------------------------------------
def publish_updates(browser, kpi, blnCancel, switch_to_frame):

    if switch_to_frame:
        browser.switch_to.parent_frame()

        if blnCancel:   # cancel editing if no update

            ellipsis = browser.find_element_by_id("rte-button-ellipsis")
            ellipsis.click()
            time.sleep(3)

            revertbtn = browser.find_element_by_id("rte-show-revert")
            revertbtn.click()
            time.sleep(3)

            # confirm revert page
            revert_page_btn = browser.find_element_by_id("qed-discard-button")
            revert_page_btn.click()
            time.sleep(3)

            wikilog.info("All updates canceled!")

            return False
            
        else:
            
            updatepage = browser.find_element_by_id("rte-button-publish")
            updatepage.click()
            time.sleep(3)

            wikilog.info("All {} updates published!".format(kpi))

    else:   # no changes to page

        cancelpage = browser.find_element_by_id("rte-button-cancel")
        if cancelpage.is_displayed():
            cancelpage.click()
            time.sleep(3)
            
        return False


    return True


#-------------------------------------------------------------
# Update text linked to each kpi to reflect current dates  
#-------------------------------------------------------------
def update_kpi_panel_header(browser, kpi, end_month):

    if kpi == "Dashboard":  # no panel header to update
        return True

    panel_menu = False
    upd_header = False

    wikilog.debug("Updating panel header....")

    try:

        headers = browser.find_elements_by_xpath("//table[@class='wysiwyg-macro']")
        time.sleep(3)

        for header in headers:
            if header.get_attribute("data-macro-name"):

                if not header.get_attribute("data-macro-name") == "panel":
                    continue
                
                if header.get_attribute("data-macro-parameters"):
                    if 'KPI' in header.get_attribute("data-macro-parameters"):
                        continue

                    # Found header panel 
                    header.click()
                    time.sleep(3)

                    browser.switch_to.parent_frame()

                    # panel header edit 
                    xpath = "/html/body/div[13]/div[2]/div/a[1]/span[2]"
                    try:
                        panel_menu = WebDriverWait(browser, 8).until(EC.presence_of_element_located((By.XPATH, xpath)))
                        panel_menu.click()               
                        time.sleep(3)

                        # set panel title
                        title = browser.find_element_by_xpath("//*[@id='macro-param-title']")
                        title_txt = title.get_attribute("value")
                        wikilog.debug("...old title: {}".format(title_txt))

                        s = title_txt.split(":")
                        new_title = ''.join([s[0], ': ', end_month])
                        wikilog.debug("...new title: {}".format(new_title))

                        title.clear()
                        time.sleep(3)
                        title.send_keys(new_title)
                        time.sleep(3)

                        upd_header = True
                        break
                
                    except TimeoutException:
                        wikilog.error("Panel menu not displayed - Timeout Exception!")
                

    except Exception as e:
        upd_header = False
        wikilog.error("Unable to update panel header - {}".format(str(e)))
    

    finally:

        if panel_menu:   # panel displayed
            
            if upd_header:  # Save changes
                savebtn = browser.find_element_by_xpath("//*[@id='macro-details-page']/div[2]/button")
                browser.execute_script("return arguments[0].scrollIntoView(true);", savebtn)
                savebtn.click()
            
            else:           # Cancel changes
                cancelbtn = browser.find_element_by_xpath("//*[@id='macro-details-page']/div[2]/a[2]")
                if cancelbtn.is_displayed():
                    browser.execute_script("return arguments[0].scrollIntoView(true);", cancelbtn)
                    cancelbtn.click()

            time.sleep(3)
    
        
    return upd_header


#-------------------------------------------------------------
# Update text linked to each kpi to reflect current dates  
#-------------------------------------------------------------
def update_kpi_text(browser, kpi, linktext, wikitype, by_month_text, by_fyq_text, end_month, swdl_kpi_text):

    blnCancel = False
    switch_to_frame = False

    try:
        # place page in edit mode for update
        editpage = browser.find_element_by_id("editPageLink")
        editpage.click()
        time.sleep(3)

        wikilog.debug("Updating KPI text....")

        # switch to edit frame
        frame = browser.find_element_by_xpath("//iframe[@id='wysiwygTextarea_ifr']")
        browser.switch_to.frame(frame)
        switch_to_frame = True

        panel_month = swdl_kpi_text["End"] if "SWDL" in kpi else end_month

        # update panel header  
        if update_kpi_panel_header(browser, kpi, panel_month):
            wikilog.info("{} panel header updated".format(linktext))

            # switch back to editing frame
            if not kpi == "Dashboard":
                browser.switch_to.frame(frame)

            # find all text elements corresponding to kpis
            xpath = ''.join(["//div[@class='content-wrapper']"])
            divs = browser.find_elements_by_xpath(xpath)
        
            for div in divs:        # div -> h3 -> text
                try:
                    h3 = div.find_element_by_tag_name("h3")
                    if not h3: continue
                except Exception as e:
                    continue

                html = None
                updtext = ""

                # setup kpi text with current dates
                if "SWDL" in kpi:
                    if "August 2016" in h3.text:
                        html = h3.get_attribute("innerHTML").split(",")
                        updtext = ''.join([",", swdl_kpi_text["All"]])
                       
                    elif "18 months" in h3.text:
                        html = h3.get_attribute("innerHTML").split("by month")
                        updtext = ''.join(["by month,", swdl_kpi_text["18"]])
                        
                    elif "12 months" in h3.text:
                        html = h3.get_attribute("innerHTML").split("by week")
                        updtext = ''.join(["by week,", swdl_kpi_text["12"]])

                    else:
                        continue
                        
                else:
                    if "by month" in h3.text:
                        html = h3.get_attribute("innerHTML").split("by month")
                        updtext = ''.join(["by month, ", by_month_text])

                    elif "by financial quarter" in h3.text:
                        html = h3.get_attribute("innerHTML").split("by financial quarter")
                        updtext = ''.join(["by financial quarter, ", by_fyq_text])
                
                    else:
                        continue

                # update text
                if html:
                    htmlupd = ''.join([html[0], updtext])
                    browser.execute_script("arguments[0].innerHTML = arguments[1];", h3, htmlupd)
                    time.sleep(2)

            wikilog.info("All {} kpi texts updated".format(linktext))
             

        else:
            wikilog.error("Unable to update KPI text for {}!".format(linktext))
            blnCancel = True

                
    except Exception as e:
        wikilog.error("Unable to update KPI texts for {0} - {1}".format(linktext, str(e)))
        blnCancel = True
        

    finally:
        publish_updates(browser, kpi, blnCancel, switch_to_frame)


    return 


#-------------------------------------------------------------
# Use file upload function replace image with current kpifile  
# - returns True/False (images updated)  
#-------------------------------------------------------------
def upload_kpi(browser, img, kpifile):

    try:
        actions = ActionChains(browser)
            
        # bring image to view and expand display
        browser.execute_script("return arguments[0].scrollIntoView(true);", img)
        actions.move_to_element(img).click(img).perform()                
        time.sleep(2)

        # uploading new kpi
        fileinputxpath = "//div[@class='plupload html5']"
        fileinputcontainer = browser.find_element_by_xpath(fileinputxpath)
        # make file input accessible
        browser.execute_script('arguments[0].style = ""; arguments[0].style.display = "block"; arguments[0].style.visibility = "visible";', fileinputcontainer)

        fileinput = fileinputcontainer.find_element_by_tag_name("input")    # file input dialog
        fileinput.send_keys(kpifile)
        time.sleep(3)       # allow time for upload

        # confirm changes
        alldone = browser.find_element_by_xpath("//*[@class='aui-button close-button']")
        alldone.click()
        time.sleep(3)

        # close image display 
        closebtn = browser.find_element_by_xpath("//button[@class='cp-control-panel-close cp-icon']")
        closebtn.click()
        time.sleep(3)

        wikilog.info("{} uploaded successfully".format(kpifile))

    except Exception as e:
        wikilog.error("Unable to upload {0} - {1}".format(kpifile, str(e)))
        return False


    return True
    
        
#-------------------------------------------------------------
# Navigate to selected kpi/link, parse HTML images and update 
# - returns True/False (page updated)  
#-------------------------------------------------------------
def update_kpi_page(browser, kpi, linktext, wikitype):

    if not navigate_to_kpi(browser, linktext, wikitype):
        wikilog.error("No kpis updated for {0} - {1}".format(linktext, kpi))
        return False

    #return True     # FOR TEST PURPOSES ONLY!!!!
    
    try:
        
        img_kpi = get_image_kpis(browser, kpi)
        if not img_kpi:
            wikilog.warning("{} - No kpi selected for update".format(kpi))
            return False

        wikilog.info("Prepare page for updates...")

        for img_id, (img_name, kpifile) in img_kpi.items():

            wikilog.debug("Image selected for update: {0} {1}".format(img_name, kpifile))
            css_selector = ''.join(['img[data-linked-resource-id="', img_id, '"]'])
            img = browser.find_element_by_css_selector(css_selector)

            kpi_uploaded = upload_kpi(browser, img, kpifile)
            
            if not kpi_uploaded:

                wikilog.error("Could not upload KPI: {}".format(kpifile))
                wikilog.error("Upload cancelled for {0} - {1}".format(kpi, linktext))

                return False
            
            
    except Exception as e:

        wikilog.error("Unable to upload {0} - {1}".format(kpifile, str(e)))
        return False
 

    return True


#-----------
# M A I N
#-----------

def main(wikitype):

    # get user credentials
    auth_user = config.autokpi["auth"]["user"]
    auth_pwd  = config.autokpi["auth"]["password"]

    # setup url
    if wikitype == 'Test':
        kpi_url = config.autokpi["wikiTest"]
    else:  
        kpi_url = config.autokpi["wikiLive"]

    try:
        wikilog.info("Start Wiki upload: {}....".format(kpi_url))

        # start headless browser
        xvfb = Xvfb(width=1280, height=720)
        xvfb.start()
        
        browser = get_wikipage(kpi_url)

        if not browser:
            xvfb.stop()
            sys.exit(-1)

        # validate login credentials
        if log_into_wiki(browser, auth_user, auth_pwd):

            # get kpi page links
            kpilinks = get_config_linktext()
            if wikitype == 'Test':
                kpilinks['Dashboard'] = "Test Dashboard KPIs"
            else:
                kpilinks['Dashboard'] = "Dashboard KPIs"

            # get updated kpi chart text  
            by_month_text, by_fyq_text, end_month = get_kpi_text_update()
            wikilog.debug("KPI Months: {0}; KPI FYQs: {1} KPI End Month: {2}".format(by_month_text, by_fyq_text, end_month))

            # get updated swdl kpi chart text 
            swdl_kpi_text = get_swdl_kpi_text()
            wikilog.debug("SWDL KPI texts: {0}".format(swdl_kpi_text))
            
            # loop through KPI page links
            for kpi, linktext in kpilinks.items():
                if linktext is None: continue     # 'wikitext' not available 

                if "SWDL" in kpi:
                    if not swdl_kpi_text:
                        continue
                    
                if update_kpi_page(browser, kpi, linktext, wikitype):                 
                    wikilog.info("{} kpis uploaded successfully".format(kpi))

                    update_kpi_text(browser, kpi, linktext, wikitype, by_month_text, by_fyq_text, end_month, swdl_kpi_text)

                    browser.refresh()
                    time.sleep(2)

                #break      # FOR TESTING PURPOSES ONLY!!!
                

    except Exception as e:
        wikilog.error("Exception: {}".format(str(e)))


    finally:
        xvfb.stop()
        
        if browser:
            browser.quit()

    
    return


#**************
# M A I N
#**************

if __name__ == "__main__":
   
    parser = argparse.ArgumentParser()
    parser.add_argument("-test", type=str, help="'Y' to indicate script is to run against 'Test' wikipage; 'N' otherwise (required)")
    args = parser.parse_args()

    wikitype = ''
    
    # Validate parameter
    if args.test is None:
        print("'-test' parameter (Y/N) is required!")
        
    else:
        if args.test.upper() == 'Y':
            wikitype = 'Test'

        main(wikitype)

        wikilog.info("")
        wikilog.info("Finished!!")
