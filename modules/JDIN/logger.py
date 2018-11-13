#!/usr/bin/python3

from   logging.handlers import RotatingFileHandler
from   logging.handlers import TimedRotatingFileHandler
import logging
import os
import time
from datetime import datetime
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


class ExtendFileHandler (TimedRotatingFileHandler, RotatingFileHandler):
    def __init__(self,              \
                 filename,          \
                 mode        ='a',  \
                 maxBytes    = 0,   \
                 backupCount = 0,   \
                 encoding    = None,\
                 delay=0, when='h', interval=1, utc=False):
        TimedRotatingFileHandler.__init__( \
                self, filename=filename, when=when, interval=interval, \
                backupCount=backupCount, encoding=encoding, delay=delay,\
                utc=utc)

        RotatingFileHandler.__init__( \
                self, filename=filename, mode=mode, maxBytes=maxBytes, \
                backupCount=backupCount, encoding=encoding, delay=delay)


    def computeRollover(self, current_time):
        return TimedRotatingFileHandler.computeRollover(self, current_time)

    def isTimedRollover (self):
        fname = os.path.basename (self.baseFilename)

        tmp = fname.split('_')[1]
        fdate = tmp.split('.')[0]
        today = datetime.today().strftime("%Y%m%d")
        if fdate == today :
            return False
        return True

    def getBaseFileName (self):
        dname = os.path.dirname (self.baseFilename)
        fname = os.path.basename (self.baseFilename)
        pname = fname.split('_')[0]

        return dname + "/" + pname + "_" \
                + datetime.today().strftime("%Y%m%d") + ".log"

    def doRollover(self):
        # get from logging.handlers.TimedRotatingFileHandler.doRollover()
        current_time = int(time.time())
        dst_now = time.localtime(current_time)[-1]
        new_rollover_at = self.computeRollover(current_time)

        while new_rollover_at <= current_time:
            new_rollover_at = new_rollover_at + self.interval

        # If DST changes and midnight or weekly rollover, adjust for this.
        if (self.when == 'MIDNIGHT' \
                or self.when.startswith('W')) and not self.utc:
            dst_at_rollover = time.localtime(new_rollover_at)[-1]
            if dst_now != dst_at_rollover:
                # DST kicks in before next rollover, \
                #        so we need to deduct an hour
                if not dst_now:
                    addend = -3600
                else:
                    # DST bows out before next rollover,
                    # so we need to add an hour
                    addend = 3600
                new_rollover_at += addend
        self.rolloverAt = new_rollover_at

        if self.isTimedRollover() is True:
            self.stream.close()
            self.baseFilename = self.getBaseFileName()
            self.stream = open(self.baseFilename, 'a')
            return

        return RotatingFileHandler.doRollover(self)

    def shouldRollover(self, record):
        """
        description : determines when to roll over (overloading)
        """
        return TimedRotatingFileHandler.shouldRollover(self, record) \
                or RotatingFileHandler.shouldRollover(self, record)


class Logger ():
    def __init__(self, logger, pname):

        self.__format      = "[%(asctime)s] [%(levelname).1s]" + \
                             "[%(module)s:%(lineno)04d] %(message)s"
        self.__datefmt     = "%Y-%m-%d %H:%M:%S"

        self.__pname       = pname
        self.__fname       = None
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

        dir_name = home + "/log/" + self.__pname
        trace.error (dir_name)
        if not os.path.isdir (dir_name):
            try :
                os.makedirs (dir_name)
            except Exception as ex:
                trace.error (ex)
                return None
        self.__fname = dir_name + "/" + self.__pname + "_" \
                        + datetime.today().strftime("%Y%m%d") + ".log"

    def set_file (self):
        self.set_file_name()
        if self.__fname is None:
            return

        file_handle = ExtendFileHandler(self.__fname,     \
                                        maxBytes = self.__max_size, \
                                        when = 'midnight',    \
                                        backupCount=self.__num_of_file)

        trace.critical ("info, trace log [{0}, {1}, {2}, {3}]"
                .format (self.__fname, self.__max_size, \
                        self.__num_of_file, self.__level))
        formatter = logging.Formatter (self.__format, self.__datefmt)
        file_handle.setFormatter (formatter)
        self.__logger.addHandler(file_handle)
        self.set_level (self.__level)


    def set_stream (self):
        formatter = logging.Formatter (self.__format, self.__datefmt)
        stream_handle = logging.StreamHandler()
        stream_handle.setFormatter(formatter)
        stream_handle.setLevel (logging.DEBUG)
        self.__logger.addHandler(stream_handle)


    def setup (self, config_fname, size_unit=1024*1024):
        try :
            conf_handle = None
            conf_handle = config.ConfigFile()
            conf_handle.open (config_fname)
        except Exception as ex:
            return False

        self.__num_of_file = (int) (conf_handle.get ("LOG", "FILECNT"))
        self.__level       = (int) (conf_handle.get ("LOG", "LEVEL"))
        self.__max_size    = (int) (conf_handle.get ("LOG", "SIZE"))
        self.__max_size    = self.__max_size * size_unit
        trace.critical ("info, trace log [{0}, {1}, {2}"
                .format (self.__max_size, \
                        self.__num_of_file, self.__level))
        self.set_file ()

def __test_main():
    logger = Logger(trace, "CLIP")
    logger.setup ("/home/bychoi/config/CLIP.INI", size_unit=1)
    logger.set_stream ()
    trace.debug ("debug : --------------")
    trace.info  ("info  : --------------")
    trace.warn  ("warn  : --------------")
    trace.error ("error : --------------")
    trace.critical ("error : --------------")


if __name__ == '__main__':
    __test_main()
