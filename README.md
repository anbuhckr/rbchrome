# rbchrome

[![GitHub issues](https://img.shields.io/github/issues/anbuhckr/rbchrome)](https://github.com/anbuhckr/rbchrome/issues)
[![GitHub forks](https://img.shields.io/github/forks/anbuhckr/rbchrome)](https://github.com/anbuhckr/rbchrome/network)
[![GitHub stars](https://img.shields.io/github/stars/anbuhckr/rbchrome)](https://github.com/anbuhckr/rbchrome/stargazers)
[![GitHub license](https://img.shields.io/github/license/anbuhckr/rbchrome)](https://github.com/anbuhckr/rbchrome/blob/master/LICENSE)
![PyPI - Python Version](https://img.shields.io/badge/python-3.6%20%7C%203.7%20%7C%203.8-blue)

Chrome DevTools Protocol Package for access lower level methods in Chrome.

## Table of Contents

* [Installation](#installation)
* [Getting Started](#getting-started)
* [Ref](#ref)


## Installation

To install rbchrome from GitHub:

```
$ python3 -m pip install -U git+https://github.com/anbuhckr/rbchrome.git
```

or from source:

```
$ python3 setup.py install
```

## Getting Started

``` python
#! /usr/bin/env python3

import time
from rbchrome.browser import Browser

def request_will_be_sent(**kwargs):
    print(f"loading: {kwargs.get('request').get('url')}")
    
def main():
    # chrome options
    options = [
        "--disable-gpu",
        "--no-sandbox",
        "--disable-setuid-sandbox",
    ]
    
    # create browser instance with custom options
    browser = Browser(opts=options)
    
    # register callback if you want
    browser.on('main', 'Network.requestWillBeSent', request_will_be_sent)
    
    # start browser with custom method
    try:
        browser.start()
        browser.send('Network.enable')
        browser.send('Page.enable')
        browser.send('Page.navigate', url="https://github.com/anbuhckr/rbchrome")
        
        # wait for loading
        time.sleep(10)
        
    # handle exception
    except Exception as e:
        print(e)
        pass
        
    # close browser
    browser.stop()
    
if __name__ == '__main__':
    main()
```
more methods or events could be found in
[Chrome DevTools Protocol](https://chromedevtools.github.io/devtools-protocol/)


## Ref

* [pychrome](https://github.com/fate0/pychrome/)
* [chrome-remote-interface](https://github.com/cyrus-and/chrome-remote-interface/)
* [selenium](https://github.com/SeleniumHQ/selenium/tree/trunk/py/)
* [Chrome DevTools Protocol](https://chromedevtools.github.io/devtools-protocol/)
