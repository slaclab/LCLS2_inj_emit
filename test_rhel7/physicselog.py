#!/usr/local/bin/python -d
# encoding: utf-8

'''
Name: physicselog.py
Author: Matt Gibbs, based heavily on code by Shawn Alverson (he did all the hard work)
Created: 9/13/2016

physicselog.py provides tools to programatically write to the physics elog.
'''
try:
    from urllib.request import urlopen, URLError, HTTPError  # Python 3
except ImportError:
    from urllib2 import urlopen, URLError, HTTPError  # Python 2
from xml.etree.ElementTree import Element, SubElement
from xml.etree import ElementTree
from datetime import datetime
import json
import subprocess
import shutil
import os
import re
import sys

def submit_entry(logbook, username, title, entry_text=None, attachment=None, thumbnail=None):
    """ Submit a new logbook entry. """
    if logbook not in ["lcls", "lcls2", "facet"]:
        send_to_printer(attachment, "physics-{name}log".format(name=logbook))
        return
    fileName = write_entry_xml(username, title, entry_text, attachment, thumbnail)
    print(fileName)
    if fileName == None:
        raise Exception("Could not write XML file.")
    success = send_to_logbook(fileName, logbook)
    if not success:
        raise Exception("Entry submission failed.")
    return success

def write_entry_xml(username, title, text=None, attachment=None, thumbnail=None):
    """Create xml file for the entry."""
    curr_time = datetime.now()
    # Set up xml tags
    log_entry = Element(None)
    severity  = SubElement(log_entry, 'severity')
    location  = SubElement(log_entry, 'location')
    keywords  = SubElement(log_entry, 'keywords')
    time      = SubElement(log_entry, 'time')
    isodate   = SubElement(log_entry, 'isodate')
    log_user  = SubElement(log_entry, 'author')
    category  = SubElement(log_entry, 'category')
    title_tag = SubElement(log_entry, 'title')
    metainfo  = SubElement(log_entry, 'metainfo')

    time_string = curr_time.strftime("%Y-%m-%dT%H:%M:%S")

    # Take care of unchanging tags first
    log_entry.attrib['type'] = "LOGENTRY"
    category.text = "USERLOG"
    location.text = "not set"
    severity.text = "NONE"
    keywords.text = "none"
    time.text = curr_time.strftime("%H:%M:%S")
    isodate.text = curr_time.strftime("%Y-%m-%d")
    metainfo.text = time_string + "-00.xml"

    # Handle attachment
    if attachment is not None:
        attached_file_tag = SubElement(log_entry, 'link')
        attached_file_name = time_string + "-00.ps"
        temp_file = "/tmp/" + attached_file_name
        shutil.copyfile(attachment, temp_file)
        attached_file_tag.text = attached_file_name
        if thumbnail is not None:
            temp_thumbnail_name = time_string + "-00.png"
            temp_thumbnail = "/tmp/" + temp_thumbnail_name
            shutil.copyfile(thumbnail, temp_thumbnail)
            thumbnail_tag = SubElement(log_entry, 'file')
            thumbnail_tag.text = temp_thumbnail_name
        else:
            temp_thumbnail_name = time_string + "-00.png"
            temp_thumbnail_file = "/tmp/" + temp_thumbnail_name
            command = "convert {inp} {out}".format(inp=attachment, out=temp_thumbnail_file)
            p = subprocess.Popen(command, shell=True)
            p.wait()
            thumbnail_tag = SubElement(log_entry, 'file')
            thumbnail_tag.text = temp_thumbnail_name

    # For some stupid reason the physics logbook needs the text tag to come last.
    text_tag = SubElement(log_entry, 'text')

    fileName = "/tmp/" + metainfo.text

    # Fill in user inputs
    log_user.text = username
    title_tag.text = title
    if title_tag.text == "":
        raise Exception("Cannot submit an entry without a title.")
    if text is None or text == "":
        text = " " #Strangely, you can't have a completely blank string or ElementTree leaves off the text tag entirely, which will cause logbook parser to fail.
    text_tag.text = text

    # Create xml file
    xmlFile = open(fileName,"w")
    rawString = ElementTree.tostring(log_entry, 'utf-8')
    rawString = rawString.decode("utf8")
    parsedString = re.sub(r'(?=<[^/].*>)','\n',rawString)
    xmlString = parsedString[1:]
    xmlFile.write(xmlString)
    xmlFile.write("\n")  # Close with newline so cron job parses correctly
    xmlFile.close()

    return fileName.rstrip(".xml")

def send_to_logbook(fileName, location='lcls'):
    """ Copies an xml file into the logbook 'new entry' directory. """
    if location == 'lcls2':
        path = os.path.join("/u1/lcls/physics/logbook/", location, "data")
    else:
        path = os.path.join("/u1/", location, "physics/logbook/data")
    try:
        shutil.copy(fileName + ".png", path)
    except IOError:
        print("Copying thumbnail failed!")
    try:
        shutil.copy(fileName + ".ps", path)
    except IOError:
        print("Copying attachment failed!")
    shutil.copy(fileName + ".xml", path)
    return True

def send_to_printer(filename, printer):
    print("Printing to {}".format(printer))
    makePostScript = "convert " + filename + " " + filename +  ".ps"
    os.system(makePostScript)
    printFile = "lpr -P " + printer + " " + filename + ".ps"
    os.system(printFile)

if __name__ == '__main__':
    logbook = sys.argv[1]
    username = sys.argv[2]
    attachment = sys.argv[3]
    thumbnail = attachment
    title = sys.argv[4]
    try:
        entry_text = sys.argv[5]
    except:
        entry_text = None
    submit_entry(logbook, username, title, entry_text, attachment, thumbnail)
