#! /usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import os
import json
import time
import logging
import warnings
import threading
import functools
import queue
import websocket
from .exceptions import *

logger = logging.getLogger(__name__)

class GenericAttr(object):
    def __init__(self, name, cdp):
        self.__dict__['name'] = name
        self.__dict__['cdp'] = cdp

    def __getattr__(self, item):
        method_name = "%s.%s" % (self.name, item)
        event_listener = self.cdp.get_listener(method_name)
        if event_listener:
            return event_listener
        return functools.partial(self.cdp.call_method, method_name)

    def __setattr__(self, key, value):
        self.cdp.set_listener("%s.%s" % (self.name, key), value)

class Cdp(object):
    status_initial = 'initial'
    status_started = 'started'
    status_stopped = 'stopped'

    def __init__(self, ws_url):        
        self.debug = os.getenv("DEBUG", False)
        self._websocket_url = ws_url
        self._cur_id = 1000
        self._ws = None
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

    def _send(self, message, timeout=None):
        if 'id' not in message:
            self._cur_id += 1
            message['id'] = self._cur_id
        message_json = json.dumps(message)
        if self.debug:  
            print("SEND > %s" % message_json)
        if not isinstance(timeout, (int, float)) or timeout > 1:
            q_timeout = 1
        else:
            q_timeout = timeout / 2.0
        try:
            self.method_results[message['id']] = queue.Queue()            
            self._ws.send(message_json)
            while not self._stopped.is_set():
                try:
                    if isinstance(timeout, (int, float)):
                        if timeout < q_timeout:
                            q_timeout = timeout
                        timeout -= q_timeout
                    return self.method_results[message['id']].get(timeout=q_timeout)
                except queue.Empty:
                    if isinstance(timeout, (int, float)) and timeout <= 0:
                        raise TimeoutException("Calling %s timeout" % message['method'])
                    continue
            raise UserAbortException("User abort, call stop() when calling %s" % message['method'])
        finally:
            self.method_results.pop(message['id'], None)

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
                    logger.error("websocket exception", exc_info=True)
                    self._stopped.set()
                return
            if self.debug:
                print('< RECV %s' % message_json)
            if "method" in message:
                self.event_queue.put(message)
            elif "id" in message:
                if message["id"] in self.method_results:
                    self.method_results[message['id']].put(message)
            else:  
                warnings.warn("unknown message: %s" % message)

    def _handle_event_loop(self):
        while not self._stopped.is_set():
            try:
                event = self.event_queue.get(timeout=1)
            except queue.Empty:
                continue
            if event['method'] in self.event_handlers:
                try:
                    self.event_handlers[event['method']](**event['params'])
                except Exception:
                    logger.error("callback %s exception" % event['method'], exc_info=True)
            self.event_queue.task_done()

    def __getattr__(self, item):
        attr = GenericAttr(item, self)
        setattr(self, item, attr)
        return attr

    def call_method(self, _method, *args, **kwargs):
        if not self._started:
            raise RuntimeException("Cannot call method before it is started")
        if args:
            raise CallMethodException("the params should be key=value format")
        if self._stopped.is_set():
            raise RuntimeException("Browser has been stopped")
        timeout = kwargs.pop("_timeout", None)        
        result = self._send({"method": _method, "params": kwargs}, timeout=timeout)
        if 'result' not in result and 'error' in result:
            warnings.warn("%s error: %s" % (_method, result['error']['message']))
            raise CallMethodException("calling method: %s error: %s" % (_method, result['error']['message']))
        return result['result']

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

    def start(self):
        if self._started:
            return False
        if not self._websocket_url:
            raise RuntimeException("Already has another client connect to this browser")
        self._started = True
        self.status = self.status_started
        self._stopped.clear()
        self._ws = websocket.create_connection(self._websocket_url, enable_multithread=True)        
        self._recv_th.start()
        self._handle_event_th.start()        
        return True

    def stop(self):        
        if self._stopped.is_set():
            return False
        if not self._started:
            raise RuntimeException("Browser is not running")        
        self.status = self.status_stopped        
        self._stopped.set()              
        self._recv_th.join()        
        self._handle_event_th.join()                       
        if self._ws:
            self._ws.close()              
        return True
