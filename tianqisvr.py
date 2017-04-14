#!/usr/bin/env python
# -*- coding: utf-8 -*-
##########################################################
#   Teach Wisedom To Machine.
#   Please Call Me Programming devil.
#
######################################################## #

import logging.config
logging.config.fileConfig("./conf/logging.conf")
logger = logging.getLogger()
statuslogger = logging.getLogger("statusLogger")
netLogger = logging.getLogger("netLogger")
managerLogger = logging.getLogger("managerLogger")

from netcore import BaseService
from netcore import EpollServer
from netcore import MsgPipe
from netcore import ServerConfig
from netcore import Utils
import Protocol
import KvCache
import DataSource
import os
import sys


class TianQiAcceptor(BaseService.BaseAcceptor):
    def __init__(self, client_session_id=-1, client_socket=None, client_addr=()):
        super(TianQiAcceptor, self).__init__(client_session_id, client_socket, client_addr)

    # how to keep live
    def keeplive(self):
        # self.sendData(Protocol.KEEPLIVE_PACKET_DATA)
        pass

    # how to unpack a packet from buffer
    def _unpack_frombuffer(self, buffer=""):
        return Protocol.httpheader_unpackfrombuffer(buffer)

    def send_data_bychunked(self,data=""):
        ss='''HTTP/1.1 200 OK\r\nServer: nginx/1.6.0\r\nConnection: close\r\nContent-Type: text/html\r\nTransfer-Encoding: chunked\r\n'''
        ss += "\r\n"
        i=0
        total = len(data)
        while i<total:
            chucked_size=0
            if total >= i+512:
                chucked_size=512
            else:
                chucked_size=total-i
            checked_data = data[i:i+chucked_size]
            ss += Utils.dec2hex(chucked_size)+"\r\n"
            ss += checked_data+"\r\n"
            i  += chucked_size
        ss += "0\r\n\r\n"
        self.sendData(ss)
	#logger.debug("send_data_bychunked>>%d",len(data))

    def send_data_bytext(self,data=""):
        length=len(data)
        ss = "HTTP/1.1 200 OK\r\nServer: nginx/1.6.0\r\nContent-Type: text/html\r\nConnection: close\r\n"
        ss +="Content-Length: "+ str(length)+"\r\n"
        ss += "\r\n"
        ss += data
        self.sendData(ss)


    # packet_data is full packet
    def _dispatch_packet(self, head=Protocol.NET_HEAD(), packet_data=""):
        header = packet_data
        url=Protocol.get_url(header)        
        if not url:
            return
        params=Protocol.urlparams2dict(url)
        try:
            service = url[0:8]
            if service != "/chelun?":
                #logger.error("Recv|not chelun service:%s|header:%s",url,header)
                return
            query = params["query"]
            cityid= params["cityid"]
	    if not query:
		logger.error("Recv|invalid query:%s",url)
		return		    
	    
	    citykey=DataSource.get_weather_citykey(cityid)
	    if not citykey:
		logger.error("Recv|invalid cityid:%s",url);		        
		return	   	
	   		
 	    #logger.debug("Recv|Url:%s",url)
            task = Protocol.REQUEST_PACKET()
            task.request_type = head.request_type
            task.request_key = citykey
            task.request_tick = Utils.gettickcount()

            if query in ["weather","weather2"]:		
                weather_data=KvCache.get_data_from_cache(k=citykey  )
                if not weather_data:
                    logger.debug("Recv|get_data_from_cache failed;then ask worker;%s",url)
                    MsgPipe.MsgPipe.push(fileno=self.client_socket.fileno(), sessionid=self.client_session_id,msgdata=task)
                    return                
                logger.debug("Recv|get_data_from_cache succ;%s",url)
                self.send_data_bychunked(weather_data)
                return
            elif query == "weather3":
                task.request_type="TEST" 
                logger.debug("Recv|Test;%s",url)
                MsgPipe.MsgPipe.push(fileno=self.client_socket.fileno(), sessionid=self.client_session_id,
                                     msgdata=task)
                return
            pass

        except:
            pass
        pass


class TianQiServer(EpollServer.EpollServer):
    # listen_addr_list is list of item as (ip,port)
    def __init__(self, listen_addr_list=[]):
        super(TianQiServer, self).__init__(listen_addr_list)
        self._listen_backlog = 1024
        self._epoll_time_out = 0.1
        self._timer_time_out = 2
        self._max_session_count = 10240
        self._last_update_time=Utils.gettimesamp()
	self._last_flush_time=Utils.gettimesamp()

    def onTcpConnectionEnter(self, session_id, client_socket, client_address):
        acceptor = TianQiAcceptor(session_id, client_socket, client_address)
        return acceptor

    def onProcessTimerTask(self):
        now=Utils.gettimesamp()
        if now > self._last_update_time+1800:
		willupdatekeys=KvCache.get_willupdatekeys_from_cache()        
		self._last_update_time=now
		for k in willupdatekeys:
		    task = Protocol.REQUEST_PACKET()
		    task.request_type = "JOB"
                    task.request_key = k
                    task.request_tick = Utils.gettickcount()
                    MsgPipe.MsgPipe.push(fileno=0, sessionid=0,msgdata=task)
        
        if now > self._last_flush_time+60:
		self._last_flush_time=now
		KvCache.flush_cache()

    def task_once(self):
        return MsgPipe.MsgPipe.pop()

    def feedback_once(self):
        return MsgPipe.FeedbackPipe.pop()


class FeadbackConsumer(MsgPipe.FeedbackPipe):
    def __init__(self, serv):
        self.serv = serv

    def out(self, msgnode):
        (fileno, sessionid, msgid, msgdata) = msgnode
        result=msgdata
        #result=Protocol.RESPONSE_PACKET()
        use_delay=result.delay_tick-result.request_tick
        use_process = result.process_tick-result.request_tick
        logger.debug("Feedback>><%s>fileno:%d sessionid:%d msgid:%d key:%s delay:%d process:%d",
                     result.request_type,
                     fileno,
                     sessionid,
                     msgid,
                     result.request_key,
                     use_delay,
                     use_process)
	if not result.data:
	    #logger.error("Feedback>>Failed;invalid data!")
	    return	
	if "TEST" != result.request_type:
            KvCache.set_data_to_cache(result.request_key,result.data)
        if fileno==0 :
	    return
        userSession = self.serv.getAcceptor(fileno, sessionid)
        if not userSession:
            logger.error("Feedback Canot Find Session>><%s>fileno:%d sessionid:%d msgid:%d key:%s delay:%d process:%d",
                     result.request_type,
                     fileno,
                     sessionid,
                     msgid,
                     result.request_key,
                     use_delay,
                     use_process)

            return
        userSession.send_data_bychunked(result.data)


class MsgConsumer(MsgPipe.PipeOutput):
    def __init__(self):
        pass

    def out(self, msgnode):
        (msgid, tick, fileno, sessionid, msgdata) = msgnode        
	request=msgdata
        #request=Protocol.REQUEST_PACKET()
        request.delay_tick=Utils.gettickcount()
        #logger.debug("Worker|PrefetchWeather,key:%s",request.request_key)
	if not request.request_key:
	    logger.error("Worker|invalid requestKey");
	    return	    
        data=""
        if "TEST"==request.request_type:
	    data=DataSource.get_weather_data(request.request_key)
	else:
            data=DataSource.get_enc_weather_data(request.request_key)
        request.process_tick=Utils.gettickcount()
        result = Protocol.RESPONSE_PACKET()
        result.copyHeader(request)
        result.data= data
        msgnode = (fileno, sessionid, msgid, result)	
        MsgPipe.FeedbackPipe.push(msgnode)
        pass

def main():
    BaseService.work_process_count = 10
    BaseService.project_index = 0
    MsgPipe.MsgPipe.callback = MsgConsumer()
    servers = ServerConfig.echo_server_config["servers"]
    project_index = BaseService.project_index
    if len(servers) < project_index + 1:
        managerLogger.debug("###############config errror###################")
        return
    server = servers[project_index]
    if len(sys.argv) == 2:
	if sys.argv[1]=="stop":
    	    BaseService.process_exit(service_name='tianqi',server=server)	
	    return
	if sys.argv[1]=="monit":
	    BaseService.process_monit()
	    return
    DataSource.init_weather_citykeys()
    KvCache.init_cache()
    print "Cache Size:",KvCache.get_cache_size()
    BaseService.listen_addr_list = [(server["host"], server["port"])]
    managerLogger.debug("select project_index:%d ip:%s port:%d", BaseService.project_index, server["host"],
                        server["port"])
    serv = TianQiServer(BaseService.listen_addr_list)
    MsgPipe.FeedbackPipe.callback=FeadbackConsumer(serv)
    BaseService.process_entry(serv)


main()
