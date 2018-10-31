#!/usr/bin/python3

import logging
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
        self.queue = list()

    def count (self):
        return len(self.queue)

    def insert (self, value):
        try :
            self.queue.append (value)
            return True, None
        except Exception as ex:
            err_string = "fail, internal exception: {0}, {1}".format(ex, value)
            return False, err_string

    def select (self, key):
        index = 0
        item  = None
        for item in self.queue:
            if item['key'] == key:
                return index, item
            index += 1
        return None, None

    def delete (self, index):
        try :
            del self.queue [index]
            trace.debug ("--------------------------")
            return True, None
        except Exception as ex:
            err_string = "fail, internal exception: {0}, {1}".format(ex, index)
            return False, err_string


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

