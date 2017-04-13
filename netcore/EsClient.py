import logging
import os
import time

from elasticsearch import ConnectionTimeout
from elasticsearch import Elasticsearch
from elasticsearch import helpers

from ServerConfig import es_server_config

logger = logging.getLogger()

INDEX_NAME = 'im_tcpgate'
DOC_TYPE = 'user_request'
'''
http://www.cnblogs.com/cswuyg/p/5651620.html
https://github.com/lufeng4828/sense
http://www.tuicool.com/articles/URFJVj
'''


def getYMD():
    return time.strftime("%Y%m%d", time.localtime(time.time()))


def _create_index(es=None, index_name="cswuyg", doc_type_name="cswuyg", properties={}):
    my_settingss = {
        'number_of_shards': 5,
        'number_of_replicas': 1
    }
    my_mappings = {
        doc_type_name: {
            '_all': {
                'enabled': 'false'
            },
            "properties": properties
        }
    }
    settings = {
        'settings': my_settingss,
        'mappings': my_mappings
    }
    create_index = es.indices.create(index=index_name, body=settings, ignore=400, timeout="300s")
    print "_create_index:", index_name
    print "settings:", settings
    print "create result:", create_index


class EsIndexer(object):
    def __init__(self, index_name="my_index_name", doc_type_name="my_doc_type_name", properties={}):
        self._index_name = index_name
        self._doc_type_name = doc_type_name
        self._properties = properties
        self._index_name_2 = self.get_index_name()
        self._es_actions = []
        self._es_bulksize = 2000
        self._es_count = 0
        self._es_uuid = ""
        self._es = None
        pass

    def get_index_name(self):
        return self._index_name + "_" + getYMD()

    def get_mapping(self):
        # return self._es.indices.get_mapping()
        print "get_mapping:", self._index_name_2, self._doc_type_name
        return self._es.indices.get_mapping(index=self._index_name_2, doc_type=self._doc_type_name)

    def _wrapper_action(self, s):
        new_action = {}
        new_action['_index'] = self._index_name_2
        new_action['_type'] = self._doc_type_name
        new_action['_id'] = time.strftime('%H%M%S') + str(s["logId"])
        new_action["_source"] = s
        return new_action

    def delete_index(self):
        self.check_es()
        print "will delete index:", self._index_name_2
        self._es.indices.delete(index=self._index_name_2)
        print "done"

    def check_es(self):
        if self._es:
            if self._es_count % 1000 == 0:
                new_index_name = self.get_index_name()
                if new_index_name != self._index_name_2:
                    _create_index(self._es, index_name=new_index_name, doc_type_name=self._doc_type_name,
                                  properties=self._properties)
                    self._index_name_2 = new_index_name
                    logger.warning("es|%s change to index,%s", self._es_uuid, new_index_name)
            return self._es
        try:
            es = Elasticsearch(es_server_config, timeout=60, sniff_on_start=True, sniff_on_connection_fail=True,
                               max_retries=3, retry_on_timeout=True)
            _create_index(es, index_name=self._index_name_2, doc_type_name=self._doc_type_name,
                          properties=self._properties)
            self._es_uuid = "{0}_{1}".format(os.getpid(), self._index_name)
            logger.warning("es|%s new instance to %s", self._es_uuid, str(es_server_config))
            self._es = es
            return es
        except Exception, e:
            logger.critical("es|%s new instance failed to %s,exception:%s",
                            self._es_uuid,
                            str(es_server_config),
                            repr(e))
        return None

    def index(self, s={}):
        t1 = int(time.time() * 1000)
        t2 = 0
        bulk_ok = False
        try:
            self._es_count += 1
            if not self.check_es():
                return False
            self._es_actions.append(self._wrapper_action(s))
            if len(self._es_actions) < self._es_bulksize:
                return True
            bulk_retry_count = 0
            while True:
                try:
                    success, errors = helpers.bulk(self._es, self._es_actions, raise_on_error=False,
                                                   request_timeout=300)
                    # self._es.indices.refresh()
                    t2 = int(time.time() * 1000)
                    bulk_ok = True
                    if errors:
                        logger.error("es|%s,cnt:%d,succ:%d,error:%s", self._es_uuid, self._es_count, success,
                                     repr(errors))
                    self._es_actions = []
                    return True
                except ConnectionTimeout:
                    logger.error("ConnectionTimeout try again;%d", bulk_retry_count)
                    bulk_retry_count += 1
                    if bulk_retry_count > 5:
                        self._es_actions = []
                        return Flase

            return True
        except Exception, e:
            logger.critical("es|%s index failed,exception:%s", self._es_uuid, repr(e))
            self._es = None
            return False
            pass
        finally:
            if len(self._es_actions) >= self._es_bulksize:
                if not bulk_ok:
                    logger.warning("es|%s bulk faild,%s", self._es_uuid, str(self._es_actions))
                else:
                    use_time = t2 - t1
                    if use_time > 200:
                        logger.warning("es|%s bulk ok[%d-%d]",
                                       self._es_uuid,
                                       use_time,
                                       len(self._es_actions)
                                       )
                        # self._es_actions = []


def es_add_index(e, s):
    if not e.index(s):
        e.index(s)
