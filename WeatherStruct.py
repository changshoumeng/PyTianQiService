#!/usr/bin/env python
# -*- coding: utf-8 -*-
##########################################################
#   Teach Wisedom To Machine.
#   Please Call Me Programming devil.
#
######################################################## #
import json
import time
import random


def conv_str(s):
    if isinstance(s,str):
        return s
    if isinstance(s,unicode):
        return s.encode("utf-8")
    return str(s)

def conv_unicode(s):
    if isinstance(s, unicode):
        return s
    return unicode(s,"utf-8")

class Forecast(object):
    def __init__(self):
        self.fengxiang = ""
        self.fengli = ""
        self.high = 0
        self.low = 0
        self.type1 = ""
        self.type2 = ""
        self.datetime = ""

    def to_json(self):
        f = dict()
        f['fc'] = str(self.high)
        f['fd'] = str(self.low)
        f['fa'] = self.type1
        f['fb'] = self.type2
        return f


class WeatherStruct(object):
    def __init__(self):
        self.usems=0
        self.city=""
        self.citykey=""
        self.aqi=""
        self.wendu = 0
        self.forecastList = []

    def add_forecaset(self, f):
        self.forecastList.append(f)

    def to_json(self):
        js = dict()
        f1=random.choice(self.forecastList )
        f2=random.choice(self.forecastList )
        self.forecastList.append(f1)
        self.forecastList.append(f2)
        js['usems']=self.usems
        js['citykey']=self.citykey
        js['f'] = {}
        js['f']['f1'] = []
        js['f']['f0'] = time.strftime("%Y%m%d%H%M", time.localtime(time.time()))
        for forecast in self.forecastList:
            js['f']['f1'].append(forecast.to_json())
        js['c']={}
        js['c']['c1']=self.citykey
        js['c']['c3']=self.city
        js['c']['c4']=''
        return json.dumps(js, sort_keys=True, separators=(',', ':'))


weather_mapping = {
    u"晴": "00",
    u"多云": "01",
    u"阴": "02",
    u"阵雨": "03",
    u"雷阵雨": "04",
    u"雷阵雨伴有冰雹": "05",
    u"雨夹雪": "06",
    u"小雨": "07",
    u"中雨": "08",
    u"大雨": "09",
    u"暴雨": "10",
    u"大暴雨": "11",
    u"特大暴雨": "12",
    u"阵雪": "13",
    u"小雪": "14",
    u"中雪": "15",
    u"大雪": "16",
    u"暴雪": "17",
    u"雾": "18",
    u"冻雨": "19",
    u"沙尘暴": "20",
    u"小到中雨": "21",
    u"中到大雨": "22",
    u"大到暴雨": "23",
    u"暴雨到大暴雨": "24",
    u"大暴雨到特大暴雨": "25",
    u"小到中雪": "26",
    u"中到大雪": "27",
    u"大到暴雪": "28",
    u"浮尘": "29",
    u"扬尘": "30",
    u"强沙尘暴": "31",
    u"雨": "32",
    u"雪": "33",
    u"阴": "34",
    u"阵雨": "35",
    u"阵雨": "36",
    u"阵雨": "37",
    u"阵雨": "38",
    u"阴": "39",
    u"阴": "40",
    u"霾": "53",

}

def weatcher_find(k=""):
    global weather_mapping
    v = weather_mapping.get(k,"")
    if v:
        return v
    for s in weather_mapping.keys():
        if v in s:
            return v
    return "100"




def weatcher_conv(s=""):
    flag=u'转'
    s=conv_unicode(s)
    p=s.find(flag)
    a=s
    b=""
    fa=""
    fb=""
    if p>2:
        a=s[:p]
        b=s[p+len(flag):]
    if a:
        fa=weatcher_find(a)
    if b:
        fb=weatcher_find(b)
    if not fb:
        fb=fa
    return fa,fb


def wendu_conv(s=""):
    a=['0','1','2','3','4','5','6','7','8','9','.']
    p1=0
    for i in xrange(len(s)):
        c=s[i]
        if c in a:
            p1=i
            break
    p2=0
    for i in xrange(p1,len(s)):
        c=s[i]
        if c not in a:
            p2=i
            break

    return s[p1:p2]
