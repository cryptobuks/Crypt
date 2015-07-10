#-*- coding: utf-8 -*-
#
#  FVController.py
#  Filevault Server
#
#  Created by Graham Gilbert on 03/12/2012.
#
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

import objc
import FoundationPlist
import os
from SystemConfiguration import *
from Foundation import *
from AppKit import *
from Cocoa import *
import subprocess
import sys
import re
import FVUtils
import urllib
import plistlib
import re
from urllib2 import Request, urlopen, URLError, HTTPError


class FVController(NSObject):
    userName = objc.IBOutlet()
    password = objc.IBOutlet()
    encryptButton = objc.IBOutlet()
    errorField = objc.IBOutlet()
    window = objc.IBOutlet()
    progressPanel = objc.IBOutlet()
    progressIndicator = objc.IBOutlet()
    progressText = objc.IBOutlet()
    autoUsername = None

    def startRun(self):
        if self.window:
            self.window.setCanBecomeVisibleWithoutLogin_(True)
            self.window.setLevel_(NSScreenSaverWindowLevel - 1)
            self.window.center()

    def runEncryptOnThread_(self, input_plist):
        # Autorelease pool for memory management
        pool = NSAutoreleasePool.alloc().init()
        the_error = None
        fv_status = ""
        recovery_key = None
        plist = plistlib.readPlistFromString(input_plist)
        user_name = plist['Username']
        # run command
        p = subprocess.Popen(['/usr/bin/fdesetup','enable','-outputplist', '-inputplist'], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        (stdout_data, err) = p.communicate(input=input_plist)
        try:
            fv_status = plistlib.readPlistFromString(stdout_data)
            recovery_key = fv_status['RecoveryKey']
        except:
            NSLog('Couldn\'t read recovery key from output')
        if p.returncode != 0:
            NSLog('ERROR: %s' % err)
            the_error = err

        self.performSelectorOnMainThread_withObject_waitUntilDone_(self.encryptionComplete(user_name, recovery_key, the_error), None, YES)
        # Clean up autorelease pool
        del pool


    def encryptionComplete(self, user_name, recovery_key, encrypt_error):
        # end the modal sheet and close the panel
        NSApp.endSheet_(self.progressPanel)
        self.progressPanel.orderOut_(self)
        def enable_inputs(self):
            self.userName.setEnabled_(True)
            self.password.setEnabled_(True)
            self.encryptButton.setEnabled_(True)
        # send the key to be escrowed if not an error
        if encrypt_error:
            ##write the key to a plist
            ##load a launch daemon - touch a file maybe?
            ##submit the key
            alert = NSAlert.alertWithMessageText_defaultButton_alternateButton_otherButton_informativeTextWithFormat_(
                                                                                                                      NSLocalizedString(u"Something went wrong", None),
                                                                                                                      NSLocalizedString(u"Aww, drat", None),
                                                                                                                      objc.nil,
                                                                                                                      objc.nil,
                                                                                                                      NSLocalizedString(u"There was a problem with enabling encryption on your Mac. Please make sure you are using your short username and that your password is correct. Please contact IT Support if you need help.", None))
            alert.beginSheetModalForWindow_modalDelegate_didEndSelector_contextInfo_(
                                                                                         self.window, self, enable_inputs(self), objc.nil)
        if recovery_key:
            self.escrowKey(recovery_key, user_name, 'initial')

    def encryptDrive(self, password, username):
        #time to turn on filevault
        # we need to see if fdesetup is available, might as well use the built in methods in 10.8
        the_error = ""
        fv_status = ""
        if os.path.exists('/usr/bin/fdesetup'):
            ##build plist
            the_settings = {}
            the_settings['Username'] = username
            the_settings['Password'] = password
            input_plist = plistlib.writePlistToString(the_settings)
            NSThread.detachNewThreadSelector_toTarget_withObject_(self.runEncryptOnThread_, self, input_plist)

        if not os.path.exists('/usr/bin/fdesetup'):
            return fv_status, the_error

    def escrowKey(self, key, username, runtype):
        #self.progressText.setStringValue_("Sending encryption key to the server...")
        if runtype == 'initial':
            NSApp.beginSheet_modalForWindow_modalDelegate_didEndSelector_contextInfo_(self.progressPanel, self.window, self, None, None)
            self.progressIndicator.startAnimation_(self)
        ##submit this to the server fv_status['recovery_password']
        FVUtils.escrow_key(key, username, runtype)

    def errorReset(self):
        # Hide the progress bar
        NSApp.endSheet_(self.progressPanel)
        self.progressPanel.orderOut_(self)
        def enable_inputs(self):
            self.userName.setEnabled_(True)
            self.password.setEnabled_(True)
            self.encryptButton.setEnabled_(True)
        # Show an error panel
        alert = NSAlert.alertWithMessageText_defaultButton_alternateButton_otherButton_informativeTextWithFormat_(
                                                                                                                  NSLocalizedString(u"Something went wrong", None),
                                                                                                                  NSLocalizedString(u"Aww, drat", None),
                                                                                                                  objc.nil,
                                                                                                                  objc.nil,
                                                                                                                  NSLocalizedString(u"There was a problem with enabling encryption on your Mac. Please make sure you are using your short username and that your password is correct. Please contact IT Support if you need help.", None))
        alert.beginSheetModalForWindow_modalDelegate_didEndSelector_contextInfo_(
                                                                                     self.window, self, enable_inputs(self), objc.nil)

    def awakeFromNib(self):
        try:
            cur_console = SCDynamicStoreCopyConsoleUser(None, None, None)[0]
            if cur_console != "":
                self.autoUsername = True
                self.userName.setStringValue_(cur_console)
        except:
            self.autoUsername = False

    @objc.IBAction
    def encrypt_(self,sender):
        fvprefspath = "/Library/Preferences/FVServer.plist"
        serial = FVUtils.GetMacSerial()
        serverURL = FVUtils.pref("ServerURL")
        NSLog(u"%s" % serverURL)
        if serverURL == "":
            self.errorField.setStringValue_("ServerURL isn't configured")
            self.userName.setEnabled_(False)
            self.password.setEnabled_(False)
            self.encryptButton.setEnabled_(False)
        username_value = self.userName.stringValue()
        password_value = self.password.stringValue()
        self.userName.setEnabled_(False)
        self.password.setEnabled_(False)
        self.encryptButton.setEnabled_(False)

        def enable_inputs(self):
            if self.autoUsername == True:
                self.userName.setEnabled_(False)
            else:
                self.userName.setEnabled_(True)
            self.password.setEnabled_(True)
            self.encryptButton.setEnabled_(True)

        if username_value == "" or password_value == "":
            self.errorField.setStringValue_("You need to enter your username and password")
            if self.autoUsername == True:
                self.userName.setEnabled_(False)
            else:
                self.userName.setEnabled_(True)
            self.password.setEnabled_(True)
            self.encryptButton.setEnabled_(True)

        if username_value != "" and password_value !="":
            self.userName.setEnabled_(False)
            self.password.setEnabled_(False)
            self.encryptButton.setEnabled_(False)

            # Open the progress sheet
            NSApp.beginSheet_modalForWindow_modalDelegate_didEndSelector_contextInfo_(self.progressPanel, self.window, self, None, None)
            self.progressIndicator.startAnimation_(self)
            self.encryptDrive(password_value, username_value)
