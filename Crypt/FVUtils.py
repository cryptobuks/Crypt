#-*- coding: utf-8 -*-
#
#  FVUtils.py
#  Filevault Server
#
#  Created by Graham Gilbert on 03/12/2012.
#
# Copyright 2013 Graham Gilbert.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import re
import os
import plistlib
import subprocess
import FoundationPlist
from Foundation import *
from urllib2 import Request, urlopen, URLError, HTTPError
import urllib
from ctypes import *
import AppKit
from ctypes import util

iokit = cdll.LoadLibrary(util.find_library('IOKit'))
cf = cdll.LoadLibrary(util.find_library('CoreFoundation'))

cf.CFStringCreateWithCString.argtypes = [c_void_p, c_char_p, c_int32]
cf.CFStringCreateWithCString.restype = c_void_p
cf.CFStringGetCStringPtr.argtypes = [c_void_p, c_uint32]
cf.CFStringGetCStringPtr.restype = c_char_p

kCFAllocatorDefault = c_void_p.in_dll(cf, "kCFAllocatorDefault")
kCFStringEncodingMacRoman = 0

kIOMasterPortDefault = c_void_p.in_dll(iokit, "kIOMasterPortDefault")
kIOPlatformSerialNumberKey = "IOPlatformSerialNumber".encode("mac_roman")
iokit.IOServiceMatching.restype = c_void_p
iokit.IOServiceGetMatchingService.argtypes = [c_void_p, c_void_p]
iokit.IOServiceGetMatchingService.restype = c_void_p
iokit.IORegistryEntryCreateCFProperty.argtypes = [c_void_p, c_void_p, c_void_p, c_uint32]
iokit.IORegistryEntryCreateCFProperty.restype = c_void_p
iokit.IOObjectRelease.argtypes = [c_void_p]
SERIAL = None

# our preferences "bundle_id"
BUNDLE_ID = 'FVServer'

def GetMacSerial():
    """Returns the serial number for the Mac
        """
    global SERIAL
    if SERIAL is None:
        platformExpert = iokit.IOServiceGetMatchingService(kIOMasterPortDefault,
                                                           iokit.IOServiceMatching("IOPlatformExpertDevice"))
        if platformExpert:
            key = cf.CFStringCreateWithCString(kCFAllocatorDefault, kIOPlatformSerialNumberKey, kCFStringEncodingMacRoman)
            serialNumberAsCFString = \
                iokit.IORegistryEntryCreateCFProperty(platformExpert,
                                                      key,
                                                      kCFAllocatorDefault, 0);
            if serialNumberAsCFString:
                SERIAL = cf.CFStringGetCStringPtr(serialNumberAsCFString, 0)
           
            iokit.IOObjectRelease(platformExpert)
   
    return SERIAL


def GetMacName():
    theprocess = "scutil --get ComputerName"
    thename = subprocess.Popen(theprocess,shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE).communicate()[0]
    thename = thename.strip()
    return thename

##This was lifted verbatim from the Munki project - hope Greg doesn't mind!

def set_pref(pref_name, pref_value):
    """Sets a preference, writing it to
        /Library/Preferences/ManagedInstalls.plist.
        This should normally be used only for 'bookkeeping' values;
        values that control the behavior of munki may be overridden
        elsewhere (by MCX, for example)"""
    try:
        CFPreferencesSetValue(
                              pref_name, pref_value, BUNDLE_ID,
                              kCFPreferencesAnyUser, kCFPreferencesCurrentHost)
        CFPreferencesAppSynchronize(BUNDLE_ID)
    except Exception:
        pass

def pref(pref_name):
    """Return a preference. Since this uses CFPreferencesCopyAppValue,
    Preferences can be defined several places. Precedence is:
        - MCX
        - /var/root/Library/Preferences/ManagedInstalls.plist
        - /Library/Preferences/ManagedInstalls.plist
        - default_prefs defined here.
    """
    default_prefs = {
        'ServerURL': 'http://crypt',
        'CryptDir': '/usr/local/crypt',
    }
    pref_value = CFPreferencesCopyAppValue(pref_name, BUNDLE_ID)
    if pref_value == None:
        pref_value = default_prefs.get(pref_name)
        # we're using a default value. We'll write it out to
        # /Library/Preferences/<BUNDLE_ID>.plist for admin
        # discoverability
        set_pref(pref_name, pref_value)
    if isinstance(pref_value, NSDate):
        # convert NSDate/CFDates to strings
        pref_value = str(pref_value)
    return pref_value
    
def internet_on():
    try:
        response=urlopen(pref('ServerURL'),timeout=1)
        NSLog(u"Server is accessible")
        return True
    except URLError as err: pass
    NSLog(u"Server is not accessible")
    return False

def filevaultStatus():
    p = subprocess.Popen(['/usr/bin/fdesetup','status'], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout_data = p.communicate()[0]
    if stdout_data.strip() == "FileVault is Off.":
        NSLog(u"FileVault is Off.")
        return False
    else:
        NSLog(u"FileVault is Enabled.")
        return True
        
def escrow_key(key, username, runtype):
    theurl = pref('ServerURL')+"/checkin/"
    serial = GetMacSerial()
    macname = GetMacName()
    mydata=[('serial',serial),('recovery_password',key),('username',username),('macname',macname)]
    mydata=urllib.urlencode(mydata)
    req = Request(theurl, mydata)
    try:
        response = urlopen(req)
    except URLError, e:
        if hasattr(e, 'reason'):
            print 'We failed to reach a server.'
            print 'Reason: ', e.reason
            has_error = True
        elif hasattr(e, 'code'):
            print 'The server couldn\'t fulfill the request'
            print 'Error code: ', e.code
            has_error = True
        if has_error:
            plistData = {}
            plistData['recovery_key']=key
            plistData['username']=username
            try:
                FoundationPlist.writePlist(plistData, '/usr/local/crypt/recovery_key.plist')
            except:
                os.makedirs('/usr/local/crypt')
                FoundationPlist.writePlist(plistData, '/usr/local/crypt/recovery_key.plist')
            
            os.chmod('/usr/local/crypt/recovery_key.plist',0700)
            if runtype=="initial":
                the_command = "/sbin/reboot"
                reboot = subprocess.Popen(the_command,shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE).communicate()[0]

    else:
        ##need some code to read in the json response from the server, and if the data matches, display success message, or failiure message, then reboot. If not, we need to cache it on disk somewhere - maybe pull it out with facter?
        #time to turn on filevault
        #NSLog(u"%s" % fvprefs['ServerURL'])
        ##escrow successful, if the file exists, remove it
        thePlist = '/usr/local/crypt/recovery_key.plist'

        if os.path.exists(thePlist):
            os.remove(thePlist)
        if runtype=="initial":
            the_command = "/sbin/reboot"
            reboot = subprocess.Popen(the_command,shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE).communicate()[0]