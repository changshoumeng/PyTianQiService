#!/usr/bin/env python
# -*- coding: utf-8 -*-
##########################################################
#   Teach Wisedom To Machine.
#   Please Call Me Programming devil.
#
######################################################## #


'''
xml
http://wthrcdn.etouch.cn/WeatherApi?citykey=101010100

json
http://wthrcdn.etouch.cn/weather_mini?citykey=101010100

citylist
http://mobile.weather.com.cn/js/citylist.xml

'''
from xml.etree import ElementTree as ET
from  HttpModule import *
from  GzipModule import *
from  AesPkcs7 import *
from  WeatherStruct import *
import traceback
import logging
logger = logging.getLogger()
import sys

http_header1='''
Accept:text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8\r\n
Accept-Encoding:gzip, deflate, sdch\r\n
Accept-Language:zh-CN,zh;q=0.8\r\n
Cache-Control:no-cache\r\n
Connection:keep-alive\r\n
Pragma:no-cache\r\n
Upgrade-Insecure-Requests:1\r\n
User-Agent:Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36
'''

weather_data_key = ''

def parse_http_header(s=http_header1):
    header={}

    for item in s.split("\r\n"):
        item = item.strip()
        if not item:
            continue
        elements=item.split(":")
        if len(elements)==2:
            e0,e1 = elements[0],elements[1]
            header[e0.strip()]=e1.strip()
        else:
            print "Error:",elements
    return header


def format_weather_data(citykey='',data=""):
    if not data:
        return ""
    try:
       js = json.loads(data)
       if js["status"] != 1000:
           print "status error"
           logger.error("format_weather_data|Failed>Status Error,k:%s d:%s", citykey,data)
           return ""
       dataJs = js["data"]
       weatherObj = WeatherStruct()
       weatherObj.wendu= dataJs["wendu"]
       weatherObj.city=dataJs["city"]
       weatherObj.citykey=citykey
       for item in dataJs["forecast"]:
           fObj=Forecast()
           high=item["high"]
           low=item["low"]
           ttpe=item["type"]
           fObj.type1,fObj.type2=weatcher_conv(ttpe)
           if fObj.type1 != fObj.type2:                  
                  logger.error("format_weather_data|MainInfo k:%s d:%s",citykey ,data );
           fObj.high=wendu_conv(high)
           fObj.low=wendu_conv(low)
           weatherObj.add_forecaset(fObj)
       s= weatherObj.to_json()
       return s
    except TypeError, e:
        logger.error("format_weather_data|Catch TypeError:%s,k:%s,d:%s", repr(e),citykey,data)
	return ""
    except:
	logger.error("format_weather_data|Unhandle Error> k:%s,d:%s",citykey,data)    	
    return ""


def load_citykeys():
    tree = ET.parse("citylist.xml")
    root=tree.findall('./c/d')
    citykeys=[]
    for child in root:
        citykey=child.attrib['d1']
        #print citykey
        citykeys.append(citykey)
        if citykey == "101340406":
            break
    #print "load_citykeys Done:",len(citykeys)
    return citykeys



def get_weather_data(citykey=""):
    #url='http://wthrcdn.etouch.cn/WeatherApi?citykey=101010100'
    url='http://wthrcdn.etouch.cn/weather_mini?citykey={0}'.format(citykey)   
    logger.debug("get_weather_data|url:%s",url)
    http_client=HttpClient(timeout=5,debug=False)
    header = parse_http_header()
    http_client.set_header(header)
    response=http_client.do_get(url)
    if not response:
	logger.error( "get_weather_data|Failed|Error:%s",http_client.error )
	return ""
    data= gzip_uncompress(response)
    logger.debug("get_weather_data|key:%s data:%s",citykey,data)
    data=format_weather_data(citykey,data)
    return data

def get_enc_weather_data(citykey=""):
    try:
	    data=get_weather_data(citykey)
	    #return data	
	    if not data:
	        return ""
	    gzip_data=gzip_compress(data)	
	    global weather_data_key
	    pc = prpcrypt(weather_data_key)  # 初始化密钥
	    enc_data = pc.encrypt(gzip_data)    
	    return enc_data
    except:
	    info = sys.exc_info()
            for file, lineno, function, text in traceback.extract_tb(info[2]):
                s1 = "DataSource>>file:{0} line:{1} in function:{2}".format(file, lineno, function)
                logger.critical(s1)
                s2 = "DataSource>>** %s: %s" % info[:2]
                logger.critical(s2)	


citykeys = []
citykeysSet = set()

def init_weather_citykeys():
    global  citykeys
    global  citykeysSet
    citykeys = load_citykeys()
    citykeysSet = set(citykeys)


def get_weather_citykey(cityid=""):
    global  citykeys
    global  citykeysSet
    if len(cityid)<9:
        return ""
    if cityid in citykeysSet:
        return cityid
    for i in xrange(  len(citykeys) ):
        tgt = citykeys[i]
        if cityid[0:8] == tgt[0:8] :
            return tgt
    return ""




