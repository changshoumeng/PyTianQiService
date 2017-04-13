# !/usr/bin/env python
# -*- coding: utf-8 -*-
##########################################################
#   Teach Wisedom To Machine.
#   Please Call Me Programming devil.
#   Module Name: ServiceStatus
######################################################## #
import logging

from .Utils import *
from MsgPipe import *
statuslogger = logging.getLogger("statusLogger")


class ServiceRunningStatus(object):
    def __init__(self):
        self.last_ymd_tick = get_ymd_tick()
        statuslogger.debug(">>>>>>>>> %d <<<<<<<<<<", self.last_ymd_tick)
        self.reset()

    def recv(self, recv_size):
        if self.recv_packet_begin == 0:
            self.recv_packet_begin = gettickcount()
        self.recv_packet_bytes += recv_size
        self.recv_packet_count += 1
        return self.recv_packet_count

    def send(self, send_size):
        if self.send_packet_begin == 0:
            self.send_packet_begin = gettickcount()
        self.send_packet_bytes += send_size
        self.send_packet_count += 1
        return self.send_packet_count

    def reset(self):
        self.recv_packet_begin = 0
        self.recv_packet_end = 0
        self.recv_packet_count = 0
        self.recv_packet_bytes = 0
        self.send_packet_begin = 0
        self.send_packet_end = 0
        self.send_packet_count = 0
        self.send_packet_bytes = 0

    def report(self):        
        nowtick = gettickcount()
        sendtick = nowtick - self.send_packet_begin
        recvtick = nowtick - self.recv_packet_begin
        send_byte_speed = 0
        send_count_speed = 0
        recv_byte_speed = 0
        recv_count_speed = 0
        if self.send_packet_begin > 0 and sendtick > 0:
            send_byte_speed = normalizeNetIO(self.send_packet_bytes, sendtick)
            send_count_speed = float(self.send_packet_count * 1000) / float(sendtick)
        if self.recv_packet_begin > 0 and recvtick > 0:
            recv_byte_speed = normalizeNetIO(self.recv_packet_bytes, recvtick)
            recv_count_speed = float(self.recv_packet_count * 1000) / float(recvtick)
        t = "sbs:{0} scs:{1:0.1f} sxx:{2}|rbs:{3} rcs:{4:0.1f} rxx:{5}|c:{6} f:{7}".format(
            send_byte_speed,
            send_count_speed,
            self.send_packet_count,
            recv_byte_speed,
            recv_count_speed,
            self.recv_packet_count,
 	    MsgPipe.size(),
            FeedbackPipe.size()	
	    )
        statuslogger.info(t)
        current_ymd_tick = get_ymd_tick()
        if current_ymd_tick > self.last_ymd_tick:
            self.reset()
            self.last_ymd_tick = current_ymd_tick
            statuslogger.debug("change to:%d<<<<<<<<<<", self.last_ymd_tick)
