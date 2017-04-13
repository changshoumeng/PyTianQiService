#!/usr/bin/env python
# -*- coding: utf-8 -*-
##########################################################
#   Teach Wisedom To Machine.
#   Please Call Me Programming devil.
#
######################################################## #
from netcore import Utils
import copy
import threading
import pickle
import os
import logging
logger = logging.getLogger()
import traceback


weather_data_cache = {}
weather_data_lock = threading.Lock()
cache_file_name="cache.data"
weather_get_count=0
weather_hit_count=0

class WEATHER_DATA(object):
    def __init__(self):
        self.key = ""
        self.request_time = 0
        self.update_time=0
        self.data = ""

    def isValid(self):
        now = Utils.gettimesamp()
        return now < self.update_time + 3600

    def needUpdate(self):
        now = Utils.gettimesamp()
        if now > self.request_time +86400:
            return False
        if now > self.update_time + 1800:
            return True
        return False
    

def get_data_from_cache(k=""):
    global weather_data_cache
    global weather_data_lock
    global weather_get_count
    global weather_hit_count
    with weather_data_lock:
        weather_get_count += 1
        if k in weather_data_cache:
            node = weather_data_cache[k]
            if node.isValid():
                # print "GET:",id(node.data)
                weather_data_cache[k].request_time=Utils.gettimesamp()
                weather_hit_count += 1 
                return copy.deepcopy(node.data)
	    else:
		logger.debug("KvCache|get_data_from_cache|invalid key:%s,now:%d last:%d id:%d  get:%d hit:%d",node.key,Utils.gettimesamp(),node.update_time,id(node),weather_get_count,weather_hit_count)
		pass
			
        return None


def set_data_to_cache(k="", data=""):
    # print "SET:",id(data)
    global weather_data_cache
    global weather_data_lock
    now=Utils.gettimesamp()
    #logger.debug("KvCache|set_data_to_cache|update key:%s t:%d",k,now)
    with weather_data_lock:
        if k not in weather_data_cache:
            node = WEATHER_DATA()
            node.key = k
            node.request_time = now
            node.update_time  = node.request_time
            node.data = data
            weather_data_cache[k] = node
            #logger.debug("KvCache|set_data_to_cache|update key:%s t:%d id:%d",k,now,id(node))		
            return k

        weather_data_cache[k].update_time = now
        weather_data_cache[k].data = data
	#logger.debug("KvCache|set_data_to_cache|update key:%s t:%d id2:%d",k,now,id(weather_data_cache[k]))
        return k


def get_cache_size():
    global weather_data_cache
    global weather_data_lock
    with weather_data_lock:
        return len(weather_data_cache)


def get_willupdatekeys_from_cache():
    global weather_data_cache
    global weather_data_lock
    willupdatekeys=[]
    with weather_data_lock:
        for v in weather_data_cache.values():            
            if v.needUpdate():
                willupdatekeys.append(v.key)
    return willupdatekeys                


def init_cache():
    global weather_data_cache
    global cache_file_name
    if not os.path.exists(cache_file_name):
	return
    try:
        with open(cache_file_name,'rb') as f:
	    weather_data_cache=pickle.load(f)
    except:
        info = sys.exc_info()
        t ='**************Caught Exceptional*************'
        for f,l, func, text in traceback.extract_tb(info[2]):
            t += "\n[file]:{0}\n[line]:{1}\n[func]:{2}\n[text]:{3}".format(f,l,func,text)
            t += "\n[info]:%s->%s\n"%info[:2]
        logger.error(t)    


def flush_cache():    
    global weather_data_cache
    global cache_file_name
    try:
        with open(cache_file_name,'wb') as f:
	    pickle.dump( weather_data_cache, f)
    except:
        info = sys.exc_info()
        t ='**************Caught Exceptional*************'
        for f,l, func, text in traceback.extract_tb(info[2]):
            t += "\n[file]:{0}\n[line]:{1}\n[func]:{2}\n[text]:{3}".format(f,l,func,text)
            t += "\n[info]:%s->%s\n"%info[:2]
        logger.error(t)    
        












