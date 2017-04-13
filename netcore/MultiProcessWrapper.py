# -*- coding: utf-8 -*-
# !/usr/bin/env python
#############################################################
# teaching wisedom to my machine,please call me Croco#
#############################################################
# graceful_exit_event.py
#   UTF-8 without BOM
#
# refer:
#   http://stackoverflow.com/questions/26414704/how-does-a-python-process-exit-gracefully-after-receiving-sigterm-while-waiting?rq=1
#   http://www.cnblogs.com/kaituorensheng/p/4445418.html
# init created: 2016-07-13
# last updated: 2016-07-14
#
#######################################################################
import logging
import multiprocessing
import multiprocessing as mp
import os
import signal
import sys
import time
import traceback
from abc import ABCMeta, abstractmethod

managerLogger = logging.getLogger("managerLogger")

mp_message_queue = mp.JoinableQueue()
mp_feedback_queue=mp.JoinableQueue()


###################################################
#   TimerInterface
#     定义了一个Timer必备的功能接口
###################################################
class TimerInterface(object):
    __metaclass__ = ABCMeta

    # return v,then the value is set as time.sleep(v)
    @abstractmethod
    def timeout(self):
        pass

    # trigger a onTimerEvent,when time.sleep(v) once
    @abstractmethod
    def onTimer(self):
        pass


###################################################
#   SimpleTimer
#
###################################################
class SimpleTimer(TimerInterface):
    def __init__(self):
        pass

    def timeout(self):
        return 1

    def onTimer(self):
        pass


###################################################
#   WorkerInterface
#     定义了一个worker必备的功能接口
###################################################
class WorkerInterface(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def onStart(self,gracefulexit_event):
        pass

    @abstractmethod
    def onEnd(self, end_code, end_reason):
        pass

    @abstractmethod
    def onRunOnce(self):
        pass

    @abstractmethod
    def onTimer(self):
        pass

    @abstractmethod
    def finished(self):
        pass

    @abstractmethod
    def timeout_ms(self):
        pass

    @abstractmethod
    def log(self, txt):
        pass

    @abstractmethod
    def daemon(self):
        pass


###################################################
#   SimpleWorker
#     基于WorkerInterface实现一个简单的worker，
#     提供使用示例
###################################################
class SimpleWorker(WorkerInterface):
    def __init__(self):
        self.is_finished = False

    def onStart(self,gracefulexit_event):
        t = "SimpleWorker(%d) start ..." % os.getpid()
        self.log(t)
        pass

    def onEnd(self, end_code, end_reason):
        t = "SimpleWorker(%d) end.with reason(%d:%s)" % (os.getpid(), end_code, end_reason)
        self.log(t)
        pass

    def onRunOnce(self):
        t = "SimpleWorker(%d) onRunOnce" % (os.getpid())
        self.log(t)
        self.is_finished = True
        pass

    def onTimer(self):
        t = "SimpleWorker(%d) onTimer" % (os.getpid())
        self.log(t)
        pass

    def finished(self):
        return self.is_finished

    def done(self):
        self.is_finished = True

    def timeout_ms(self):
        return 5000

    def log(self, txt):
        print "=>", txt
        pass

    def daemon(self):
        return True


###################################################
#   GracefulExitException
#
###################################################
class GracefulExitException(Exception):
    @staticmethod
    def sigterm_handler(signum, frame):
        raise GracefulExitException()

    pass


###################################################
#   GracefulExitException
#
###################################################
class GracefulExitEvent(object):
    def __init__(self):
        self.workers = []
        self.exit_event = multiprocessing.Event()
        self.timer_interface = None

        # Use signal handler to throw exception which can be caught
        # by worker process to allow graceful exit.
        signal.signal(signal.SIGTERM, GracefulExitException.sigterm_handler)

        pass

    def set_master_process_timer(self, timer_interface=SimpleTimer()):
        self.timer_interface = timer_interface

    def reg_worker(self, wp):
        self.workers.append(wp)
        pass

    def is_stop(self):
        return self.exit_event.is_set()

    def notify_stop(self):
        self.exit_event.set()

    def wait_all(self):
        while True:
            try:
                should_exit = True
                for wp in self.workers:
                    # print "main process({0}) observe child status=>name:{1} pid:{2} is_alive:{3}".format(os.getpid(), wp.name,wp.pid,wp.is_alive(),)
                    if wp.is_alive():
                        should_exit = False
                        break
                        # wp.join()
                if should_exit:
                    managerLogger.error("master process(%d) should_exit.", os.getpid())
                    break
                else:
                    if self.timer_interface:
                        time.sleep(self.timer_interface.timeout())
                        self.timer_interface.onTimer()
                    else:
                        time.sleep(3)
            except GracefulExitException:
                self.notify_stop()
                managerLogger.error("master process(%d) got graceful exit exception.", os.getpid())
            except:
                self.notify_stop()
                info = sys.exc_info()
                for file, lineno, function, text in traceback.extract_tb(info[2]):
                    str_info = "MasterLoop>{0} line:{1} in function:{2}".format(file, lineno, function)
                    managerLogger.critical(str_info)
                    str_text = "MasterLoop>** %s: %s" % info[:2]
                    managerLogger.critical(str_text)
                managerLogger.critical("=" * 15)

        managerLogger.critical("++++++++++++++++++++++++++++++")


#######################################################################
def worker_proc(gee, worker_interface=SimpleWorker()):
    try:
        worker_interface.onStart( gee  )
        last = int(time.time() * 1000)
        while not gee.is_stop():
            worker_interface.onRunOnce()
            if worker_interface.finished():
                worker_interface.onEnd(0, "finished")
                break
            current = int(time.time() * 1000)
            if current >= last + worker_interface.timeout_ms():
                worker_interface.onTimer()
                last = current
        else:
            worker_interface.onEnd(1, "got parent exit notify")
            managerLogger.error("worker process(%d) got parent exit notify.", os.getpid())
            return
    except GracefulExitException:
        worker_interface.onEnd(-1, "got graceful exit exception")
        managerLogger.error("worker process(%d) got graceful exit exception.", os.getpid())
        return
    except:
        info = sys.exc_info()
        for file, lineno, function, text in traceback.extract_tb(info[2]):
            str_info = "WorkerLoop>{0} line:{1} in function:{2}".format(file, lineno, function)
            managerLogger.critical(str_info)
            str_text = "WorkerLoop>** %s: %s" % info[:2]
            managerLogger.critical(str_text)
        managerLogger.critical("worker process(%d) caught unhandle exception", os.getpid())
        worker_interface.onEnd(-2, "caught unhandle exception")
        return
    finally:
        worker_interface.onEnd(2, "exit")
        managerLogger.critical("worker process(%d) exit", os.getpid())
        # sys.exit(0)
        os._exit(0)


#######################################################################
class MultiProcessWrapper(object):
    def __init__(self):
        pass

    # Start some workers process and run forever
    def startAsForver(self, worker_interface_array=list(), timer_interface=None):
        gee = GracefulExitEvent()
        gee.set_master_process_timer(timer_interface)
        for worker_interface in worker_interface_array:
            wp = multiprocessing.Process(target=worker_proc, args=(gee, worker_interface))
            wp.daemon = worker_interface.daemon()
            wp.start()
            gee.reg_worker(wp)
        gee.wait_all()


if __name__ == "__main__":
    print "main process(%d) start" % os.getpid()
    # p=MultiProcessWrapper()
    # p.startAsForver(SimpleWorker()      )
    # print "main process(%d) end" % (os.getpid())
