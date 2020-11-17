#! /usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import time
import json
import os
import base64
from urllib.request import urlopen
from urllib.error import URLError
from .cdp import Cdp
from .service import Service
from .exceptions import *

class Browser(object):
    def __init__(self, url=None, *args, **kwargs):
        self.service = None
        self.timeout_stats = False
        if not url:            
            self.service = Service(*args, **kwargs)
            url = self.service.url
        self.dev_url = url
        rsp = self.get_ws_endpoint()
        self.cdp = Cdp(rsp)
        self.cdp.set_listener("Page.frameStoppedLoading", self.on_load_finished)    

    def on_load_finished(self, **kwargs):        
        self.timeout_stats = True

    def time_out_check(self, timeout):        
        count = 0
        while not self.timeout_stats:
            count += 1
            if count == timeout:
                self.timeout_stats = True
                raise TimeoutException()                
            time.sleep(1)     

    def get_ws_endpoint(self):
        url = f"{self.dev_url}/json/new?"       
        while True:
            time.sleep(0.1)
            try:
                with urlopen(url) as f:
                    data = json.loads(f.read().decode())
                break
            except URLError:
                continue
        else:
            raise Exception("Browser closed unexpectedly!")        
        return data['webSocketDebuggerUrl']

    def start(self):           
        self.cdp.start()

    def send(self, method, **kwargs):                 
        self.cdp.call_method(method, **kwargs)

    def get(self, url, reff=None, timeout=30):        
        if reff:
            self.cdp.call_method("Page.navigate", url=url, referrer=reff)
        else:
            self.cdp.call_method("Page.navigate", url=url)
        time.sleep(0.9)
        self.time_out_check(timeout)
        
    def takeScreenShoot(self):
        script = """
        ({
            width: Math.max(window.innerWidth, document.body.scrollWidth, document.documentElement.scrollWidth)|0,
            height: Math.max(innerHeight, document.body.scrollHeight, document.documentElement.scrollHeight)|0,
            deviceScaleFactor: window.devicePixelRatio || 1,
            mobile: typeof window.orientation !== 'undefined'
        })
        """
        response = self.cdp.call_method("Runtime.evaluate", returnByValue=True, expression=script)
        result = response["result"]["value"]    
        val_item = [v for k,v in result.items()]                  
        self.cdp.call_method("Emulation.setDeviceMetricsOverride", width=val_item[0], height=val_item[1], deviceScaleFactor=val_item[2], mobile=val_item[3])        
        screenshot = self.cdp.call_method("Page.captureScreenshot", format="png", fromSurface=True)
        self.cdp.call_method("Emulation.clearDeviceMetricsOverride")
        png = base64.b64decode(screenshot["data"])
        with open("screenshot.png", "wb") as f:
            f.write(png)
        return True
    
    def getTitle(self):        
        response = self.cdp.call_method("Runtime.evaluate", expression="document.title")        
        result = response["result"]["value"]                   
        return result
    
    def runJs(self, script):        
        response = self.cdp.call_method("Runtime.evaluate", expression=script)        
        result = response["result"]["value"]                   
        return result

    def listen(self, event, callback):
        self.cdp.set_listener(event, callback)    

    def stop(self):        
        self.cdp.stop()
        self.service.stop()

    def __enter__(self):
        return self    
   
    def __exit__(self, *args):
        try:
            self.stop()
        except Exception:
            pass

