#!/usr/bin/python3

import logging
import sys
from configparser import ConfigParser


trace = logging.getLogger(__name__)

class ConfigFile ():
    def __init__ (self):
        self.__instance = None
        self.__fname    = None

    def open (self, fname):
        self.__fname = fname
        try :
            self.__instance = ConfigParser()
            self.__instance.read (self.__fname)
        except Exception as ex:
            err_string = "name:{0}, args:{1}"\
                         .format(type(ex).__name__, ex.args)
            trace.error (err_string)

    def get (self, section, field, default = None):
        try :
            value = None
            value = self.__instance.get(section, field)
            if value is None:
                value = default
            return value
        except Exception as ex:
            err_string = "name:{0}, args:{1}"\
                         .format(type(ex).__name__, ex.args)
            trace.error (err_string)
            return None



def __test_main():

    if len(sys.argv) < 3:
        print ("Usage: {0} fname section variable"\
                .format(sys.argv[0]))
        return

    formatter = logging.Formatter ("[%(levelname).1s]" + \
                                   "[%(module)s:%(lineno)04d] %(message)s")
    stream_handle = logging.StreamHandler()
    stream_handle.setFormatter(formatter)
    trace.addHandler(stream_handle)
    trace.setLevel (logging.DEBUG)

    config = ConfigFile()
    config.open (sys.argv[1])

    value = config.get (sys.argv[2], sys.argv[3], "5")
    print (value)

if __name__ == '__main__':
    __test_main()
