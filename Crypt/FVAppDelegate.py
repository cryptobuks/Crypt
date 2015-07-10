#-*- coding: utf-8 -*-
#
#  Filevault_ServerAppDelegate.py
#  Filevault Server
#
#  Created by Graham Gilbert on 04/11/2012.
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


from Foundation import *
import FVUtils
from AppKit import *
import objc

class FVAppDelegate(NSObject):
    window = objc.IBOutlet()

    def applicationWillFinishLaunching_(self, sender):

        #[self.panel setCanBecomeVisibleWithoutLogin:YES];
        self.window.setCanBecomeVisibleWithoutLogin_(True)
        # // Our application is a UI element which never activates, so we want our
        # // panel to show regardless.

        #self.panel setHidesOnDeactivate:NO];
        self.window.setHidesOnDeactivate_(False)

        # // Due to a problem with the relationship between the UI frameworks and the
        # // window server <rdar://problem/5136400>, -[NSWindow orderFront:] is not
        # // sufficient to show the window.  We have to use -[NSWindow orderFrontRegardless].

        # if ([[NSUserDefaults standardUserDefaults] boolForKey:@"ForceOrderFront"]) {
        #     [[LogManager sharedManager] logWithFormat:@"Showing window with extreme prejudice"];
        #     [self.panel orderFrontRegardless];
        # } else {
        #     [[LogManager sharedManager] logWithFormat:@"Showing window normally"];
        #     [self.panel orderFront:self];
        # }
        self.window.makeKeyAndOrderFront_(self)
        # don't show menu bar
        NSMenu.setMenuBarVisible_(NO)

    def applicationDidFinishLaunching_(self, sender):
        # Prevent automatic relaunching at login on Lion
        if NSApp.respondsToSelector_('disableRelaunchOnLogin'):
            NSApp.disableRelaunchOnLogin()
        # Quit if filevault is already enabled, encrypting or decrypting.
        if FVUtils.filevaultStatus():
            NSApp.terminate_(self)
        # Quit if the server isn't available
        if not FVUtils.internet_on():
            NSApp.terminate_(self)
