#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import os
import json
import time
import warnings
import threading
import queue
import functools
import socket
import websocket
from urllib.request import urlopen
from urllib.error import URLError
from subprocess import Popen, PIPE, STDOUT
from .exceptions import *

class GenericAttr(object):
    def __init__(self, name, browser):
        self.__dict__["name"] = name
        self.__dict__["browser"] = browser

    def __getattr__(self, item):
        method_name = f"{self.name}.{item}"
        event_listener = self.browser.get_listener(method_name)

        if event_listener:
            return event_listener
        return functools.partial(self.browser.run_command, method_name)

    def __setattr__(self, key, value):
        self.browser.set_listener(f"{self.name}.{key}", value)
        
class Browser(object):
    def __init__(self, headless=False, rb_options=[]):
        self.headless = headless
        self.rb_options = rb_options
        self._cur_id = 1000        
        self._recv_th = threading.Thread(target=self._recv_loop)
        self._recv_th.daemon = True
        self._handle_event_th = threading.Thread(target=self._handle_event_loop)
        self._handle_event_th.daemon = True
        self._stopped = threading.Event()
        self._started = False
        self.status = self.status_initial
        self.event_handlers = {}
        self.method_results = {}
        self.event_queue = queue.Queue()
        
    def free_port(self):
        free_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        free_socket.bind(('0.0.0.0', 0))
        free_socket.listen(5)
        port = free_socket.getsockname()[1]
        free_socket.close()
        return port

    def find(self, name):
        for root, dirs, files in os.walk("C:/"):
            if name in files:
                return os.path.join(root, name).replace("\\", "/")
                
    def browser_options(self):
        if "nt" in os.name:            
            options = [self.find("chrome.exe")]
            options.append(f"--user-data-dir={os.getenv('LOCALAPPDATA')}/Google/Chrome/User Data/RbChrome")
        else:
            options = ["google-chrome"]
            options.append(f"--user-data-dir=/tmp/rbchrome")
            options.append("--no-sandbox")
            options.append("--disable-setuid-sandbox")            
        options.append("about:blank")
        options.append(f"--remote-debugging-port={self.port}")
        if self.headless:
            options.append("--headless")        
        options.append("--disable-background-networking")
        options.append("--enable-features=NetworkService,NetworkServiceInProcess")
        options.append("--disable-background-timer-throttling")
        options.append("--disable-backgrounding-occluded-windows")
        options.append("--disable-breakpad")
        options.append("--disable-client-side-phishing-detection")
        options.append("--disable-component-extensions-with-background-pages")
        options.append("--disable-default-apps")
        options.append("--disable-dev-shm-usage")
        options.append("--disable-extensions")
        options.append("--disable-features=TranslateUI,BlinkGenPropertyTrees")
        options.append("--disable-hang-monitor")
        options.append("--disable-ipc-flooding-protection")
        options.append("--disable-popup-blocking")
        options.append("--disable-prompt-on-repost")
        options.append("--disable-renderer-backgrounding")
        options.append("--disable-sync")
        options.append("--force-color-profile=srgb")
        options.append("--metrics-recording-only")
        options.append("--no-first-run")
        options.append("--enable-automation")
        options.append("--password-store=basic")
        options.append("--use-mock-keychain")
        options.extend(self.rb_options) 
        return options
        
    def _send(self, message, timeout=None):
        if "id" not in message:
            self._cur_id += 1
            message["id"] = self._cur_id
        message_json = json.dumps(message)
        if not isinstance(timeout, (int, float)) or timeout > 1:
            q_timeout = 1
        else:
            q_timeout = timeout / 2.0
        try:
            self.method_results[message["id"]] = queue.Queue()            
            self._ws.send(message_json)
            while not self._stopped.is_set():
                try:
                    if isinstance(timeout, (int, float)):
                        if timeout < q_timeout:
                            q_timeout = timeout
                        timeout -= q_timeout
                    return self.method_results[message["id"]].get(timeout=q_timeout)
                except queue.Empty:
                    if isinstance(timeout, (int, float)) and timeout <= 0:
                        raise TimeoutException(f"Calling {message['method']} timeout")
                    continue
            raise UserAbortException(f"User abort, call stop() when calling {message['method']}")
        finally:
            self.method_results.pop(message["id"], None)

    def _recv_loop(self):
        while not self._stopped.is_set():
            try:
                self._ws.settimeout(1)
                message_json = self._ws.recv()
                message = json.loads(message_json)
            except websocket.WebSocketTimeoutException:
                continue
            except (websocket.WebSocketException, OSError):
                if not self._stopped.is_set():                    
                    self._stopped.set()
                return
            if "method" in message:
                self.event_queue.put(message)
            elif "id" in message:
                if message["id"] in self.method_results:
                    self.method_results[message["id"]].put(message)
            else:
                warnings.warn(f"unknown message: {message}")

    def _handle_event_loop(self):
        while not self._stopped.is_set():
            try:
                event = self.event_queue.get(timeout=1)
            except queue.Empty:
                continue
            if event["method"] in self.event_handlers:
                try:
                    self.event_handlers[event["method"]](**event["params"])
                except:
                    warnings.warn(f"callback {event['method']} exception")
            self.event_queue.task_done()

    def __getattr__(self, item):
        attr = GenericAttr(item, self)
        setattr(self, item, attr)
        return attr 

    def run_command(self, method, *args, **kwargs):
        if args:
            raise CallMethodException("the params should be key=value format")
        timeout = kwargs.pop("_timeout", None)
        result = self._send({"method": method, "params": kwargs}, timeout=timeout)
        if "result" not in result and "error" in result:
            warnings.warn(f"{method} error: {result['error']['message']}")         
            raise CallMethodException(f"calling method: {method} error: {result['error']['message']}")
        return result["result"]

    def set_listener(self, event, callback):
        if not callback:
            return self.event_handlers.pop(event, None)
        if not callable(callback):
            raise RuntimeException("callback should be callable")
        self.event_handlers[event] = callback
        return True

    def get_listener(self, event):
        return self.event_handlers.get(event, None)

    def del_all_listeners(self):
        self.event_handlers = {}
        return True

    def get_ws_endpoint(self):
        url = f"http://localhost:{self.port}/json"
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
        return data[0]['webSocketDebuggerUrl']

    def start(self):
        self.port = self.free_port()
        cmd = self.browser_options()        
        self.process = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)        
        ws_url = self.get_ws_endpoint()
        if self._started:
            return False
        if not ws_url:
            raise RuntimeException("Already has another client connect to this browser")
        self._started = True
        self.status = self.status_started
        self._stopped.clear()
        self._ws = websocket.create_connection(ws_url, enable_multithread=True)
        self._recv_th.start()
        self._handle_event_th.start()               

    def stop(self):
        if self._stopped.is_set():
            return False
        if not self._started:
            raise RuntimeException("Browser is not running")
        self.status = self.status_stopped        
        self.run_command("Browser.close")
        time.sleep(0.5)        
        self._recv_th.join()
        self._handle_event_th.join()
        self._stopped.set()
        self._ws.close()              
        for stream in [self.process.stdin, self.process.stdout, self.process.stdout]:
            try:
                stream.close()
            except AttributeError:
                pass
        self.process.terminate()
        self.process.wait()  
        self.process.kill()
