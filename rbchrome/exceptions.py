#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals


class RbChromeException(Exception):
    pass


class UserAbortException(RbChromeException):
    pass


class TabConnectionException(RbChromeException):
    pass


class CallMethodException(RbChromeException):
    pass


class TimeoutException(RbChromeException):
    pass


class RuntimeException(RbChromeException):
    pass
