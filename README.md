# rbchrome

[![PyPI](https://img.shields.io/pypi/pyversions/pyppeteer.svg)](https://github.com/anbuhckr/rbchrome)

A Python Package for the Google Chrome Dev Protocol

## Table of Contents

* [Installation](#installation)
* [Getting Started](#getting-started)
* [Ref](#ref)


## Installation

To install rbchrome from GitHub:

```
$ pip install -U git+https://github.com/anbuhckr/rbchrome.git
```

## Getting Started

``` python
import rbchrome
import time

def request_will_be_sent(**kwargs):
    print(f"loading: {kwargs.get('request').get('url')}")

options = [
    "--ignore-certificate-errors",
    "--ignore-ssl-errors",
]
browser = rbchrome.Browser(headless=True, rb_options=options)
browser.set_listener("Network.requestWillBeSent", request_will_be_sent)
browser.start()
browser.run_command("Network.enable")
try:
    browser.run_command("Page.navigate", url="https://github.com/anbuhckr/rbchrome", _timeout=10)
    time.sleep(5)
except KeyboardInterrupt:
    driver.stop()
except TimeoutException:
    print("Browser Timeout!!!")
    pass
except Exception as e:
    print(e)
    pass
finally:
    browser.stop()
```

more methods or events could be found in
[Chrome DevTools Protocol](https://chromedevtools.github.io/devtools-protocol/tot/)


## Ref

* [pychrome](https://github.com/fate0/pychrome/)
* [chrome-remote-interface](https://github.com/cyrus-and/chrome-remote-interface/)
* [Chrome DevTools Protocol](https://chromedevtools.github.io/devtools-protocol/tot/)
