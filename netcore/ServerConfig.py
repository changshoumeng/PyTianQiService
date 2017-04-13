#!/usr/bin/env python
# -*- coding: utf-8 -*-
##########################################################
#   Teach Wisedom To Machine.
#   Please Call Me Programming devil.
#   Module Name: ServerConfig
#
#
######################################################## #

import json

imlog_server_config = {}
imlog_server_config["namespace"] = "imlogsvr"
imlog_server_config["module_id"] = 0
imlog_server_config["servers"] = []
imlog_server_config["servers"].append({"host": "192.168.1.167", "port": 8555, "weight": 50, "status": "online"})  # 0

cwzlog_server_config = {}
cwzlog_server_config["namespace"] = "cszlogsvr"
cwzlog_server_config["module_id"] = 0
cwzlog_server_config["servers"] = []
cwzlog_server_config["servers"].append({"host": "192.168.1.167", "port": 9555, "weight": 50, "status": "online"})  # 0
cwzlog_server_config["servers"].append({"host": "192.168.1.167", "port": 9565, "weight": 50, "status": "offline"})  # 1
cwzlog_server_config["servers"].append({"host": "192.168.1.167", "port": 9575, "weight": 50, "status": "offline"})  # 2
cwzlog_server_config["servers"].append({"host": "192.168.1.167", "port": 9585, "weight": 50, "status": "offline"})  # 3

es_server_config = []
es_server_config.append({'host': '192.168.1.161', 'port': 9200})
es_server_config.append({'host': '192.168.1.162', 'port': 9200})
es_server_config.append({'host': '192.168.1.164', 'port': 9200})
es_server_config.append({'host': '192.168.1.165', 'port': 9200})

echo_server_config = {}
echo_server_config["servers"] = []
echo_server_config["servers"].append({'host': '0.0.0.0', 'port': 18098})


def write_imlogsvr_config():
    global imlog_server_config
    with open("../conf/imlogsvr.conf", 'w') as f:
        s = json.dumps(imlog_server_config, sort_keys=True, separators=(',', ':'))
        f.write(s)


def write_cwzlogsvr_config():
    global cwzlog_server_config
    with open("../conf/cwzlogsvr.conf", 'w') as f:
        s = json.dumps(cwzlog_server_config, sort_keys=True, separators=(',', ':'))
        f.write(s)


def update_cwzlogsvr_config(project_index=0, status="online"):
    s = ""
    with open("../conf/cwzlogsvr.conf", 'r') as f:
        s = f.read()
    if not s:
        print "cwzlogsvr.conf empty"
        return
    global cwzlog_server_config
    cwzlog_server_config = json.loads(s)
    cwzlog_server_config["servers"][project_index]["status"] = status
    write_cwzlogsvr_config()


if __name__ == '__main__':
    # write_imlogsvr_config()
    write_cwzlogsvr_config()
    # update_cwzlogsvr_config()
