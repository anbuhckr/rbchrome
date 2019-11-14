#! /usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import time
import json
import os
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

