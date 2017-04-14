#!/usr/bin/env python
# -*- coding: utf-8 -*-
##########################################################
#   Teach Wisedom To Machine.
#   Please Call Me Programming devil.
#   Model Name: BaseService
######################################################## #
import MultiProcessWrapper as mpw
from EpollServer import *
import os
import thread
import traceback
import time
import commands

logger = logging.getLogger()
statuslogger = logging.getLogger("statusLogger")
netLogger = logging.getLogger("netLogger")
managerLogger = logging.getLogger("managerLogger")
listen_addr_list = [("0.0.0.0", 8554)]
work_process_count = 5
project_index = 0


class BaseAcceptor(ConnectionBase):
    '''Init connection
    '''

    def __init__(self, client_session_id=-1, client_socket=None, client_addr=()):
        super(BaseAcceptor, self).__init__(client_session_id, client_socket, client_addr)
        self.connection_type = CONNECT_TYPE.IS_ACCEPTOR
        self.connect_status = CONNECT_STATUS.CONNECT_SUCC
        self.max_send_buffer_size = 1024 * 2
        self.max_recv_buffer_size = 1024 * 1024 * 10
        self.max_keeplive_time = 600  # seconds
        self.send_count = 0
        self.task_list = []

    def onDisconnectEvent(self):
        super(BaseAcceptor, self).onDisconnectEvent()

    def onTimerEvent(self, current_time):
        if not super(BaseAcceptor, self).onTimerEvent(current_time):
            return False
        self.keeplive()
        return True

    # 处理收到的数据
    def _process_recv_buffer(self):
        global serviceRunningStatus
        total_bufsize = len(self.recv_buffer)
        has_unpack_bufsize = 0
        while has_unpack_bufsize < total_bufsize:
            (unpack_size, packet_head) = self._unpack_frombuffer(self.recv_buffer[has_unpack_bufsize:])
            if unpack_size == 0:
                break
            if unpack_size < 0:
                return unpack_size
            self._dispatch_packet(packet_head, self.recv_buffer[has_unpack_bufsize:has_unpack_bufsize + unpack_size])
            has_unpack_bufsize += unpack_size
            serviceRunningStatus.recv(unpack_size)
        # else:
        #    print "process all:",has_unpack_bufsize,total_bufsize
        return has_unpack_bufsize

    # how to unpack a packet from buffer
    def _unpack_frombuffer(self, buffer=""):
        raise NotImplementedError()
        return (0, None)

    # packet_data is full packet
    def _dispatch_packet(self, head=None, packet_data=""):
        print ">>_dispatch_packet"
        raise NotImplementedError()

    # how to keep live
    def keeplive(self):
        raise NotImplementedError()


def feedback_consumer(gracefulexit_event, serv):
    managerLogger.debug("feedback_consumer start")
    try:
        processMaxNum = 100
        while not gracefulexit_event.is_stop():
	    serv.feedback_once()                        
        else:
            managerLogger.error("feedback_consumer got parent exit notify")
            return
    except mpw.GracefulExitException:
        managerLogger.error("feedback_consumer got graceful exit exception.")
        return
    except:
        info = sys.exc_info()
        for file, lineno, function, text in traceback.extract_tb(info[2]):
            str_info = "feedback_consumer>{0} line:{1} in function:{2}".format(file, lineno, function)
            managerLogger.critical(str_info)
            str_text = "feedback_consumer>** %s: %s" % info[:2]
            managerLogger.critical(str_text)
        managerLogger.critical("feedback_consumer caught unhandle exception")

    finally:
        managerLogger.critical("feedback_consumer exit")


class HeavyWorker(mpw.SimpleWorker):
    def __init__(self, worker_id=0, serv=None):
        super(HeavyWorker, self).__init__()
        self._worker_id = worker_id
        self._serv = serv
        pass

    def onStart(self, gracefulexit_event):
        self.task_process_count = 0
        pid = os.getpid()
        pid = str(pid)
        if self._worker_id == 0:
            self._serv.start()
            managerLogger.info("tcpservice process start,pid:%s", pid)
            with open("run/tcpservice.pid", "w") as f:
                f.write(pid)
                f.write(" ")
            thread.start_new_thread(feedback_consumer, (gracefulexit_event, self._serv))
            return
        if self._worker_id != 0:
            managerLogger.info("worker_%d process start,pid:%s", self._worker_id, pid)
            with open("run/worker_{0}.pid".format(self._worker_id), "w") as f:
                f.write(pid)
                f.write(" ")
                # exec("from gevent import monkey; monkey.patch_all();import gevent;")
        pass

    def onEnd(self, end_code, end_reason):
        if self._worker_id == 0:
            pid = os.getpid()
            managerLogger.info("tcpservice end at pid:{0} reason:{1}".format(pid, end_reason))
        if end_code < 0:
            print end_reason
            return
        if end_code == 2:
            self.onExit()
        pass

    def onRunOnce(self):
        processSuccNum = 0
        processMaxNum = 1000
        if self._worker_id == 0:
            self._serv.serve_once()
            return
        if self._worker_id != 0:            
            self._serv.task_once() 
            return

    def onTimer(self):
        pass

    def onExit(self):
        if self._worker_id == 0:
            self._serv.stop()
        pass


class MasterTimer(mpw.TimerInterface):
    def __init__(self):
        pass

    def timeout(self):
        return 2

    def onTimer(self):
        pass


def process_entry(serv):
    global work_process_count
    pid = os.getpid()
    pid = str(pid)
    managerLogger.info("master process start,pid:%s,workercount:%d", pid, work_process_count)
    with open("run/master.pid", "w") as f:
        f.write(pid)
        f.write(" ")
    if work_process_count == 1:
        print "single_process_entry>> begin"
        InterruptableTaskLoop(serv).startAsForver()
        print "single_process_entry>> end"
        return
    managerLogger.debug("###############begin###################")
    worker_list = [HeavyWorker(i, serv) for i in range(work_process_count)]
    p = mpw.MultiProcessWrapper()
    p.startAsForver(worker_list, MasterTimer())
    managerLogger.debug("###############end###################")


def process_exit(service_name='',server={}):
    global work_process_count
    print "******process_exit*****",Utils.getYmdHMS()
    master_pid=Utils.file2str('run/master.pid')
    if not master_pid:
	print "master_pid NULL"
        return
    print "master_pid:",master_pid
    tcpservice_pid=Utils.file2str('run/tcpservice.pid')
    if not tcpservice_pid:
       print "tcpservice_pid NULL"
       return
    print "tcpservice_pid:",tcpservice_pid
    worker_pids = [master_pid,tcpservice_pid]
    for i in xrange(work_process_count):
        worker_pid_file='run/worker_{0}.pid'.format(i)        
        worker_pid=Utils.file2str( worker_pid_file)
        if worker_pid:
            worker_pids.append(worker_pid)
            print "worker_pid:",worker_pid

    
    for pid in worker_pids:
        print "-------------------------------------"
        cmd='pidof python'
        results=commands.getoutput(cmd)
        if not results:
            print "No Python Process is running"
	    return
	killcmd='kill {0}'.format(pid) if master_pid==pid else 'kill -9 {0}'.format(pid)
        i=0
        while True:
            print i,cmd,"->",results," ->",pid
            if (pid not in results) or i>=8:
                break              
	     	    
            print i,killcmd,commands.getstatusoutput( killcmd )
            time.sleep(2)
	    results=commands.getoutput(cmd)
            if not results:
                break
	    i += 1	
        print "Close pid:",pid

    if not  server:
	return
    ip,port=server["host"], server["port"]
    print "Service should work at:",ip,port
    result=os.popen("netstat -ntlp|grep {0}".format(port) ).read()
    if result:
        print "---------------------------"
        print "Notice It:"
        print result
        return
    print "DONE"

def process_is_running():
    global work_process_count        
    master_pid=Utils.file2str('run/master.pid')   
    if not master_pid:
        #print "master_pid NULL"
        return False
    tcpservice_pid=Utils.file2str('run/tcpservice.pid')
    if not tcpservice_pid:
        #print "tcpservice_pid NULL"
        return False
    worker_pids = [master_pid,tcpservice_pid]
    for i in xrange(work_process_count):
        worker_pid_file='run/worker_{0}.pid'.format(i)
        worker_pid=Utils.file2str( worker_pid_file)
        if  worker_pid:
            worker_pids.append(worker_pid)
            #print "workerid:",worker_pid,len(worker_pid)

    #print worker_pids
    cmd='pidof python'
    results=commands.getoutput(cmd)
    #print results
    if not results:
	return False
 
    for pid in worker_pids:        
	if pid not in results:
	    return False
    return True	
    

def process_monit():
    while True:
        if process_is_running():
            print "OK"
	    time.sleep(15)
            continue
        process_exit()
        time.sleep(10)
        os.popen("./start.sh")
        time.sleep(2)
        
        
	    

