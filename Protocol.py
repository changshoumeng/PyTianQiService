#!/usr/bin/env python
# -*- coding: utf-8 -*-
##########################################################
#   Teach Wisedom To Machine.
#   Please Call Me Programming devil.
#
######################################################## #
from urlparse import urlparse
import logging
logger = logging.getLogger()

class NET_HEAD(object):
    def __init__(self):
        self.request_type=""
        self.header_size=0

class REQUEST_PACKET(object):
    def __init__(self):
        self.request_type=""
        self.request_key=""
        self.request_tick=0
        self.delay_tick=0
        self.process_tick=0
        pass

class RESPONSE_PACKET(object):
    def __init__(self):
        self.request_type=""
        self.request_key=""
        self.request_tick=0
        self.delay_tick=0
        self.process_tick=0
        self.data=""

    def copyHeader(self,request):
        self.request_type=request.request_type
        self.request_key=request.request_key
        self.request_tick=request.request_tick
        self.delay_tick=request.delay_tick
        self.process_tick=request.process_tick

def httpheader_unpackfrombuffer(buf=""):
    head=NET_HEAD()
    END_FLAG='\r\n\r\n'
    pos=buf.find(END_FLAG)
    if pos < 0:
        return (-1,head)
    http_header = buf[0:pos+len(END_FLAG)]
    request_type=buf[0:4].strip()
    head.request_type=request_type    
    if request_type == "GET":
        head.header_size=len(http_header)
        return (len(http_header),head)
    return (-1,head)
    #if request_type in  [ "POST", "HEAD"] :
    #    pass
    #logger.error("httpheader_unpackfrombuffer Failed; request_type:%s buf:%s",request_type,buf)
    #return (-1,head)


def urlparams2dict(url=""):
    data_dict = {}
    url_obj = urlparse(url)   
    query_str = url_obj.query    
    for item in query_str.split('&'):
        arr = item.split('=')
        if len(arr) == 2:
            k, v = arr[0], arr[1]
            data_dict[k] = v
    return data_dict

def get_url(header=""):
    pos=header.find("\r\n")
    if pos<0:
        logger.error("get_url Failed>1;header:%s",header)
        return ""
    first_line=header[4:pos-4]
    pos=first_line.rfind("HTTP")
    if pos<0:
        logger.error("get_url Failed>2;header:%s", header)
        return ""
    return first_line[0:pos]

