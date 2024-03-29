#! /usr/bin/env python3

import errno
import os
import platform
from subprocess import Popen, PIPE
import time
import socket
from tempfile import TemporaryDirectory
from urllib import request as url_request
from pathlib import Path

URLError = url_request.URLError

class Service(object):

    def __init__(self, opts=[]):
        self.service_args = [
            'about:blank',
            '--disable-background-networking',
            '--disable-background-timer-throttling',
            '--disable-breakpad',
            '--disable-browser-side-navigation',
            '--disable-client-side-phishing-detection',
            '--disable-default-apps',
            '--disable-infobars',
            '--disable-dev-shm-usage',
            '--disable-features=IsolateOrigins,site-per-proces',
            '--disable-hang-monitor',
            '--disable-prompt-on-repost',
            '--disable-sync',
            '--disable-translate',
            '--metrics-recording-only',
            '--no-first-run',
            '--safebrowsing-disable-auto-update',
            '--password-store=basic',
            '--use-mock-keychain',
            '--ignore-ssl-errors',
            '--ignore-certificate-errors',
            '--remote-allow-origins=*',
        ]
        self.path = 'google-chrome'
        if platform.system() == 'Windows':
            self.path = self.find()
        elif platform.system() == 'Darwin':
            self.path = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
        self.tmpdir = TemporaryDirectory()
        self.port = self.free_port()
        self.service_args += opts
        self.service_args += [f'--user-data-dir={self.tmpdir.name}']
        self.service_args += [f'--remote-debugging-port={self.port}']
        self.env = os.environ
        self.url = f"http://localhost:{self.port}"
        self.process = None
        self.start()

    def find(self):
        path = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
        if not os.path.isfile(path):
            path = "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
        if not os.path.isfile(path):
            home = str(Path.home())
            path = home + "\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe"
        return path

    def free_port(self):
        free_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        free_socket.bind(('0.0.0.0', 0))
        free_socket.listen(5)
        port = free_socket.getsockname()[1]
        free_socket.close()
        return port

    def start(self):
        try:
            cmd = [self.path]
            cmd.extend(self.service_args)
            self.process = Popen(cmd, env=self.env, close_fds=platform.system() != 'Windows', stdout=PIPE, stderr=PIPE, stdin=PIPE)
        except TypeError:
            raise
        except OSError as err:
            if err.errno == errno.ENOENT:
                raise ChromeException(f"'{os.path.basename(self.path)}' executable needs to be in PATH.")
            elif err.errno == errno.EACCES:
                raise ChromeException(f"'{os.path.basename(self.path)}' executable may have wrong permissions.")
            else:
                raise
        except Exception as e:
            raise ChromeException(f"The executable {os.path.basename(self.path)} needs to be available in the path.\n{e}")
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
            raise ChromeException(f'Service {self.path} unexpectedly exited. Status code was: {return_code}')

    def is_connectable(self):
        socket_ = None
        try:
            socket_ = socket.create_connection(('localhost', self.port), 1)
            result = True
        except socket.error:
            result = False
        finally:
            if socket_:
                socket_.close()
        return result

    def send_remote_shutdown_command(self):
        try:
            url_request.urlopen(f"{self.url}/shutdown")
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
                for stream in [self.process.stdin, self.process.stdout, self.process.stderr]:
                    try:
                        stream.close()
                    except AttributeError:
                        pass
                self.process.terminate()
                self.process.wait()
                self.process.kill()
                self.process = None
                time.sleep(0.5)
        except OSError:
            pass
        try:
            self.tmpdir.cleanup()
        except:
            pass

    def __enter__(self):
        return self
    
    def __exit__(self):
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
        exception_msg = f"Message: {self.msg}\n" 
        if self.screen is not None:
            exception_msg += "Screenshot: available via screen\n"
        if self.stacktrace is not None:
            stacktrace = "\n".join(self.stacktrace)
            exception_msg += f"Stacktrace:\n{stacktrace}"
        return exception_msg
