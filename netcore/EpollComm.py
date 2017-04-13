#!/usr/bin/env python
# -*- coding: utf-8 -*-
###################################################
# Teach wisedom to my machine,please call me croco#
#
# reference :
# http://scotdoyle.com/python-epoll-howto.html#async-benefits
# http://blog.csdn.net/yusiguyuan/article/details/15027821
# https://blog.alswl.com/2013/01/python-epoll/
##################################################

import errno
import logging
import select
import signal
import socket
import sys
import threading
import traceback

from Utils import *

netLogger = logging.getLogger("netLogger")
isContinue_event = threading.Event()
is_sigint_up = False
'''
   function:sigint_handler
   定义中断信号的事件处理过程
'''


def sigint_handler(signum, frame):
    global is_sigint_up
    global isContinue_event
    is_sigint_up = True
    isContinue_event.set()
    # print 'sigint_handler,catched interrupt signal!'


def print_epoll_events(fileno, events):
    aList = [
        (select.EPOLLET, "select.EPOLLET"),
        (select.EPOLLIN, "select.EPOLLIN"),
        (select.EPOLLOUT, "select.EPOLLOUT"),
        (select.EPOLLPRI, "select.EPOLLPRI"),
        (select.EPOLLERR, "select.EPOLLERR"),
        (select.EPOLLHUP, "select.EPOLLHUP"),
        (select.EPOLLET, "select.EPOLLET"),
        (select.EPOLLONESHOT, "select.EPOLLONESHOT"),
        (select.EPOLLRDNORM, "select.EPOLLRDNORM"),
        (select.EPOLLRDBAND, "select.EPOLLRDBAND"),
        (select.EPOLLWRNORM, "select.EPOLLWRNORM"),
        (select.EPOLLWRBAND, "select.EPOLLWRBAND"),
        (select.EPOLLMSG, "select.EPOLLMSG"),
    ]
    s = "fileno:{0} events({1}) contains:".format(fileno, events)
    for a in aList:
        if events & a[0]:
            s += " {0}:{1}".format(a[0], a[1])
    netLogger.debug(s)


############################################################################
class ServerInterface(object):
    '''
    class ServerInterface
     定义一个Server的通用接口，被InterruptableTaskLoop调用

    '''

    # ServerInterface.start()
    def start(self):
        raise NotImplementedError()

    # ServerInterface.stop()
    def stop(self):
        raise NotImplementedError()

    # ServerInterface.serve_once()
    def serve_once(self):
        raise NotImplementedError()


############################################################################
class InterruptableTaskLoop(object):
    '''
        class InterruptableTaskLoop
        定义可信号中断的事件循环
    '''

    # worker is implemention of ServerInterface
    def __init__(self, worker, timeout=0):
        if not hasattr(worker, 'start'):
            raise AttributeError("AttributeError:miss method called start() ")
        if not hasattr(worker, 'serve_once'):
            raise AttributeError("AttributeError:miss method called serve_once() ")
        if not hasattr(worker, 'stop'):
            raise AttributeError("AttributeError:miss method called stop() ")
        # if not hasattr(worker, 'notify'):
        #    raise AttributeError("AttributeError:miss method called notify() ")
        self.worker = worker
        self.timeout = timeout
        pass

    @staticmethod
    def wait(timeout):
        if int(timeout) == 0:
            return
        global is_sigint_up
        global isContinue_event
        try:
            isContinue_event.clear()
            isContinue_event.wait(timeout=timeout)
        except:
            pass

    # wait for a while
    def _wait(self):
        InterruptableTaskLoop.wait(self.timeout)

    # if start succ then run a eventloop
    def startAsForver(self):
        global is_sigint_up
        global isContinue_event
        is_sigint_up = False
        if not self.worker.start():
            netLogger.critical("taskloop>>start failed,then system.exit")
            return
        try:
            netLogger.debug("taskloop>>start ok")
            signal.signal(signal.SIGINT, sigint_handler)
            self.worker.serve_once()
            netLogger.debug("taskloop>>serve_once ok")

            while not is_sigint_up:
                try:
                    self._wait()
                    if not self.worker.serve_once():
                        netLogger.critical("taskloop>>serve_once failed!!!")
                        break
                except:
                    netLogger.critical("taskloop2>>" + "*" * 15)
                    info = sys.exc_info()
                    for file, lineno, function, text in traceback.extract_tb(info[2]):
                        s1 = "taskloop2>>file:{0} line:{1} in function:{2}".format(file, lineno, function)
                        netLogger.critical(s1)
                        s2 = "taskloop2>>** %s: %s" % info[:2]
                        netLogger.critical(s2)
                    netLogger.critical("taskloop2>>" + "#" * 15)
            else:
                netLogger.critical("taskloop2>>catched interrupt signal!!!")

        except:
            netLogger.critical("taskloop1>>" + "*" * 15)
            info = sys.exc_info()
            for file, lineno, function, text in traceback.extract_tb(info[2]):
                s1 = "taskloop1>>file:{0} line:{1} in function:{2}".format(file, lineno, function)
                netLogger.critical(s1)
                s2 = "taskloop1>>** %s: %s" % info[:2]
                netLogger.critical(s2)
            netLogger.critical("taskloop1>>" + "#" * 15)
            return
        finally:
            self.worker.stop()
            netLogger.warning("taskloop>>stop")
            return


def loop_wait(timeout):
    return InterruptableTaskLoop.wait(timeout)


############################################################################
class EpollLoop(object):
    """
    A epoll-based event loop implementation for
    system supporting epoll system-call.
    """

    def __init__(self, ):
        if not hasattr(select, 'epoll'):
            raise SystemError("Not support epoll for current system.")
        self._epoll = select.epoll()

    def close(self):
        self._epoll.close()

    def register(self, fd, event_type):
        self._epoll.register(fd, event_type)

    def unregister(self, fd):
        self._epoll.unregister(fd)

    def modify(self, fd, event_type):
        self._epoll.modify(fd, event_type)
        print "epoll loop modify fd:{0} event:{1}".format(fd, event_type)

    def poll(self, timeout):
        return self._epoll.poll(timeout)


############################################################################

class CONNECT_STATUS(object):
    '''
    定义常量，描述client_status的值
    '''
    CONNECT_SUCC = 0  # 连接是好的
    CONNECT_DOING = 1  # 客户端正在连接
    CONNECT_FAIL = 2  # 客户端连接服务端，一连接就失败了
    CONNECT_LOSELIVE = 3  # 超时失活
    CONNECT_CLI_WILLCONNECT = 10  # 客户端将要连接
    CONNECT_CLI_WILLCLOSED = 11  # 将要被关闭，是因为客户端断开了连接，或者检查连接无效了
    CONNECT_SER_WILLCLOSED = 12  # 将要被关闭，是因为该连接上检查到不符合逻辑行为
    CONNECT_SYS_WILLCLOSED = 13  # 将要被关闭，是因为系统资源准备不足,异常，程序BUG
    CONNECT_CLOSED = 20  # 已经关闭


############################################################################

class CONNECT_TYPE(object):
    '''
    定义常量，connection_type
    '''
    IS_CONNECTOR = 0
    IS_ACCEPTOR = 1


############################################################################



class ConnectionBase(object):
    '''
       连接器的基类
    '''
    __slots__ = (
        'connection_type',
        'client_session_id',
        'client_socket',
        'client_addr',
        'connect_status',
        'max_recv_buffer_size',
        'max_send_buffer_size',
        'recv_buffer',
        'send_buffer',
        'send_buffer_lock',
        'is_writtable',
        'send_bytes',
        'recv_bytes',
        'max_sendonce_size',
        'max_recvonce_size',
        'begin_timestamp',
        'last_recv_time',
        'max_keeplive_time',
        'session_uuid',

    )
    BUSYING_STATUS = [errno.EAGAIN, errno.EWOULDBLOCK, errno.EINTR]

    def __init__(self, client_session_id=-1, client_socket=None, client_addr=()):
        self.connection_type = CONNECT_TYPE.IS_ACCEPTOR
        self.client_session_id = client_session_id
        self.client_socket = client_socket
        self.client_addr = client_addr
        self.connect_status = CONNECT_STATUS.CONNECT_SUCC
        self.max_recv_buffer_size = 16 * 1024
        self.max_send_buffer_size = 16 * 1024
        self.max_keeplive_time = 60
        self.recv_buffer = ''
        self.send_buffer = ''
        self.is_writtable = True
        self.send_buffer_lock = threading.Lock()
        self.begin_timestamp = gettimesamp()
        self.last_recv_time = self.begin_timestamp
        self.send_bytes = 0
        self.recv_bytes = 0
        self.max_sendonce_size = 0
        self.max_recvonce_size = 0
        fileno = -1 if not self.client_socket else self.client_socket.fileno()
        self.session_uuid = "t{0}_s{1}_f{2}".format(self.connection_type,
                                                 self.client_session_id,
                                                 fileno
                                                 )
        netLogger.info("init|{0}".format(self.session_uuid))
        # netLogger.debug("onReadEvent|%s",self.session_uuid)

    # 是否正在连接
    def isConnecting(self):
        return self.connect_status == CONNECT_STATUS.CONNECT_DOING

    # 是否连接完全正常
    def isConnectSucc(self):
        return self.connect_status == CONNECT_STATUS.CONNECT_SUCC


    def isClosedByClient(self):
        return self.connect_status == CONNECT_STATUS.CONNECT_CLI_WILLCLOSED

    def get_intval(self):
        if self.isConnectSucc():
            return 1
        return 0

    def onReadEvent(self):
        recv_count = 0
        while self.connect_status == CONNECT_STATUS.CONNECT_SUCC:
            try:
                if recv_count > 128:
                    netLogger.warning("onReadEvent|%s,recv too slow!!!", self.session_uuid)
                    return True

                canrecvLen = self.max_recv_buffer_size - len(self.recv_buffer)
                if canrecvLen <= 4:
                    self.connect_status = CONNECT_STATUS.CONNECT_SYS_WILLCLOSED
                    netLogger.warning("onReadEvent|%s,recv_buffer is not enough to canrecvLen!", self.session_uuid)
                    return False

                data = self.client_socket.recv(canrecvLen)
                if not data:
                    netLogger.warning("onReadEvent|%s,recv 0", self.session_uuid)
                    self.connect_status = CONNECT_STATUS.CONNECT_CLI_WILLCLOSED
                    return False

                recvonce_size = len(data)
                self.last_recv_time = time.time()
                if recvonce_size > self.max_recvonce_size:
                    self.max_recvonce_size = recvonce_size
                self.recv_bytes += recvonce_size

                if recv_count >= 32:
                    netLogger.debug("onReadEvent|%s,i:%d,canrecv:%d,recvonce:%d,maxrcvsize:%d",
                                    self.session_uuid,
                                    recv_count,
                                    canrecvLen,
                                    recvonce_size,
                                    self.max_recvonce_size)

                recv_count += 1
                self.recv_buffer += data
                begin_tick = gettickcount()
                processed_size = self._process_recv_buffer()
                use_tick = gettickcount() - begin_tick
                if use_tick >= 100:
                    netLogger.warning("process_recv_buffer|%s,i:%d,procsize:%d,usetime:%d",
                                      self.session_uuid,
                                      recv_count,
                                      processed_size,
                                      use_tick)

                if processed_size == len(self.recv_buffer):
                    self.recv_buffer = ''
                    # print "finish to process allpacket"
                elif processed_size < len(self.recv_buffer):
                    self.recv_buffer = self.recv_buffer[processed_size:]
                    # print "should be continue to recv to nextpacket"
                elif processed_size == 0:
                    # print "should be continue to recv to firstpacket"
                    pass
                else:
                    netLogger.error("onReadEvent|%s,proess error", self.session_uuid)
                    self.connect_status = CONNECT_STATUS.CONNECT_SER_WILLCLOSED
                    return False
            except socket.error, msg:
                if msg.errno in ConnectionBase.BUSYING_STATUS:
                    if msg.errno == errno.EINTR:
                        netLogger.warning("onReadEvent|%s,errno.EINTR", self.session_uuid)

                    # 在 非阻塞 socket 上进行 recv 需要处理 读穿 的情况
                    # 这里实际上是利用 读穿 出 异常 的方式跳到这里进行后续处理
                    # print "onReadEvent EAGAIN or EWOULDBLOCK,recvonce_size:{0} max_recvonce_size:{1} canrecvLen:{2}".format(
                    #    recvonce_size, self.max_recvonce_size, canrecvLen)
                    return True
                else:
                    netLogger.critical("onReadEvent|%s,unhandle socket.erro:%s", self.session_uuid, repr(msg))
                    self.connect_status = CONNECT_STATUS.CONNECT_SYS_WILLCLOSED
                    return False
            except:
                self.connect_status = CONNECT_STATUS.CONNECT_SYS_WILLCLOSED
                netLogger.critical("onReadEvent|%s,caught unhandle exception", self.session_uuid)
                info = sys.exc_info()
                for file, lineno, function, text in traceback.extract_tb(info[2]):
                    s1 = "onReadEvent|file:{0} line:{1} in function:{2}".format(file, lineno, function)
                    netLogger.critical(s1)
                    s2 = "onReadEvent|** %s: %s" % info[:2]
                    netLogger.critical(s2)
                return False
        return False

    # 有两种情况触发onWriteEvent事件
    # 1.epoll通知
    # 2.用户send时且is_writtable=True，可能直接触发
    def onWriteEvent(self, is_epoll_trigger=1):
        if is_epoll_trigger == 1:
            if self.is_writtable:
                pass
                # print "onWriteEvent is_epoll_trigger"
            else:
                self.is_writtable = True

        if len(self.send_buffer) == 0:
            return True
        sendLen = 0
        send_count = 0
        while self.connect_status == CONNECT_STATUS.CONNECT_SUCC:
            # 加锁
            with self.send_buffer_lock:
                try:
                    if send_count > 100:
                        return True

                    willsendLen = len(self.send_buffer) - sendLen
                    sendonce_size = self.client_socket.send(self.send_buffer[sendLen:])
                    if sendonce_size > self.max_sendonce_size:
                        self.max_sendonce_size = sendonce_size
                    # a += 1
                    # print "{0} willsendLen:{1} sendonce_size:{2},max_sendonce_size:{3}".format(a, willsendLen,
                    #                                                                            c,
                    #
                    if send_count % 10 == 1:
                        netLogger.debug("onWriteEvent|%s,i:%d,willsendLen:%d,sendoncesize:%d,maxsndsize:%d",
                                        self.session_uuid,
                                        send_count,
                                        willsendLen,
                                        sendonce_size,
                                        self.max_recvonce_size)
                    send_count += 1

                    sendLen += sendonce_size
                    self.send_bytes += sendonce_size
                    # 在全部发送完毕后退出 while 循环
                    if sendLen == len(self.send_buffer):
                        # print "finished write:{0}".format(sendLen)
                        self.send_buffer = ''
                        return True
                except socket.error, msg:
                    self.is_writtable = False
                    if msg.errno in ConnectionBase.BUSYING_STATUS:
                        if msg.errno == errno.EINTR:
                            netLogger.warning("onWriteEvent|%s,errno.EINTR", self.session_uuid)

                        # 在 非阻塞 socket 上进行 recv 需要处理 写穿 的情况
                        # 这里实际上是利用 读穿 出 异常 的方式跳到这里进行后续处理
                        # print "onWriteEvent EAGAIN or EWOULDBLOCK,sendonce_size:{0} max_sendonce_size:{1} willsendLen:{2}".format(
                        #     sendonce_size,
                        #     self.max_sendonce_size,
                        #     willsendLen)
                        self.send_buffer = self.send_buffer[sendLen:]
                        return True
                    else:
                        netLogger.critical("onWriteEvent|%s,unhandle socket.erro:%s", self.session_uuid, repr(msg))
                        self.connect_status = CONNECT_STATUS.CONNECT_SYS_WILLCLOSED
                        return False
                except:
                    self.connect_status = CONNECT_STATUS.CONNECT_SYS_WILLCLOSED
                    netLogger.critical("onWriteEvent|%s,caught unhandle exception", self.session_uuid)
                    info = sys.exc_info()
                    for file, lineno, function, text in traceback.extract_tb(info[2]):
                        s1 = "onWriteEvent|file:{0} line:{1} in function:{2}".format(file, lineno, function)
                        netLogger.critical(s1)
                        s2 = "onWriteEvent|** %s: %s" % info[:2]
                        netLogger.critical(s2)
                    return False
        return True

    # 是否有发送的必要
    def isNeedSend(self):
        if self.connect_status != CONNECT_STATUS.CONNECT_SUCC:
            return False
        if len(self.send_buffer) == 0:
            return False
        return True

    # 这里可以加锁，以适应多线程的send安全性；这里简单实现sendData过程
    # 这里可以做很大的优化
    def sendData(self, data=""):
        if self.connect_status != CONNECT_STATUS.CONNECT_SUCC:
            netLogger.critical("sendData|%s,connect_status:%d", self.session_uuid, self.connect_status)
            return False
        with self.send_buffer_lock:
            if len(self.send_buffer) > self.max_send_buffer_size:
                netLogger.error("sendData|%s,send too big:%d", self.session_uuid, len(self.send_buffer))
                return False
            self.send_buffer += data

        if self.is_writtable:
            self.onWriteEvent(is_epoll_trigger=0)
        else:
            netLogger.error("sendData|%s,will senddata but is not writtable", self.session_uuid)
        return True


        # reason=0  被动关闭 ，出错了
        # reason=1  主动关闭 ，不符合逻辑

    def onDisconnectEvent(self):
        if self.connect_status == CONNECT_STATUS.CONNECT_CLOSED:
            return
        now=gettimesamp()
        uses=now-self.begin_timestamp
        netLogger.warning("onDisconnectEvent|%s,reason:%d,uses:%d", self.session_uuid, self.connect_status,uses)

        # _Connector会用此接口

    def onConnectEvent(self, isOK=True):
        netLogger.info("onConnectEvent|%s,addr:%s", self.session_uuid, self.connect_status, str(self.client_addr))
        if isOK:
            self.connect_status = CONNECT_STATUS.CONNECT_SUCC
        else:
            self.connect_status = CONNECT_STATUS.CONNECT_FAIL

    def onTimerEvent(self, current_time):
        if self.connect_status == CONNECT_STATUS.CONNECT_SUCC:
            if current_time > self.last_recv_time + self.max_keeplive_time:
                netLogger.warning("onTimerEvent|%s,lose live,lastlive:%d,now:%d",
                                  self.session_uuid,
                                  int(self.last_recv_time),
                                  int(current_time))
                self.connect_status = CONNECT_STATUS.CONNECT_LOSELIVE
                return False
        return True

    def close(self):
        netLogger.warning("close|%s,reason:%d", self.session_uuid, self.connect_status)
        self.client_socket.close()
        self.connect_status = CONNECT_STATUS.CONNECT_CLOSED
        self.send_buffer = ''
        self.recv_buffer = ''

    # 处理收到的数据
    def _process_recv_buffer(self):
        return len(self.recv_buffer)


if __name__ == '__main__':
    print CONNECT_TYPE.IS_ACCEPTOR
