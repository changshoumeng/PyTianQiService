#!/usr/bin/env python
# -*- coding: utf-8 -*-
##########################################################
#   Teach Wisedom To Machine.
#   Please Call Me Programming devil.
#   Module Name: EpollServer
###################################################### #

from EpollComm import *
from ServiceStatus import *
from Utils import *

logger = logging.getLogger()
statuslogger = logging.getLogger("statusLogger")
netLogger = logging.getLogger("netLogger")

serviceRunningStatus = ServiceRunningStatus()

''' LogAcceptor
'''


############################################################################
class EpollServer(ServerInterface):
    '''epoll-loop-based server
    '''

    # listen_addr_list is list of item as (ip,port)
    def __init__(self, listen_addr_list=[]):
        self._listen_addr_list = listen_addr_list
        self._listen_backlog = 40000
        self._epoll_time_out = 1
        self._timer_time_out = 10
        self._max_session_count = 1024
        pass

    # ServerInterface.start()
    def start(self):
        self._is_started = 0
        self._epoll_loop = EpollLoop()
        self._max_notify_event_count = 0
        self._max_socket_fileno = 0
        self._max_doaccept_count = 0  # 一次accept通知，可以accept的最大次数

        self._listener_dict = {}
        for listen_addr in self._listen_addr_list:
            if not self._createListenSocket(listen_addr):
                return False

        self._acceptor_dict = {}  # <acceptor_id=xxx.fileno(),acceptor=object()>
        self._invalid_acceptorfd_set = set()
        self._session_id = 0
        self._is_started = 1
        self._is_abort_serve_once = 0  # 是否终止serve_once操作
        self._last_timestamp = time.time()        
        return True

    # ServerInterface.stop()
    def stop(self):
        if self._is_started == 0:
            return
        self._is_started = 0
        self._epoll_loop.close()
        for listen_socket in self._listener_dict.values():
            listen_socket.close()
        self._listener_dict.clear()
        for acceptor in self._acceptor_dict.values():
            acceptor.close()
        self._is_abort_serve_once = 1
        pass

    # ServerInterface.serve_once()
    def serve_once(self):
        """ Pool the ready event """
        # epoll 进行 fd 扫描的地方 -- 未指定超时时间则为阻塞等待
        if self._is_abort_serve_once == 1:
            netLogger.warning("serve_once _is_abort_serve_once=1 ")
            return False
        now_timestamp = time.time()
        if now_timestamp > self._last_timestamp + self._timer_time_out:
            self._last_timestamp = now_timestamp
            self._triggerTimerEvent()

        epoll_list = self._epoll_loop.poll(self._epoll_time_out)
        for fileno, events in epoll_list:
            # print_epoll_events(fileno,events)
            # 若为监听 fd 被激活
            if fileno in self._listener_dict:
                self._onFdAcceptable(listen_fd=fileno)
                continue
            acceptor = self._acceptor_dict.get(fileno, None)
            if acceptor is None:
                t = "cannot find fd:{0} from _acceptor_dict".format(fileno)
                netLogger.warning(t)
                continue
            if acceptor.isConnectSucc():
                self._checkSocketDataEvent(fileno, events)
                pass
            pass

        if len(epoll_list) > 0:
            if len(epoll_list) > self._max_notify_event_count:
                self._max_notify_event_count = len(epoll_list)
                # self._reportStatus()

        # 可以延时处理失效的acceptor
        self._checkInvalidAcceptors()
        return True
     #
    def getAcceptor(self,acceptor_fd=0,acceptor_sessionid=0):
        if acceptor_fd not in self._acceptor_dict:
            netLogger.debug("getAcceptor NULL;fd:%d sessionid:%d",acceptor_fd,acceptor_sessionid)
            return None
        acceptor =  self._acceptor_dict[acceptor_fd]
        if acceptor.client_session_id != acceptor_sessionid:
            netLogger.debug("getAcceptor failed;fd:%d sessionid:%d>currentsessionid:%d", acceptor_fd, acceptor_sessionid,acceptor.client_session_id)
            return None
        return acceptor

    # Public Virtual Method
    def onTcpConnectionEnter(self, session_id, client_socket, client_address):
        raise NotImplementedError()
        # acceptor = _Acceptor(session_id, client_socket, client_address)
        # return acceptor
    # Public Virtual Method
    def onProcessTimerTask(self):
        raise NotImplementedError()
    # Public Virtual Method
    def task_once(self):
        raise NotImplementedError()
    # Public Virtual Method
    def feedback_once(self):
        raise NotImplementedError()


    def _reportStatus(self):
        acceptors = self._acceptor_dict.values()
        accept_succ_count = reduce(lambda x, y: x + y.get_intval(), acceptors, 0)

        if accept_succ_count > 2:
            t = "reportStatus>>  acceptors:{0} accept_succ_count:{1} max_events:{2},maxfileno:{3}".format(
                len(self._acceptor_dict),
                accept_succ_count,
                self._max_notify_event_count,
                self._max_socket_fileno)
            statuslogger.debug(t)

    def _assignSessionId(self):
        self._session_id += 1
        return self._session_id

    def _pushInvalidFd(self, client_fd):
        self._invalid_acceptorfd_set.add(client_fd)

    # 定时事件触发器
    def _triggerTimerEvent(self):
        for fileno, acceptor in self._acceptor_dict.items():
            if not acceptor.onTimerEvent(self._last_timestamp):
                self._pushInvalidFd(fileno)
        self.onProcessTimerTask()
        self._reportStatus()
        global serviceRunningStatus
        serviceRunningStatus.report()
        pass

    # 创建listen socket,并且注册到epoll,关注EPOLLIN
    def _createListenSocket(self, listen_addr=()):
        try:
            listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listen_socket.setblocking(False)
            listen_socket.bind(listen_addr)
            listen_socket.listen(self._listen_backlog)
            self._listener_dict[listen_socket.fileno()] = listen_socket
            self._epoll_loop.register(listen_socket.fileno(), select.EPOLLIN)
            t = "_createListenSocket ok addr:{0} pid:{1}".format(listen_addr, os.getpid())
            netLogger.info(t)
            return True
        except socket.error, e:
            t = "_createListenSocket,error,addr:{0} pid:{1} msg:{2}".format(listen_addr, os.getpid(), repr(e))
            netLogger.critical(t)
            sys.exit(1)
        return False

    def _checkSocketDataEvent(self, fileno, events):

        # 异常事件
        if events & (select.EPOLLHUP | select.EPOLLERR):
            self._onFdExceptional(client_fd=fileno)
            print_epoll_events(fileno, events)
            return

        # 合法事件
        if events & select.EPOLLIN:
            # <连接到达；有数据来临；>有 可读 事件激活
            self._onFdReadable(client_fd=fileno)
            return
        if events & select.EPOLLPRI:
            # <   外带数据>
            netLogger.warning("_checkSocketEvent EPOLLPRI")
            self._onFdReadable(client_fd=fileno)
            return
        if events & select.EPOLLOUT:
            # <有数据要写>有 可写 事件激活
            self._onFdWritable(client_fd=fileno)
            return

        # 没有预期的事件
        # EPOLLERR 是服务器这边出错
        # 对端正常关闭（程序里close()，shell下kill或ctr+c），触发EPOLLIN和EPOLLRDHUP，但是不触发EPOLLERR和EPOLLHUP
        # 关于这点，以前一直以为会触发EPOLLERR或者EPOLLHUP。
        # man epoll_ctl看下后两个事件的说明，这两个应该是本端（server端）出错才触发的。
        # 对端异常断开连接（只测了拔网线），没触发任何事件。
        t = "_checkSocketDataEvent <unhandle_event fileno:{0} events:{1}> ".format(fileno, events)
        netLogger.critical(t)
        pass

    # Accept就绪
    def _onFdAcceptable(self, listen_fd):
        # 进行 accept -- 获得连接上来 client 的 ip 和 port，以及 socket 句柄
        listen_socket = self._listener_dict[listen_fd]
        accept_count = 0
        while True:
            try:
                client_socket, client_address = listen_socket.accept()
                if len(self._acceptor_dict) > self._max_session_count:
                    t = "_onFdAcceptable Failed;Too Many Sessions;Then Close It"
                    netLogger.critical(t)
                    client_socket.close()
                    return False

                session_id = self._assignSessionId()
                # print "accept fd:{0} sessionId:{1}".format(client_socket.fileno(),session_id )
                # logger.debug("accept connection from %s, %d, fd = %d" % (addr[0], addr[1], conn.fileno()))
                # 将连接 socket 设置为 非阻塞
                client_socket.setblocking(0)
                acceptor = self.onTcpConnectionEnter(session_id, client_socket, client_address)
                self._max_socket_fileno = client_socket.fileno()
                self._addTcpAcceptor(acceptor.client_socket.fileno(), acceptor)
                accept_count += 1
            except socket.error, e:
                if e.errno == errno.EAGAIN or e.errno == errno.EWOULDBLOCK:
                    # 在 非阻塞 socket 上进行 recv 需要处理 读穿 的情况
                    # 这里实际上是利用 读穿 出 异常 的方式跳到这里进行后续处理
                    # print "_onFdAcceptable EAGAIN or EWOULDBLOCK,acceptor_count:{0}".format(acceptor_count)
                    if accept_count > self._max_doaccept_count:
                        self._max_doaccept_count = accept_count
                    return True
                else:
                    t = "_onFdAcceptable unhandle socket.error:{0}".format(repr(e))
                    netLogger.critical(t)
                return False

    # Read就绪
    def _onFdReadable(self, client_fd):
        # print "_onFdReadable fd:{0}".format(client_fd)
        acceptor = self._acceptor_dict.get(client_fd, None)
        if acceptor is None:
            netLogger.critical("_onFdReadable failed,NULL,client_fd:%d", client_fd)
            return
        if acceptor.onReadEvent():
            pass
            # if acceptor.isNeedSend():
            #     # 更新 epoll 句柄中连接d 注册事件为 可写
            #     #self._epoll_loop.modify(client_fd, select.EPOLLET|select.EPOLLOUT )
            #     #print "_onFdReadable modify to epoll_out"
            # else:
            #     print "_onFdReadable not modify"
            #     pass
        else:
            # 出错
            self._pushInvalidFd(client_fd)
            if not acceptor.isClosedByClient():
                t = "_onFdReadable error,client_fd:{0}".format(client_fd)
                netLogger.critical(t)

    # Write就绪
    def _onFdWritable(self, client_fd):
        # print "_onFdWritable fd:{0}".format(client_fd)
        acceptor = self._acceptor_dict.get(client_fd, None)
        if acceptor is None:
            netLogger.critical("_onFdWritable failed,client_fd:%d", client_fd)
            return
        if acceptor.onWriteEvent():
            # 更新 epoll 句柄中连接 fd 注册事件为 可读
            # self._epoll_loop.modify(client_fd, select.EPOLLET | select.EPOLLIN)
            pass
        else:
            # 出错
            self._pushInvalidFd(client_fd)
            t = "_onFdWritable error,client_fd:{0}".format(client_fd)
            netLogger.critical(t)

    # Exception通知
    def _onFdExceptional(self, client_fd):
        acceptor = self._acceptor_dict.get(client_fd, None)
        if acceptor is None:
            netLogger.critical("_onFdExceptional failed,client_fd:%d", client_fd)
            return
        # 出错
        t = "_onFdExceptional client_fd:{0}".format(client_fd)
        netLogger.critical(t)
        self._pushInvalidFd(client_fd)
        pass

    # 检查失效的acceptors
    def _checkInvalidAcceptors(self):
        if not self._invalid_acceptorfd_set:
            return
        for client_fd in self._invalid_acceptorfd_set:
            acceptor = self._acceptor_dict.get(client_fd, None)
            if acceptor is None:
                continue
            self._delTcpAcceptor(client_fd, acceptor)
            acceptor.onDisconnectEvent()
            acceptor.close()

        self._invalid_acceptorfd_set.clear()

    def _addTcpAcceptor(self, acceptor_fd, acceptor):
        # 向 epoll 句柄中注册 连接 socket 的 可读 事件
        self._epoll_loop.register(acceptor_fd, select.EPOLLET | select.EPOLLOUT | select.EPOLLIN)
        self._acceptor_dict[acceptor_fd] = acceptor

        t = "_addTcpAcceptor sessionId:{0} fd:{1} addr:{2} conns:{3}".format(
            acceptor.client_session_id,
            acceptor_fd,
            acceptor.client_addr,
            len(self._acceptor_dict))
        netLogger.debug(t)

    def _delTcpAcceptor(self, acceptor_fd, acceptor):
        if acceptor_fd in self._acceptor_dict:
            self._epoll_loop.unregister(acceptor_fd)
            del self._acceptor_dict[acceptor_fd]
            t = "_delTcpAcceptor sessionId:{0} fd:{1} addr:{2} conns:{3}".format(
                acceptor.client_session_id,
                acceptor_fd,
                acceptor.client_addr,
                len(self._acceptor_dict))
            netLogger.debug(t)
            return
        t = "_delTcpAcceptor nothing"
        netLogger.warning(t)





############################################################################
class _Acceptor(ConnectionBase):
    def __init__(self, client_session_id=-1, client_socket=None, client_addr=()):
        super(_Acceptor, self).__init__(client_session_id, client_socket, client_addr)
        self.connection_type = CONNECT_TYPE.IS_ACCEPTOR
        self.connect_status = CONNECT_STATUS.CONNECT_SUCC
        self.max_send_buffer_size = 1024 * 1024 * 10
        self.max_recv_buffer_size = 1024 * 1024 * 10
        self.max_keeplive_time = 600000000000
        self.send_count = 0

    def onDisconnectEvent(self):
        if self.connect_status == CONNECT_STATUS.CONNECT_CLOSED:
            return
        print "_Acceptor::onDisconnectEvent fd:{0} reason:{1}".format(self.client_socket.fileno(), self.connect_status)

    def onTimerEvent(self, current_time):
        # if not super(_Acceptor,self).onTimerEvent(current_time):
        #     return False
        #
        # tm = time.time()
        # data = '2'*1024*60 +"2"* 1024 * self.send_count
        # self.send_count += 1
        # self.sendData(data)
        # print tm,"sendbytes:{0} recvbytes:{1}".format(self.send_bytes,self.recv_bytes)
        return True

    # 处理收到的数据
    def _process_recv_buffer(self):
        pid = str(os.getpid())
        # print '_Acceptor_{0}-recv:'.format(pid)
        # self.sendData(pid + "say:" + self.recv_buffer)
        return len(self.recv_buffer)


if __name__ == '__main__':
    listen_addr_list = [("0.0.0.0", 1234)]
    serv = EpollServer(listen_addr_list)
    InterruptableTaskLoop(serv, 0).startAsForver()
