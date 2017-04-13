#!/usr/bin/env python
# -*- coding: utf-8 -*-
##########################################################
#   Teach Wisedom To Machine.
#   Please Call Me Programming devil.
#
######################################################## #

import urllib, urllib2, socket
from urllib2 import URLError, HTTPError
import traceback
import httplib, ssl
from functools import wraps
import socket

def sslwrap(func):
    @wraps(func)
    def bar(*args, **kw):
        kw['ssl_version'] = ssl.PROTOCOL_TLSv1
        return func(*args, **kw)
    return bar
ssl.wrap_socket = sslwrap(ssl.wrap_socket)


def openHttpDebug():
    httpHandler = urllib2.HTTPHandler(debuglevel=1)
    httpsHandler = urllib2.HTTPSHandler(debuglevel=1)
    opener = urllib2.build_opener(httpHandler, httpsHandler)
    urllib2.install_opener(opener)




class HTTPSConnectionV3(httplib.HTTPSConnection):
    def __init__(self, *args, **kwargs):
        httplib.HTTPSConnection.__init__(self, *args, **kwargs)

    def connect(self):
        print "HTTPSConnectionV3 connect() host:{0} port:{1}".format(self.host,self.port)
        #self.host="222.189.23.246"
        sock = socket.create_connection((self.host, self.port), self.timeout)
        if self._tunnel_host:
            self.sock = sock
            self._tunnel()
        try:
            self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file, ssl_version=ssl.PROTOCOL_TLSv1)
        except ssl.SSLError, e:
            print("Trying SSLv3.sslError:{0}".format(e))
            # try:
            #     self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file, ssl_version=ssl.PROTOCOL_SSLv23)
            # except ssl.SSLError, e:
            #     print("Trying SSLv23.sslError:{0}".format(e))
            #     try:
            #         self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file, ssl_version=ssl.PROTOCOL_TLSv1)
            #     except ssl.SSLError, e:
            #         print("Trying TLSv1.sslError:{0}".format(e))
        except Exception,e:
            print e

class HTTPSHandlerV3(urllib2.HTTPSHandler):
    def https_open(self, req):
        return self.do_open(HTTPSConnectionV3, req)



def doHttpGetRequest(url,headers={}):
    error="no error"
    try:
        print "doHttpGetRequest:",url
        if url[:5]=="https":
            urllib2.install_opener(urllib2.build_opener(HTTPSHandlerV3()))
            print "-use https--"
        req = urllib2.Request(url=url,headers=headers)
        response = urllib2.urlopen(req)
        rsp_data = response.read()
        return rsp_data
    except URLError, e:
        if hasattr(e, 'code'):
            error = "doHttpGetRequest() failed;The server couldn\'t fulfill the request; ErrCode:{0}".format(e.code)
        elif hasattr(e, 'reason'):
            error = "doHttpGetRequest() failed;We failed to reach a server. reason:{0}".format(e.reason)
    except:
        error = traceback.format_exc()

    print error
    return ""



class HttpClient(object):
    def __init__(self,timeout=5,debug=True):
        self.header={}
	self.timeout=timeout
        self.debug =debug
        self.error=""
        if self.debug:            
            openHttpDebug()
        pass
    def set_header(self,header={}):
        self.header=header
    def get_header(self):
        return self.header

    def do_get(self,url):
	self.error=""
        try:
            if url[:5] == "https":
                urllib2.install_opener(urllib2.build_opener(HTTPSHandlerV3()))
            req = urllib2.Request(url=url, headers=self.header)
            response = urllib2.urlopen(req,timeout=self.timeout)
            rsp_data = response.read()
            return rsp_data
        except urllib2.URLError,e:
            self.error="<%s>Failed"%(url)
            if hasattr(e, "code"):
                self.error += " Code:"+str(e.code)
            if hasattr(e, "reason"):
                self.error += " Reason:"+str(e.reason)
        return ""


