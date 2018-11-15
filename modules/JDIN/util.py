#!/usr/bin/python3

import logging
import time
import os

trace = logging.getLogger(__name__)

class PendingQueue ():
    """
    name : PendingQueue()
    desc : package common queue
           item = {'key'  : search key,
                   'value': user defined data}
    """
    def __init__(self):
        self.queue       = list()
        self.expire_tick = 5

    def count (self):
        return len(self.queue)
    def set_expire_tick (self, tick):
        self.expire_tick = tick

    def insert (self, key, value):
        try :
            item = dict()
            item['key']         = key
            item['expire_tick'] = int(time.time()) + self.expire_tick
            item['value']       = value

            self.queue.append (item)
            return True, None
        except Exception as ex:
            err_string = "fail, internal exception: {0}, {1}".format(ex, value)
            return False, err_string

    def select (self, key):
        index = 0
        item  = None
        for item in self.queue:
            if item['key'] == key:
                return index, item['value']
            index += 1
        return None, None

    def delete (self, index):
        try :
            del self.queue [index]
            return True, None
        except Exception as ex:
            err_string = "fail, internal exception: {0}, {1}".format(ex, index)
            return False, err_string

    def select_timer_expired (self, tick):
        index = 0
        item  = None
        for item in self.queue:
            if item['expire_tick'] < int(time.time()):
                return index, item['value']
            index += 1
        return None, None


def get_pkg_home ():
    try :
        pkg_root = os.environ ['PKG_ROOT']
    except Exception as ex:
        if type(ex).__name__ == "KeyError":
            trace.error ("fail, not found ENV variable [{0}]"\
                          .format('PKG_ROOT'))
        else:
            trace.error (ex)
        return None
    return pkg_root

