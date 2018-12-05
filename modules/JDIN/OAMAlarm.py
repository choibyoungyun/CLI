#!/usr/bin/env python3
import sys
import struct
import logging
from JDIN               import logger
from JDIN.IPCProtocol   import JDINIPCProtocol
from JDIN.OAMTester     import Tester

trace = logging.getLogger(__name__)


class JDINAlarmReport ():
    def __init__(self, raw_bytes=None):
        self.raw_bytes       = raw_bytes
        self.__packet_format = 'hhhhhhhhh129s129s129s33s33s33s'
        self.__packet_size   = struct.calcsize (self.__packet_format)

        # packet field name
        self.code     = None
        self.onoff    = None
        self.grade    = None
        self.reason   = None
        self.shelf    = None
        self.slot     = None
        self.node     = None
        self.block    = None
        self.area     = None
        self.subid    = None
        self.strloc   = None
        self.info     = None
        self.data1    = None
        self.data2    = None
        self.data3    = None


    def get_size (self):
        return self.__size

    def get_packet (self):
        return self.raw_bytes


    def encode (self):
        try:
            self.raw_bytes = struct.pack (self.__packet_format,self.code ,\
                                                        self.onoff    ,\
                                                        self.grade    ,\
                                                        self.reason   ,\
                                                        self.shelf    ,\
                                                        self.slot     ,\
                                                        self.node     ,\
                                                        self.block    ,\
                                                        self.area     ,\
                                                        self.subid    ,\
                                                        self.strloc   ,\
                                                        self.info     ,\
                                                        self.data1    ,\
                                                        self.data2    ,\
                                                        self.data3)
            return True
        except Exception as ex:
            trace.error ("fail, {0} [name:{1}, args:{2}"  \
                         .format(self.__class__.__name__, \
                                 type(ex).__name__, ex.args))
            return False


    def set_packet (self, code, onoff, grade, reason, shelf, slot, node, \
                    block, area, subid, strloc, info, data1, data2, data3):
        try:
            self.code     = code
            self.onoff    = onoff
            self.grade    = grade
            self.reason   = reason
            self.shelf    = shelf
            self.slot     = slot
            self.node     = node
            self.block    = block
            self.area     = area
            self.subid    = subid.encode()
            self.strloc   = strloc.encode()
            self.info     = info.encode()
            self.data1    = data1.encode()
            self.data2    = data2.encode()
            self.data3    = data3.encode()
            self.encode()

            return True
        except Exception as ex:
            trace.error ("fail, {0} [name:{1}, args:{2}"  \
                         .format(self.__class__.__name__, \
                                 type(ex).__name__, ex.args))
            return False


    def decode (self):
        try:
            self.code     ,\
            self.onoff    ,\
            self.grade    ,\
            self.reason   ,\
            self.shelf    ,\
            self.slot     ,\
            self.node     ,\
            self.block    ,\
            self.area     ,\
            self.subid    ,\
            self.strloc   ,\
            self.info     ,\
            self.data1    ,\
            self.data2    ,\
            self.data3    = struct.unpack(self.__packet_format, self.raw_bytes)

            return True
        except Exception as ex:
            trace.error ("fail, {0} [name:{1}, args:{2}"  \
                         .format(self.__class__.__name__, \
                                 type(ex).__name__, ex.args))
            return False


class JDINAlarmList ():
    def __init__(self, raw_bytes=None):
        self.raw_bytes    = raw_bytes
        self.jobkey       = None
        self.num_of_alarm = None
        self.alarms       = list()


    def add_alarm   (self, alarm_report):
        self.alarms.append(alarm_report)


    def get_alarm_packet (self):
        out_packet = None
        if len(self.alarms) :
            out_packet = self.alarms[0]
        else :
            return None

        for alarm in self.alarms[1:]:
            out_packet += alarm
        return out_packet


    def set_packet (self, alarm_packet = None):
        # set jobkey and number of alarm report  value
        self.jobkey       = 0
        if alarm_packet:
            self.add_alarm(alarm_packet)
        self.num_of_alarm = len(self.alarms)
        num_bytes  = struct.pack('Ii',self.jobkey, self.num_of_alarm)
        trace.debug ("JOBKEY/COUNT : {0}".format(num_bytes))

        # set alarm report packet
        alarm_bytes  = self.get_alarm_packet()
        if alarm_bytes is None:
            self.raw_bytes = num_bytes
        else :
            self.raw_bytes = num_bytes + alarm_bytes

    def get_packet (self):
        return self.raw_bytes


class AlarmTester(Tester):
    def __init__(self):
        pass

    def get_alarm_report_packet (self):
        handle = JDINAlarmReport()
        field = self.tcase['ALARM']
        handle.set_packet (int(field['code']),
                                 int(field['onoff']),
                                 int(field['grade']),
                                 int(field['reason']),
                                 int(field['shelf']),
                                 int(field['slot']),
                                 int(field['node']),
                                 int(field['block']),
                                 int(field['area']),
                                 field['subid'],
                                 field['strloc'],
                                 field['info'],
                                 field['data1'],
                                 field['data2'],
                                 field['data3'])
        return handle.get_packet()


    def get_alarm_list_packet (self):

        alarm_handle = JDINAlarmList()
        alarm_handle.set_packet (self.get_alarm_report_packet())

        ipc_handle = JDINIPCProtocol()
        field = self.tcase['SIGNAL']
        ipc_handle.set_packet(int(field['signal_id']),
                              int(field['source_node']),
                              int(field['destination_node']),
                              int(field['source_block']),
                              int(field['destination_block']),
                              int(field['source_area']),
                              int(field['destination_area']),
                              alarm_handle.get_packet())
        return ipc_handle.get_packet()

    def run (self, ip, port, case):
        # initialize trasport protocol
        super().__init__(ip, port)

        # load test case
        self.load_tcase (case)

        self.run_client(self.get_alarm_list_packet())


    def stop (self):
        self.stop_client()
