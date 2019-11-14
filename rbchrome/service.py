#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import errno
import os
import platform
from subprocess import Popen, PIPE
import time
import socket
from tempfile import TemporaryDirectory

class Service(object):
    def __init__(self, port=0, env=None, start_error_message="",
                rb_options=[], headless=False):
        if 'nt' in os.name:
            self.path = find('chrome.exe')
        else:
            self.path = 'google-chrome'
        self.tmpdir = TemporaryDirectory()              
        self.port = port
        if self.port == 0:
            self.port = free_port()           
        self.service_args = rb_options       
        self.service_args += ['about:blank', '--disable-background-networking',
                                '--disable-client-side-phishing-detection',
                                '--disable-default-apps', '--disable-hang-monitor',
                                '--disable-infobars', '--disable-popup-blocking',
                                '--disable-prompt-on-repost', '--disable-sync',
                                '--password-store=basic', '--no-first-run',                             
                                '--ignore-ssl-errors', '--ignore-certificate-errors', 
                                '--metrics-recording-only', '--use-mock-keychain', 
                                '--user-data-dir='  + self.tmpdir.name]            
        self.service_args += ['--remote-debugging-port=' + str(self.port)]
        self.service_args += ['--headless'] if headless else []
        self.start_error_message = start_error_message        
        self.env = env or os.environ                 
        self.start()

    @property
    def url(self):
        return "http://%s" % join_host_port('localhost', self.port)

    def start(self):
        try:
            cmd = [self.path]
            cmd.extend(self.service_args)
            self.process = Popen(cmd, env=self.env,
                                            close_fds=platform.system() != 'Windows',
                                            stdout=PIPE,
                                            stderr=PIPE,
                                            stdin=PIPE)
        except TypeError:
            raise
        except OSError as err:
            if err.errno == errno.ENOENT:
                raise ChromeException(
                    "'%s' executable needs to be in PATH. %s" % (
                        os.path.basename(self.path), self.start_error_message)
                )
            elif err.errno == errno.EACCES:
                raise ChromeException(
                    "'%s' executable may have wrong permissions. %s" % (
                        os.path.basename(self.path), self.start_error_message)
                )
            else:
                raise
        except Exception as e:
            raise ChromeException(
                "The executable %s needs to be available in the path. %s\n%s" %
                (os.path.basename(self.path), self.start_error_message, str(e)))
        count = 0
        while True:
            self.assert_process_still_running()
            if self.is_connectable():
                break
            count += 1
            time.sleep(1)
            if count == 30:
                raise ChromeException("Can not connect to the Service %s" % self.path)

    def assert_process_still_running(self):
        return_code = self.process.poll()
        if return_code is not None:
            outs, errs = self.process.communicate(timeout=15)
            print("\nChrome STDOUT:\n" + outs.encode() + "\n\n")
            print("\nChrome STDERR:\n" + errs.encode() + "\n\n")
            raise ChromeException(
                'Service %s unexpectedly exited. Status code was: %s'
                % (self.path, return_code)
            )

    def is_connectable(self):
        return is_connectable(self.port)

    def send_remote_shutdown_command(self):
        try:
            from urllib import request as url_request
            URLError = url_request.URLError
        except ImportError:
            import urllib2 as url_request
            import urllib2
            URLError = urllib2.URLError

        try:
            url_request.urlopen("%s/shutdown" % self.url)
        except URLError:
            return

        for x in range(30):
            if not self.is_connectable():
                break
            else:
                time.sleep(1)

    def stop(self):        
        if self.process is None:
            return
        try:
            self.send_remote_shutdown_command()
        except TypeError:
            pass
        try:
            if self.process:
                for stream in [self.process.stdin,
                               self.process.stdout,
                               self.process.stderr]:
                    try:
                        stream.close()
                    except AttributeError:
                        pass
                self.process.terminate()
                self.process.wait()
                self.process.kill()
                self.process = None
                time.sleep(0.5)
                try:
                    self.tmpdir.cleanup()
                except Exception:
                    pass
        except OSError:
            pass

    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.__del__()    
        
    def __del__(self):
        try:
            self.stop()
        except Exception:
            pass       

class ChromeException(Exception):
    def __init__(self, msg=None, screen=None, stacktrace=None):
        self.msg = msg
        self.screen = screen
        self.stacktrace = stacktrace

    def __str__(self):
        exception_msg = "Message: %s\n" % self.msg
        if self.screen is not None:
            exception_msg += "Screenshot: available via screen\n"
        if self.stacktrace is not None:
            stacktrace = "\n".join(self.stacktrace)
            exception_msg += "Stacktrace:\n%s" % stacktrace
        return exception_msg

def free_port():
    free_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    free_socket.bind(('0.0.0.0', 0))
    free_socket.listen(5)
    port = free_socket.getsockname()[1]
    free_socket.close()
    return port

def find(name):
    for root, dirs, files in os.walk("C:/"):
        if name in files:
            return os.path.join(root, name).replace("\\", "/")

def is_connectable(port, host="localhost"):
    socket_ = None
    try:
        socket_ = socket.create_connection((host, port), 1)
        result = True
    except socket.error:
        result = False
    finally:
        if socket_:
            socket_.close()
    return result

def join_host_port(host, port):
    if ':' in host and not host.startswith('['):
        return '[%s]:%d' % (host, port)
    return '%s:%d' % (host, port)
