#! /usr/bin/env python3

import json
import warnings
import threading
import queue
import websocket

from urllib.request import urlopen
from .service import Service

__all__ = ["Browser"]

class Browser:
    
    def __init__(self, loop=None, opts=[]):       
        self.service = Service(opts)            
        self.dev_url = self.service.url
        self.tab_id = None
        self._cur_id = 1000
        self.started = False
        self.stopped = False
        self.connected = False
        self.event_handlers = {}
        self.method_results = {}
        self.event_queue = queue.Queue()
        self._recv_th = threading.Thread(target=self._recv_loop)
        self._recv_th.daemon = True
        self._handle_event_th = threading.Thread(target=self._handle_event_loop)
        self._handle_event_th.daemon = True
        
    def ws_endpoint(self):
        ws_url = None
        try:
            f = urlopen(f'{self.dev_url}/json/new?')
            data = json.loads(f.read().decode())
            self.tab_id = data.get('id')
            ws_url = data.get('webSocketDebuggerUrl')
        except:            
            pass
        return ws_url
        
    def close_tab(self):
        try:
            urlopen(f"{self.dev_url}/json/close/{self.tab_id}")
        except:
            pass        
        
    def ws_send(self, message):
        if 'id' not in message:
            self._cur_id += 1
            message['id'] = self._cur_id
        message_json = json.dumps(message)        
        try:
            self.method_results[message['id']] = queue.Queue()            
            self._ws.send(message_json)
            while not self.stopped:
                try:
                    return self.method_results[message['id']].get(timeout=1)
                except queue.Empty:                    
                    continue
            raise Exception(f"User abort, call stop() when calling {message['method']}")                           
        finally:
            self.method_results.pop(message['id'], None)

    def _recv_loop(self):
        while not self.stopped:
            try:
                self._ws.settimeout(1)
                message_json = self._ws.recv()
                message = json.loads(message_json)
            except:
                continue            
            if "method" in message:
                self.event_queue.put(message)
            elif "id" in message:
                if message["id"] in self.method_results:
                    self.method_results[message['id']].put(message)
            else:  
                warnings.warn(f"unknown message: {message}")

    def _handle_event_loop(self):
        while not self.stopped:
            try:
                event = self.event_queue.get(timeout=1)
            except queue.Empty:
                continue
            if event['method'] in self.event_handlers:
                try:
                    self.event_handlers[event['method']](**event['params'])
                except Exception:
                    print(f"callback {event['method']} exception")
            self.event_queue.task_done()

    def send(self, _method, *args, **kwargs):
        if not self.started:
            raise Exception("Cannot call method before it is started")
        if args:
            raise Exception("the params should be key=value format")
        if self.stopped:
            raise Exception("browser has been stopped")        
        result = self.ws_send({"method": _method, "params": kwargs})
        if 'result' not in result and 'error' in result:
            warnings.warn(f"{_method} error: {result['error']['message']}")
            raise Exception(f"calling method: {_method} error: {result['error']['message']}")
        return result['result']

    def on(self, event, callback):
        if not callback:
            return self.event_handlers.pop(event, None)
        if not callable(callback):
            raise Exception("callback should be callable")
        self.event_handlers[event] = callback
        return

    def start(self):
        if self.started:
            return
        self.stopped = False
        self.started = True
        self.connected = False
        self._websocket_url = self.ws_endpoint()                            
        self._ws = websocket.create_connection(self._websocket_url, enable_multithread=True)
        if self._ws:
            self.connected = True
            self._recv_th.start()
            self._handle_event_th.start()        
        return

    def stop(self):        
        if self.stopped:
            return
        if not self.started:
            raise Exception("Browser is not running")    
        self.started = False
        self.stopped = True
        if self.connected and self._ws:
            self._ws.close()
            self.close_tab()
            self._recv_th.join()
            self._handle_event_th.join()
            self.connected = False                
        self.service.stop()             
        return
                            
    def __str__(self):
        return f'<Browser {self.dev_url}>' 

    __repr__ = __str__    

    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.__del__()    
        
    def __del__(self):
        try:
            self.stop()
        except Exception:
            pass
                            
                            
