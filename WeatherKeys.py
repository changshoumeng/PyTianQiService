#!/usr/bin/env python
# -*- coding: utf-8 -*-
##########################################################
#   Teach Wisedom To Machine.
#   Please Call Me Programming devil.
#
######################################################## #
from  HttpModule import *
from xml.etree import ElementTree as ET

def download_citykeys():
    url= "http://mobile.weather.com.cn/js/citylist.xml"
    http_client = HttpClient()
    response = http_client.do_get(url)
    with open("citylist.xml",'w') as f:
        f.write(response)
        # 101340406


def pareXml():
    fileName = "QCPWeatherCity.plist"
    per = ET.parse(fileName)
    p = per.findall('./array/dict')

    resultList = []
    for oneper in p:
        # print "*"*12
        item = dict()
        keyList = []
        valList = []
        count = 0
        for child in oneper.getchildren():
            if child.tag == "key":
                keyList.append(child.text)
                count += 1
            elif child.tag == "string" or child.tag == "integer":
                valList.append(child.text)
            else:
                print "ERROR:", child.tag, ':', child.text
                return
        for i in xrange(count):
            item[keyList[i]] = valList[i]
            # print item
        resultList.append(item)
    return resultList

def writeLine2File(cityidList):
    with open('citylist.conf','w') as f:
        f.write("10\n")
        for cityid in cityidList:
            cityid=cityid.strip()
            f.write(cityid)
            f.write('\n')
    print "writeDone:",len(cityidList)


def load_citykeys():
    tree = ET.parse("citylist.xml")
    root = tree.getroot()
    root=tree.findall('./c/d')
    for child in root:
        print child.tag,child.attrib['d1']



save_citykeys()
