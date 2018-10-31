#!/usr/bin/python3

import asyncio
import logging
import json
import os
import sys
#from abc import *

from JDIN.CLI import cli
from JDIN.CLI import pod


NMS_CMD_DICTIONARY_PATH = os.environ['PKG_ROOT'] + "/config/command/"

trace = logging.getLogger(__name__)

class NMSCommandParser ():
    def __init__(self, command_line):
        self.__command_terminator = ';'
        self.__name_delimiter     = ":"
        self.__para_separator     = ","
        self.__value_delimiter    = "="

        self.__command_line       = command_line
        self.__command_list       = list()
        self.__error_string       = ""


    def __parser_command_line (self, command):
        """
        command = {'line'     : "command line",
                   'name'     : "name",
                   'parameter : {"field1" : "value1",
                                 "field2" : "value2", ...}}
        """
        line = command['line']
        tokens = [item.strip() for item in line.split(self.__name_delimiter)]

        #
        # command name
        #
        if tokens [0][-1] == '?' or tokens[0][0] == '?':
            tmp = tokens[0]
            tokens[0] = "HELP"
            tokens.append("COMMAND=" + tmp.strip('?').strip('/'))
        command['name'] = tokens[0]


        #
        # command_parameter
        #
        if (len (tokens) > 1) and len(tokens[1]) > 0 \
                and  (self.__para_separator is not None) :
            parameter = dict()
            tokens = [item.strip() \
                      for item     \
                      in  tokens[1].split(self.__para_separator)]

            for item in tokens:
                try :
                    value = item.split(self.__value_delimiter)
                    if len (value) == 1 :
                        parameter[value[0].lower()] = None
                    else :
                        parameter[value[0].lower()] = \
                                value[1].strip('\"').strip('\'')
                except Exception as ex:
                    self.__error_string = \
                            "fail, invalid command parameter {0}"\
                            .format(command['line'])
                    self.__error_string += "[exception [name:{0}, args:{1}]"\
                                            .format(type(ex).__name__, ex.args)
                    trace.error (self.__error_string)
                    return False
            command['parameter'] = parameter
        else :
            command['parameter'] = {}

        return True


    def __parser_command_list (self):
        command_list = \
                [item.strip() for item \
                 in  self.__command_line.split(self.__command_terminator)]

        for token in command_list:
            command = dict()
            if len(token) == 0:
                continue
            command['line'] = token.strip()
            self.__command_list.append (command)


    def do_parging (self):
        self.__parser_command_list ()
        for item in self.__command_list:
            if self.__parser_command_line (item) != True:
                return False
        self.parser_print()
        return True


    def __get_command_fname (self, path, name):
        fname = path.rstrip('/') + '/' + name.lower() + ".json"

        if os.path.exists(fname) is True:
            return fname

        fname = path.rstrip('/') + '/' + name.upper() + ".json"
        if os.path.exists (fname) is True:
            return fname
        return None


    def do_job (self, path):
        if self.do_parging() is not True:
            return None

        dictionary = list()
        for command in self.__command_list:
            fname = self.__get_command_fname (path, command['name'])
            if fname is None:
                self.__error_string = \
                        "fail, undefined command name [{0}]"\
                        .format(command['line'])
                return None
            try :
                instance = pod.CommandDictionary()
                instance.set_pod_fname (fname)
                e_code = instance.open_pod()
                if e_code is not True:
                    self.__error_string += instance.get_pod_error_string()
                    trace.error (self.__error_string)
                    return None

                instance.set_pod_command (command['line'])
                e_code = instance.set_pod_request (command['parameter'])
                if e_code is not True:
                    trace.error (instance.get_pod_error_string())
                    self.__error_string += instance.get_pod_error_string()
                    return None

                dictionary.append (instance)
            except Exception as ex:
                self.__error_string += instance.get_pod_error_string()
                self.__error_string += "[exception [name:{0}, args:{1}]"\
                                        .format(type(ex).__name__, ex.args)
                trace.error (self.__error_string)
                return None
        return tuple (dictionary)

    def get_error_string (self):
        return self.__error_string

    def parser_print (self):
        trace.critical ("{0}".format (self.__command_list))


class NMSClient (cli.CLIClient):
    fault_instance       = None
    state_instance       = None
    command_instance     = None
    period_instance      = None
    real_instance        = None

    def __init__(self, reader, writer):
        # Protocol status
        self.protocol_status = False
        self.alive_timeout   = 0

        self.__istream       = reader
        self.__ostream       = writer
        self.__addr          = writer.get_extra_info('peername')

        self.__parser        = None
        try :
            cli.CLIClient.__init__(self)
        except Exception as ex:
            trace.error (ex)


    def get_addr (self): return self.__addr
    def set_fault_instance (self, instance):
        NMSClient.fault_instance   = instance

    def set_state_instance (self, instance):
        NMSClient.state_instance  = instance

    def set_real_instance (self, instance):
        NMSClient.real_instance    = instance

    def set_period_instance (self, instance):
        NMSClient.period_instance  = instance

    def set_command_instance (self, instance):
        NMSClient.command_instance = instance

    def __get_current_state (self):
        return (self.protocol_status)
    def __set_active_current_state (self):
        self.protocol_status = True
    def __set_inactive_current_state (self):
        self.protocol_status = False

    def __encode_header (self, header):
        packet = struct.pack("!iihhi",header[0], \
                                      header[1],\
                                      header[2],\
                                      header[3],\
                                      header[4])
        return packet


    async def __check_app_status (self, header, parameter = None):
        response = self.__encode_header((header[0] + 1, \
                                         header[1], \
                                         header[2], \
                                         header[3], \
                                         0))
        try:
            await self.__send (response)
            trace.info ("succ, {} send check_app response"\
                    .format(self.get_addr()))
        except Exception as ex:
            pass

    async def __close_port_connection (self, header, parameter = None):
        response = self.__encode_header((header[0] + 1, \
                                         header[1], \
                                         header[2], \
                                         header[3], \
                                         0))
        try :
            await self.__send (response)
            self.__set_inactive_current_state()
            trace.info ("succ, {} close_port ".format(self.get_addr()))
        except Exception as ex:
            pass

    async def __stop_msg_transmission (self, header, parameter = None):
        response = self.__encode_header((header[0] + 1, \
                                         header[1], \
                                         header[2], \
                                         header[3], \
                                         0))
        try :
            await self.__send (response)
            self.__set_inactive_current_state()
            trace.info ("succ, {} stop_msg ".format(self.get_addr()))
        except Exception as ex:
            pass


    async def __confirm_port_type (self, header, parameter):
        port_type   = int.from_bytes(parameter[0], byteorder='big')
        """
        if port_type == 0x01:
            trace.debug ("info, fault    managment  port")
        elif prot_type == 0x02:
            trace.debug ("info, realtime performace port")
        elif prot_type == 0x03:
            trace.debug ("info, longtime performace port")
        elif prot_type == 0x04:
            trace.debug ("info, status   management port")
        elif prot_type == 0x05:
            trace.debug ("info, operater command    port")
        elif prot_type == 0x06:
            trace.debug ("info, backup   data       port")
        """
        trace.debug ("------------------debug1---------------")
        response = self.__encode_header((header[0] + 1, \
                                         header[1], \
                                         header[2], \
                                         header[3], \
                                         0))
        try :
            trace.debug ("------------------debug2---------------")
            await self.__send (response)
            trace.info ("succ, {} confirm_port [type:{}]"\
                        .format(self.get_addr(), port_type))
        except Exception as ex:
            trace.error ("fail, {0} confimr_port_type [{1}]"\
                    .format(self.get_addr(), ex))

    async def __start_msg_transmission (self, header, parameter):
        msg_type   = int.from_bytes (parameter[0], byteorder='big')
        response = self.__encode_header((header[0] + 1, \
                                         header[1], \
                                         header[2], \
                                         header[3], \
                                         0))
        try :
            await self.__send (response)
            self.__set_active_current_state()

            trace.info ("succ, {} start_msg [type:{}]"\
                        .format(self.get_addr(), msg_type))
        except Exception as ex:
            pass


    async def __in_command (self, header, parameter):
        '''
        ptype     : 0x0000005
        parameter : InOut String
        '''
        try :
            dictionary = None
            parser = NMSCommandParser(parameter)
            dictionary = parser.do_job (self.get_path())
            if dictionary is None:
                code = 0
                err  = "SUCC, synctax checking"
            else :
                code = 1

            resp_header = self.__encode_header((header[0] + 1, \
                                                header[1], \
                                                header[2], \
                                                header[3], \
                                                len(err.encode())+1))
            format='b{0}s'.format(len(err.encode()))
            resp_parameter = struct.pack (format, code, err.encode())

            msg = resp_header + resp_parameter
            await self.__send(msg)
        except Exception as ex:
            trace.error ("fail, {}".format(ex))
        finally :
            return dictionary


    async def __output_msg (self, msg):
        ptype         = 0x00000007
        msgid         = msg['key']
        value         = msg['value'].encode()
        total_length  = len(value)
        para_length   = total_length
        start_index   = 0
        segment_num   = 0
        segment_flag  = 0

        try :
            while total_length > 0:
                segment_flag = 0x00
                if total_length > 4096:
                    segment_flag = 1
                    segment_num += 1
                    para_length  = 4096

                parameter = value[start_index:start_index + para_length]
                packet = struct.pack("!iihhi{0}s".format(para_length), ptype, \
                                               msgid,\
                                               segment_flag,\
                                               segment_num,\
                                               para_length,
                                               parameter)

                start_index  += para_length
                total_length -= para_length

                await NMSClient.state_instance.__send (packet)

            return True

        except Exception as ex:
            trace.error ("fail, {} send to client [{}]".format(self.get_addr(), ex))
            return False


    async def __send (self, msg):
        try:
            self.__ostream.write (msg)
            await self.__ostream.drain()
            trace.debug ("info, {0} send msg [{1}]"\
                        .format(self.get_addr(), msg))
        except Exception as ex:
            trace.error ("fail, {} send [{}]".format(self.get_addr(), ex))

    def __decode_header (self, in_bytes):
        ptype , \
        msgid, \
        segment_flag, \
        segment_num, \
        para_length= struct.unpack("!iihhi", in_bytes)

        header = (ptype, msgid, segment_flag, segment_num, para_length)
        trace.debug ("info, {0} decode header [{1}".format(self.get_addr(), header))
        return header


    def __decode_body (self, in_bytes):
        return (in_bytes,)

    async def __recv (self):
        try :
            in_bytes = await self.__istream.readexactly(16)
            header = self.__decode_header (in_bytes)

            if header [4] > 0:
                parameter = None
                in_bytes = await self.__istream.readexactly (header[4])
                if in_bytes is None:
                    return None, None
                parameter = self.__decode_body (in_bytes)
                trace.debug ("info, {0} recv parameter [{1}]"\
                            .format(self.get_addr(), parameter))
                return header, parameter
            else :
                return header, None
        except Exception as ex:
            trace.error ("fail, {0} recv request [{1}]"\
                    .format(self.get_addr(), ex))
            return None, None

    async def __setup (self):
        trace.info ("-----------------------------".format(self.get_addr()))
        trace.info ("info, {} start setup protocol".format(self.get_addr()))
        try :
            header, parameter = await self.__recv()
            if header[0] != 0x00000008:
                raise ValueError
            await self.__confirm_port_type(header, parameter)

            header, parameter = await self.__recv()
            if header[0] != 0x0000000A:
                raise ValueError
            await self.__start_msg_transmission(header, parameter)
            self.status = True
            trace.info ("succ, {} complete setup protocol"\
                    .format(self.get_addr()))
            trace.info ("-----------------------------".format(self.get_addr()))
        except Exception as ex:
            self.status = False

    async def __recv_command (self):
        try :
            dictionary = None
            while True:
                header, parameter = await self.__recv()
                ptype = header[0]
                if ptype == 0x00000001:
                    await self.__check_app_status (header, parameter)
                    continue
                elif ptype == 0x00000003:
                    await self.__close_port_connection(header, parameter)
                    continue
                elif ptype == 0x00000005:
                    dictionary = await self.__in_command (header, parameter)
                    if dictionary is None:
                        continue
                    break;
                elif ptype == 0x00000008:
                    await self.__confirm_port_type (header, parameter)
                    continue
                elif ptype == 0x0000000A:
                    await self._start_msg_transmission(header, parameter)
                    continue
                elif ptype == 0x0000000C:
                    await self.__stop_msg_transmission(header, parameter)
                    continue
                else:
                    trace.error ("fail, recv unknown ptype [{}:{}"\
                            .format(self.get_addr(), ex))
            return dictionary
        except Exception as ex:
            trace.error ("fail,{0} exception[{1}]".format(self.get_addr(), ex))
            return None

    async def recv (self):
        try:
            if self.__get_current_state() != True:
                try:
                    await self.__setup()
                except Exception as ex:
                    pass

            dictionary = await self.__recv_command ()
            return dictionary
        except Exception as ex:
            trace.error (ex)


    async def send (self, msg):
        trace.debug ("send. code={0}, value={1}".format(msg['code'], msg['value']))
        return await self.__output_msg (msg)


    def open (self):
        pass

    def close (self):
        self.__ostream.close()
        self.__ostream = None
        self.__istream = None
        self.__addr    = None


class NMSJob ():
    def __init__(self, fault=8282, real=8283, \
                       period=8284, state=8285, command=8286):
        self.nms_fault_port       = fault;
        self.nms_real_port        = real;
        self.nms_period_port      = period;
        self.nms_state_port       = state;
        self.nms_command_port     = command;

    async def handle_fault (self, reader, writer):
        try :
            instance = NMSClient(reader, writer)
            instance.set_fault_instance(instance)
            await instance.run()
        except Exception as ex:
            pass
        finally :
            instance.close()

    async def handle_real (self, reader, writer):
        try :
            instance = NMSClient(reader, writer)
            instance.set_real_instance(instance)
            await instance.run()
        except Exception as ex:
            pass
        finally :
            instance.close()

    async def handle_period (self, reader, writer):
        try :
            instance = NMSClient(reader, writer)
            instance.set_period_instance(instance)
            await instance.run()
        except Exception as ex:
            pass
        finally :
            instance.close()

    async def handle_state (self, reader, writer):
        try :
            instance = NMSClient(reader, writer)
            instance.set_state_instance(instance)
            await instance.run()
        except Exception as ex:
            pass
        finally :
            instance.close()

    async def handle_command (self, reader, writer):
        try :
            instance = NMSClient(reader, writer)
            instance.set_command_instance(instance)
            await instance.run()
        except Exception as ex:
            pass
        finally :
            instance.close()

    def do_job (self, event_loop):
        event_loop.run_until_complete(asyncio.start_server(self.handle_fault,\
                                                          None,\
                                                          self.nms_fault_port,\
                                                          loop=event_loop))
        event_loop.run_until_complete(asyncio.start_server(self.handle_real,\
                                                          None,\
                                                          self.nms_real_port,\
                                                          loop=event_loop))

        event_loop.run_until_complete(asyncio.start_server(self.handle_period,\
                                                          None,\
                                                          self.nms_period_port,\
                                                          loop=event_loop))
        event_loop.run_until_complete(asyncio.start_server(self.handle_state,\
                                                          None,\
                                                          self.nms_state_port,\
                                                          loop=event_loop))
        event_loop.run_until_complete(asyncio.start_server(self.handle_command,\
                                                          None,\
                                                          self.nms_command_port,\
                                                          loop=event_loop))

