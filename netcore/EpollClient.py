#!/usr/bin/env python
# -*- coding: utf-8 -*-
##########################################################
#   Teach Wisedom To Machine.
#   Please Call Me Programming devil.
#   Module Name: EpollClient
######################################################## #

from EpollComm import *

socket.setdefaulttimeout(4)


############################################################################
class EpollClient(ServerInterface):
    '''epoll-loop-based client
    '''
    test_data = None

    def __init__(self, connect_addr, connection_pool_size=1, echo_text='hello'):
        self._connect_addr = connect_addr
        self._connection_pool_size = connection_pool_size
        self._epoll_time_out = 1
        self._timer_time_out = 5
        self._is_auto_reconnect = True
        self._echo_text = echo_text
        pass

    # ServerInterface.start()
    def start(self):
        self._is_started = 0
        self._epoll_loop = EpollLoop()
        self._max_notify_event_count = 0
        self._max_socket_fileno = 0
        self._last_socket_fileno = 0

        self._invalid_connectorfd_set = set()
        self._pending_connector_dict = {}
        self._connector_dict = {}
        self._connct_time_list = []
        self._is_connectable = True
        for i in xrange(self._connection_pool_size):
            connector = self.onTcpConnectionCreate(i + 1, None, self._connect_addr)
            self._addPendingConnector(connector)

        self._is_started = 1
        self._is_abort_serve_once = 0  # 是否终止serve_once操作
        self._last_timestamp = 0
        self._start_timestamp = time.time()
        time.sleep(3)
        return True

    # public virtual method
    # How to Create Connection to process tcpdata with remote server
    def onTcpConnectionCreate(self, sessionid=0, client_socket=None, connect_addr=()):
        # return _Connector(sessionid, client_socket, connect_addr)
        raise NotImplementedError()

    # ServerInterface.stop()
    def stop(self):
        print "ServerInterface.stop()"
        if self._is_started == 0:
            return
        self._is_started = 0
        self._is_abort_serve_once = 1
        self._epoll_loop.close()
        self._invalid_connectorfd_set.clear()
        for connector in self._connector_dict.values():
            connector.close()
        pass

    # ServerInterface.serve_once()
    def serve_once(self):
        """ Pool the ready event """
        # epoll 进行 fd 扫描的地方 -- 未指定超时时间则为阻塞等待
        if self._is_abort_serve_once == 1:
            return False

        now_timestamp = time.time()
        if now_timestamp > self._last_timestamp + self._timer_time_out:
            self._last_timestamp = now_timestamp
            self._triggerTimerEvent()

        epoll_list = self._epoll_loop.poll(self._epoll_time_out)

        for fileno, events in epoll_list:
            # print_epoll_events(fileno, events)
            if fileno not in self._connector_dict:
                print "serve_once failed: fileno:{0} is not ini dict".format(fileno)
                continue
            connector = self._connector_dict[fileno]
            if connector.isConnecting():
                if self._checkSocketConnEvent(fileno, events):
                    self._delPendingConnector(connector.client_session_id)
                    connector.onConnectEvent(True)
                    self._connct_time_list.append(gettickcount() - gettickcount2(connector.next_connect_time))
                else:
                    connector.onConnectEvent(False)
                    self._pushInvalidFd(fileno)

            elif connector.isConnectSucc():
                self._checkSocketDataEvent(fileno, events)

        if len(epoll_list) > 0:
            if len(epoll_list) > self._max_notify_event_count:
                self._max_notify_event_count = len(epoll_list)
                # self._reportStatus()

        self._checkInvalidFds()
        return True

    # ServerInterface.notify()
    def notify(self, message):
        print "notify:", message

    # 定时事件触发器
    def _triggerTimerEvent(self):
        for fileno, connector in self._connector_dict.items():
            if not connector.onTimerEvent(self._last_timestamp):
                self._pushInvalidFd(fileno)

        # print "_triggerTimerEvent"
        connect_count = 0

        t1 = gettickcount()
        for connector in self._pending_connector_dict.values():
            if not connector.isReadyNextConnect():
                # print "isReadyNextConnect,not"
                continue

            self._buildConnection(connector)
            connect_count += 1
            if connect_count > 10000:
                pass
                break
            pass
        # self._reportStatus()
        pass

    def _reportStatus(self):
        connectors = self._connector_dict.values()
        conn_succ_count = reduce(lambda x, y: x + y.get_intval(), connectors, 0)

        print ">>reportStatus>> pendings:{0} conns1:{1} conn_succ_count:{2} max_events:{3},maxfileno:{4} lastfileno:{5}".format(
            len(self._pending_connector_dict),
            len(self._connector_dict),
            conn_succ_count,
            self._max_notify_event_count,
            self._max_socket_fileno,
            self._last_socket_fileno)

        if len(self._connct_time_list) >= self._connection_pool_size:
            t = gettickcount() - gettickcount2(self._start_timestamp)
            print "Finish All Connect", len(self._connct_time_list), t
            self._connct_time_list.sort()
            print "ConnMinTime:{0} ConnMaxTime:{1} ConnAvergeTime:{2} ConnTotalTime:{3} ConnCount:{4}".format(
                self._connct_time_list[0],
                self._connct_time_list[-1],
                sum(self._connct_time_list) / len(self._connct_time_list),
                t,
                len(self._connct_time_list)
            )

    def _checkSocketConnEvent(self, fileno, events):
        # 异常事件
        if events & (select.EPOLLHUP | select.EPOLLERR):
            return False
        # 连接事件
        if events & select.EPOLLOUT:
            # print "_checkSocketConnEvent,Call Connect(),then connect OK"
            return True
        return False

    def _checkSocketDataEvent(self, fileno, events):
        # 异常事件
        if events & (select.EPOLLHUP | select.EPOLLERR):
            self._onFdExceptional(client_fd=fileno)
            return

        # 合法事件
        if events & select.EPOLLIN:
            # <连接到达；有数据来临；>有 可读 事件激活
            self._onFdReadable(client_fd=fileno)
            return
        if events & select.EPOLLPRI:
            # <   外带数据>
            print "_checkSocketEvent EPOLLPRI"
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
        print "_checkSocketDataEvent <unhandle_event fileno:{0} events:{1}> ".format(fileno, events)
        pass

    def _pushInvalidFd(self, client_fd):
        self._invalid_connectorfd_set.add(client_fd)

    def _addPendingConnector(self, connector):
        connector.prepareNextConnect()
        connector_id = connector.client_session_id
        if connector_id not in self._pending_connector_dict:
            print "_addPendingConnector connector_id:{0}".format(connector_id)
            self._pending_connector_dict[connector_id] = connector

    def _delPendingConnector(self, connector_id):
        if connector_id in self._pending_connector_dict:
            # print "_delPendingConnector connector_id:{0}".format(connector_id)
            del self._pending_connector_dict[connector_id]

    def _buildConnection(self, connector, is_block_connect=False):
        if not self._is_connectable:
            connector.prepareNextConnect()
            InterruptableTaskLoop.wait(5)
            return False

        connector.resetConnectStatus()
        connect_addr = connector.client_addr
        # t1 = gettickcount()
        try:
            connect_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            connector.client_socket = connect_socket
            self._last_socket_fileno = connect_socket.fileno()
            if self._last_socket_fileno > self._max_socket_fileno:
                self._max_socket_fileno = self._last_socket_fileno
            if not is_block_connect:
                connect_socket.setblocking(False)
                self._addTcpConnector(connect_socket.fileno(), connector)
                connect_socket.connect(connect_addr)
            else:
                connect_socket.connect(connect_addr)
                connect_socket.setblocking(False)
                self._addTcpConnector(connect_socket.fileno(), connector)
            connector.onConnectEvent(isOK=True)
            self._delPendingConnector(connector.client_session_id)
            # t2 = gettickcount() -t1
            self._connct_time_list.append(gettickcount() - gettickcount2(connector.next_connect_time))
            print "_buildConnection ok addr:{0} id:{1}".format(connect_addr, connector.client_session_id)
            return True
        except socket.error, msg:
            if msg.errno in (errno.EAGAIN, errno.EWOULDBLOCK, errno.EINPROGRESS):
                # print "_buildConnection doing addr:{0} id:{1}".format(connect_addr, connector.client_session_id)
                return True
            else:
                connector.onConnectEvent(isOK=False)
                print "_buildConnection caught socketeror addr:{0} id:{1} msg:{2}".format(connect_addr,
                                                                                          connector.client_session_id,
                                                                                          msg)
                self._is_connectable = False
                print "9" * 80
        return False

    # Read就绪
    def _onFdReadable(self, client_fd):
        print "_onFdReadable fd:{0}".format(client_fd)
        connector = self._connector_dict.get(client_fd, None)
        if connector is None:
            print "_onFdRead failed"
            return
        if connector.onReadEvent():
            pass
            # if connector.isNeedSend():
            #     # 更新 epoll 句柄中连接d 注册事件为 可写
            #     #self._epoll_loop.modify(client_fd, select.EPOLLET | select.EPOLLOUT | select.EPOLLHUP)
            #     #print "_onFdReadable modify to epoll_out"
            #     pass
            # else:
            #     # print "_onFdReadable not modify"
            #     pass
        else:
            # 出错
            self._pushInvalidFd(client_fd)
            print "_onFdReadable error,client_fd:{0}".format(client_fd)

    # Write就绪
    def _onFdWritable(self, client_fd):
        # print "_onFdWritable fd:{0}".format(client_fd)
        connector = self._connector_dict.get(client_fd, None)
        if connector is None:
            print "_onFdWrite failed,"
            return
        if connector.onWriteEvent():
            # 更新 epoll 句柄中连接 fd 注册事件为 可读
            # self._epoll_loop.modify(client_fd, select.EPOLLET | select.EPOLLIN)
            pass
        else:
            # 出错
            self._pushInvalidFd(client_fd)
            print "_onFdWritable error,client_fd:{0}".format(client_fd)

    # Exception通知
    def _onFdExceptional(self, client_fd):
        connector = self._connector_dict.get(client_fd, None)
        if connector is None:
            print "_onFdExceptional failed,"
            return
        # 出错
        print "_onFdExceptional client_fd:{0}".format(client_fd)
        self._pushInvalidFd(client_fd)
        pass

    # 检查失效的fd
    def _checkInvalidFds(self):
        if not self._invalid_connectorfd_set:
            return
        for client_fd in self._invalid_connectorfd_set:
            connector = self._connector_dict.get(client_fd, None)
            if connector is None:
                continue
            self._delTcpConnector(client_fd, connector)
            if self._is_auto_reconnect:
                self._addPendingConnector(connector)

            if not connector.isConnectFailed():
                connector.onDisconnectEvent()
            connector.close()
        self._invalid_connectorfd_set.clear()

    def _addTcpConnector(self, connector_fd, connector):
        # 向 epoll 句柄中注册 连接 socket 的 可读 事件
        self._epoll_loop.register(connector_fd, select.EPOLLET | select.EPOLLOUT | select.EPOLLIN)  # | select.EPOLLHUP
        self._connector_dict[connector_fd] = connector
        # print "_addTcpConnector sessionId:{0} fd:{1} addr:{2} conns:{3}".format(
        #     connector.client_session_id,
        #     connector_fd,
        #     connector.client_addr,
        #     len(self._connector_dict))

    def _delTcpConnector(self, connector_fd, connector):
        if connector_fd in self._connector_dict:
            self._epoll_loop.unregister(connector_fd)
            del self._connector_dict[connector_fd]
            # print "_delTcpConnector sessionId:{0} fd:{1} addr:{2} conns:{3}".format(
            #     connector.client_session_id,
            #     connector_fd,
            #     connector.client_addr,
            #     len(self._connector_dict))
            return
        print "_delTcpConnector nothing"


############################################################################
class _Connector(ConnectionBase):
    def __init__(self, client_session_id=-1, client_socket=None, client_addr=()):
        super(_Connector, self).__init__(client_session_id, client_socket, client_addr)
        self.connection_type = CONNECT_TYPE.IS_CONNECTOR
        self.connect_status = CONNECT_STATUS.CONNECT_CLI_WILLCONNECT
        self.max_send_buffer_size = 16 * 1024
        self.max_recv_buffer_size = 1024
        self.max_keeplive_time = 600000000000
        self.has_send_size = 0
        self.has_recv_size = 0
        self.next_connect_time = 0  # 下次执行conenct的时间，为0，表示不需要执行
        # print self.client_session_id

    def prepareNextConnect(self):
        self.next_connect_time = time.time() + 6000

    def isReadyNextConnect(self):
        if self.isConnectSucc():
            return False
        if self.connect_status == CONNECT_STATUS.CONNECT_CLI_WILLCONNECT or time.time() > self.next_connect_time:
            return True
        return False

    # 重置连接状态
    def resetConnectStatus(self):
        self.connect_status = CONNECT_STATUS.CONNECT_DOING
        self.next_connect_time = time.time()
        pass

    def isConnectFailed(self):
        return self.connect_status == CONNECT_STATUS.CONNECT_FAIL

    def onConnectEvent(self, isOK=True):
        if self.client_session_id < 10000:
            pass
        else:
            print "_Connector::onConnectEvent({0}) addr:{1} sessionId:{2} ".format(isOK, self.client_addr,
                                                                                   self.client_session_id)
        if isOK:
            self.connect_status = CONNECT_STATUS.CONNECT_SUCC
            self.sendData(EpollClient.test_data)
        else:
            self.connect_status = CONNECT_STATUS.CONNECT_FAIL
            print "FAIL" * 15

    # reason=0  被动关闭 ，出错了
    # reason=1  主动关闭 ，不符合逻辑
    def onDisconnectEvent(self):
        if self.connect_status == CONNECT_STATUS.CONNECT_CLOSED:
            return
        print "_Connector::onDisconnectEvent fd:{0} reason:{1}".format(self.client_socket.fileno(), self.connect_status)
        print "4" * 20

    def onTimerEvent(self, current_time):
        # print "onTimer:",current_time - self.last_recv_time
        # if  current_time  > self.last_recv_time + 10:
        #     print "onTimerEvent"*4
        #     #self.onReadEvent()
        #     self.sendData("1")
        #     return True
        # if 1==1:
        #     return True
        # if  not  super(_Connector, self).onTimerEvent(current_time):
        #     return False
        return True

    def _process_recv_buffer(self):
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
        else:
            print "process all:", has_unpack_bufsize, total_bufsize
        return has_unpack_bufsize

    # how to unpack a packet from buffer
    def _unpack_frombuffer(self, buffer=""):
        raise NotImplementedError()
        return (0, None)

    # packet_data is full packet
    def _dispatch_packet(self, head=None, packet_data=""):
        print ">>_dispatch_packet"
        raise NotImplementedError()


if __name__ == '__main__':
    print "BEGIN"
    cli = EpollClient(connect_addr=("10.10.2.220", 1234), connection_pool_size=1000, echo_text='1' * 20)
    InterruptableTaskLoop(cli, 0.0).startAsForver()
    print "END"
