#!/usr/bin/python3

"""********************************************************************
Created by:   Fiona Egbulefu (Contractor)

Created date: 07 May 2019

Description:  Export KPI charts to Confluence (Wiki) page

********************************************************************"""

import os
import sys
import time
import win32clipboard

import config # user defined
import logger # uerr defined

from shutil import copyfile

from PIL import Image
from io import BytesIO

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait 
from selenium.webdriver.common.action_chains import ActionChains

# setup log
kpilog = logger.get_logger(config.autokpi["logname"])


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

    try:
                           
        browser = start_browser()
        browser.get(url)

    except Exception as e:
                           
        kpilog.error("Unable to access Confluence: {}".format(str(e)))
        if browser:
            browser.quit()
            
        return None

    return browser


#-----------------------------------------------
# Access Wiki page  
# - returns True/False (logged in)
#-----------------------------------------------
def log_into_wiki(browser, auth_user, auth_pwd):

    if not browser.find_element_by_name("login"):                   # test for login page
        return True

    try:
        # access login boxes
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
                kpilog.info("User {0} Login: OK".format(auth_user))
                return True
            else:
                kpilog.error("Unable to access Confluence; Check user credentials")
            
    except Exception as e:
        kpilog.error("Unable to access Confluence {}".format(str(e)))


    return False


#-------------------------------------------------------------
# Copy chart to clipboard
# - returns True/False (image sent to clipboard)
#-------------------------------------------------------------
def copy_chart_to_clipboard(chartpath):

    kpilog.debug("...copy saved chart to clipboard")

    try:
        # open chart
        output = BytesIO()
        image = Image.open(chartpath)
        image.convert("RGB").save(output, "BMP")
        data = output.getvalue()[14:]       # .bmp header is 14 bytes
        output.close()

        # paste into clipboard
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
        win32clipboard.CloseClipboard()

        return True

    except Exception as e:
        kpilog.error("Exception: {}".format(str(e)))

    return False

   
#-------------------------------------------------------------
# Get full path name of chart to replace image 
# - returns string (full path of chart)
#-------------------------------------------------------------
def get_chart(img_name):

    chartpath = None

    # access folder of saved charts
    cwd = os.getcwd()
    chartfiles = os.path.join(cwd, config.autokpi["savedir"])

    for chart in os.listdir(chartfiles):
        
        if (img_name == "CMSA-Month.PNG" and chart == "CFPD_AllMonths.png") \
           or (img_name == "All-CFDs-Month.PNG" and chart == "AllCFD_AllMonths.png") \
           or (img_name == "CMSAM-PSIRT.PNG" and chart == "PSIRT_AllMonths.png"):
    
            chartpath = os.path.join(chartfiles, chart)
            kpilog.debug("Chart exists: {}".format(chartpath))
                           
            break
        
    return chartpath


#-------------------------------------------------------------
# Update image width, height and title 
# - returns None  
#-------------------------------------------------------------
def update_image_title(browser, img_id, img_name, frame):

    kpilog.debug("...reselect image and update image title")

    css_selector = ''.join(['img[data-linked-resource-id="', img_id, '"]'])
    element = browser.find_element_by_css_selector(css_selector)
    # bring image to view
    browser.execute_script("return arguments[0].scrollIntoView(true);", element)

    actions = ActionChains(browser)
    actions.move_to_element(element).click(element).perform()                
    time.sleep(3)

    browser.switch_to.parent_frame()

    # click on 'Properties' menu button
    xpath = "//div[@class='panel-buttons']/a[contains(@class, 'properties')]/span[@class='panel-button-text']"
    prop_menu = browser.find_element_by_xpath(xpath)
    prop_menu.click()               
    time.sleep(3)

    # 'Title' link
    title_link = browser.find_element_by_xpath("//*[@id='image-attributes']")
    title_link.click()
    time.sleep(3)

    # set 'Title text'
    title = browser.find_element_by_xpath("//*[@id='image-title-attribute']")
    title.clear()

    if title.text:
        title.send_keys(Keys.CONTROL + 'a')
        title.send_keys(Keys.DELETE)

    time.sleep(2)
    title.send_keys(img_name)       # set as image name
    time.sleep(3)

    # Save changes
    savebtn = browser.find_element_by_xpath("//button[text()='Save']")
    savebtn.click()
    time.sleep(3)
    
    browser.switch_to.frame(frame)
   
    return None


#-------------------------------------------------------------
# Update image width, height
# - returns None  
#-------------------------------------------------------------
def update_image_attributes(browser, new_img, img_name):
        
    browser.execute_script("arguments[0].setAttribute('width', '570')", new_img)

    browser.execute_script("arguments[0].setAttribute('height', '370')", new_img)
   
    return None


#-------------------------------------------------------------
# Cut/Paste image onto Wiki 
# - returns None  
#-------------------------------------------------------------
def update_image(browser, element, img_name, cut_or_paste):

    actions = ActionChains(browser)
     
    if cut_or_paste == 'x':   # cut

        # find parenet of image
        parent = element.find_element_by_xpath('..')
        if parent.tag_name == "p":       # ignore <p> tags
            parent = parent.find_element_by_xpath('..')

        # bring image to view
        browser.execute_script("return arguments[0].scrollIntoView(true);", element)
        actions.move_to_element(element).double_click(element).perform()                
        time.sleep(3)

        kpilog.debug("...cut/remove image")
                           
        actions.key_down(Keys.CONTROL).send_keys('x').key_up(Keys.CONTROL).perform()    
        time.sleep(3)

        return parent

    else:       # paste

        parent = element

        actions.move_to_element(parent).perform()           
        time.sleep(3)
        actions.key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
        time.sleep(3)

        kpilog.debug("...update new image attributes")
                           
        new_img = parent.find_element_by_tag_name("img")       # use parent to get new image
        update_image_attributes(browser, new_img, img_name)

        return new_img


#-------------------------------------------------------------
# Publish Wiki changes
# - returns True/False (updates published)
#-------------------------------------------------------------
def publish_updates(browser, blnCancel, switch_to_frame):

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

            kpilog.info("All updates canceled!")

            return False
            
        else:
            
            updatepage = browser.find_element_by_id("rte-button-publish")
            updatepage.click()
            time.sleep(3)

            kpilog.info("All updates published!")

    else:   # no changes to page

        cancelpage = browser.find_element_by_id("rte-button-cancel")
        if cancelpage.is_displayed():
            cancelpage.click()
            time.sleep(3)
            
        return False


    return True

        
#-------------------------------------------------------------
# Parse HTML images and update images 
# - returns True/False charts updated  
#-------------------------------------------------------------
def update_charts(browser):

    img_chart = {}

    blnCancel = False
    switch_to_frame = False
    
    try:

        # find images and corresponding charts      
        imgs = browser.find_elements_by_class_name("confluence-embedded-image")

        for img in imgs:

            # get image name from 'title' if it exists 
            if img.get_attribute("title"):      
                img_name = img.get_attribute("title")
            else:
                img_name = img.get_attribute("data-linked-resource-default-alias")

            # find corresponding chart
            chart = get_chart(img_name)
            if chart:
                img_id = img.get_attribute("data-linked-resource-id")       # unique to each chart
                img_chart[img_id] = (img_name, chart)

        # ------------------------------
        # update images if charts found
        # ------------------------------

        if img_chart:

            # place page in edit mode for update
            editpage = browser.find_element_by_id("editPageLink")
            editpage.click()
            time.sleep(3)

            kpilog.info("Prepare page for updates...")

            # switch to frame containing images 
            frame = browser.find_element_by_xpath("//iframe[@id='wysiwygTextarea_ifr']")
            browser.switch_to.frame(frame)

            switch_to_frame = True

            for img_id, (img_name, img_chart) in img_chart.items():

                kpilog.debug("Image selected for update: {0} {1}".format(img_name, img_chart))
                css_selector = ''.join(['img[data-linked-resource-id="', img_id, '"]'])
                element = browser.find_element_by_css_selector(css_selector)

                parent = update_image(browser, element, img_name, 'x')          # cut

                if copy_chart_to_clipboard(img_chart):  # send saved chart to clipboard
                    kpilog.debug("Paste new image")
                    new_img = update_image(browser, parent, img_name, 'v')      # paste

                    kpilog.debug("Update new image title")
                    new_img_id = new_img.get_attribute("data-linked-resource-id")
                    update_image_title(browser, new_img_id, img_name, frame)
                    
                else:
                    kpilog.error("Update cancelled; Could not update {0}".format(img_name))
                    blnCancel = True
                    break

##                break    TESTING
            
        else:
            kpilog.error("No images found for update")

            
    except Exception as e:

        kpilog.error("Update cancelled: {}".format(str(e)))
        blnCancel = True


    finally:
        if not publish_updates(browser, blnCancel, switch_to_frame):
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
        kpilog.info("Start Wiki upload....")
        browser = get_wikipage(kpi_url)

        if not browser:
            sys.exit(-1)

        # validate login credentials; upload charts
        if log_into_wiki(browser, auth_user, auth_pwd):
            if update_charts(browser):
                kpilog.info("Charts uploaded successfully!")
                    

    except Exception as e:
        kpilog.error("Exception: {}".format(str(e)))


    finally:
        if browser:
            browser.quit()

    
    return

    

if "__name__" == "__main__":
   
    main("Test")

    kpilog.info("Finished Wiki Upload")
