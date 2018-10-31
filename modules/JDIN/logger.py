#!/usr/bin/python3

from   logging.handlers import RotatingFileHandler
from   logging.handlers import TimedRotatingFileHandler
import logging
import os
import time
from JDIN import config
from JDIN import util

trace  =  logging.getLogger(__name__)

def init_logger ():

    formatter = logging.Formatter ("[%(asctime)s] [%(levelname).1s]" + \
                                   "[%(module)s:%(lineno)04d] %(message)s",\
                                   datefmt="%Y-%m-%d %H:%M:%S")
    stream_handle = logging.StreamHandler()
    stream_handle.setFormatter(formatter)
    stream_handle.setLevel (logging.DEBUG)
    trace.addHandler(stream_handle)


class Logger ():
    def __init__(self, logger, name):
        self.__format      = "[%(asctime)s] [%(levelname).1s]" + \
                             "[%(module)s:%(lineno)04d] %(message)s"
        self.__datefmt     = "%Y-%m-%d %H:%M:%S"

        self.__pname       = name
        self.__level       = logging.DEBUG
        self.__num_of_file = 10
        self.__max_size    = (10*1024*1024)

        self.__logger      = logger


    def get_logger (self):
        return self.__logger


    def set_formatrer (self, formatter = None):
        if formatter is None:
            self.__logger.setFormatter(self.__formatter, self.__datefmt)
        else :
            self.__formatter = formatter
            self.__logger.setFormatter (self.__formatter, self.__datefmt)


    def set_level (self, level):
        self.__level = level
        if self.__level == 5:
            self.__logger.setLevel (logging.DEBUG)
        elif self.__level == 4:
            self.__logger.setLevel (logging.INFO)
        elif self.__level == 3:
            self.__logger.setLevel (logging.WARNING)
        elif self.__level == 2:
            self.__logger.setLevel (logging.ERROR)
        elif self.__level == 1:
            self.__logger.setLevel (logging.CRITICAL)
        elif self.__level == 0:
            self.__logger.setLevel (logging.NOTSET)
        else :
            pass

    def set_file_name (self):
        home = util.get_pkg_home()
        if home in self.__pname:
            return None

        dir_name = home.rstrip('/') + "/log/" + self.__pname
        if not os.path.isdir (dir_name):
            try :
                os.makedirs (dir_name)
            except Exception as ex:
                return None
        return dir_name + "/" + self.__pname
    def set_file (self):
        log_fname = self.set_file_name()
        if log_fname is None:
            return

        #file_handle = RotatingFileHandler(log_fname, \
        #                                  self.__max_size, self.__num_of_file)
        file_handle = TimedRotatingFileHandler(log_fname,    \
                                               when = 'D',   \
                                               backupCount=10)

        trace.critical ("info, trace log [{0}, {1}, {2}, {3}"
                .format (log_fname, self.__max_size, \
                        self.__num_of_file, self.__level))
        formatter = logging.Formatter (self.__format, self.__datefmt)
        file_handle.setFormatter (formatter)
        #file_handle.setLevel (self.__level)
        self.__logger.addHandler(file_handle)
        self.set_level (self.__level)


    def set_stream (self):
        formatter = logging.Formatter (self.__format, self.__datefmt)
        stream_handle = logging.StreamHandler()
        stream_handle.setFormatter(formatter)
        stream_handle.setLevel (logging.DEBUG)
        self.__logger.addHandler(stream_handle)


    def setup (self, config_fname):
        try :
            conf_handle = None
            conf_handle = config.ConfigFile()
            conf_handle.open (config_fname)
        except Exception as ex:
            return False

        self.__num_of_file = (int) (conf_handle.get ("LOG", "FILECNT"))
        self.__level       = (int) (conf_handle.get ("LOG", "LEVEL"))
        self.__max_size    = (int) (conf_handle.get ("LOG", "SIZE"))
        self.__max_size    = self.__max_size * (1024*1024)
        trace.critical ("info, trace log [{0}, {1}, {2}"
                .format (self.__max_size, \
                        self.__num_of_file, self.__level))
        self.set_file ()

def __test_main():
    logger = Logger(trace, "CLIP")
    logger.setup ()
    logger.set_stream ()
    trace.debug ("debug : --------------")
    trace.info  ("info  : --------------")
    trace.warn  ("warn  : --------------")
    trace.error ("error : --------------")
    trace.critical ("error : --------------")


if __name__ == '__main__':
    __test_main()
