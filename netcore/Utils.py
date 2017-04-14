#!/usr/bin/env python
# -*- coding: utf-8 -*-
##########################################################
#   Teach Wisedom To Machine.
#   Please Call Me Programming devil.
#   Module Name: Utils
######################################################## #
import os
import time

def file2str(file_name):
    if not os.path.exists(file_name):
	return ""
    with open(file_name,'r') as f:
        return f.read().strip()


def dec2hex(dec):
    s=hex(dec)
    return s[2:]

def getYmdHMS():
    return time.strftime("[%Y-%m-%d %H:%M:%S]", time.localtime(time.time()))


# 毫秒级别时间戳
def gettickcount():
    t = time.time() * 1000
    return int(t)

def gettimesamp():
    t=time.time()
    return int(t)


def gettickcount2(t):
    return int(t * 1000)


def get_ymd_tick():
    a = time.strftime("%Y%m%d", time.localtime(time.time()))
    return int(a)


def parent_dir_name():
    cwd = os.getcwd()
    cwd = cwd.replace('\\', '/')
    pos = cwd.rfind('/')
    if pos == -1:
        return cwd
    return cwd[pos + 1:]


def current_project_index():
    s = parent_dir_name()
    num = ""
    for i in xrange(1, len(s) + 1):
        a = s[-i]
        if a.isdigit():
            num = a + num
        else:
            break
    num = int(num)
    return num


def normalizeNetIO(total_bytes, total_ms):
    if total_ms == 0:
        return "error net io"
    speed = float(total_bytes) / float(total_ms)
    speed = speed * 1000
    if speed < 1024:
        return "{0:0.1f}Bytes/s".format(speed)
    if 1024 <= speed < 1048576:
        return "{0:0.1f}KB/s".format(speed / 1024)
    return "{0:0.1f}MB/s".format(speed / 1048576)
