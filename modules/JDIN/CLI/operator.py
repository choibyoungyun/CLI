#!/usr/bin/python3

import asyncio
import logging
import json
import os
import sys
#from abc import *

from JDIN.CLI import cli
from JDIN.CLI import pod
from JDIN.CLI import ems

from JDIN     import config
from JDIN     import logger

CLI_MAX_CMD_REQUEST_LEN = 1024
trace = logging.getLogger(__name__)


# ##############################################################
#  ERROR STRING
#  ------------------------------------------------------------
#  UNDEFINED_COMMAND : fail, undefined command name    [{0}]
#  INVALID_PARAMETER : fail, invalid command parameter [{0}]
# ##############################################################


class OPParser ():
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
        trace.debug ("{0}".format (self.__command_list))


class OPProtocol ():
    def __init__(self, reader, writer, addr):
        self.__istream     = reader
        self.__ostream     = writer
        self.__addr        = addr
        self.__is_connectd = False

    def get_addr (self):
        return self.__addr

    def open (self):
        pass

    def close (self):
        self.__ostream.close()
        self.__ostream = None
        self.__istream = None
        self.__addr    = None

    async def send (self, msg):
        try:
            out_bytes = None
            out_bytes = msg.encode()
            self.__ostream.write (out_bytes)
            await self.__ostream.drain()
            trace.debug ("info, {0} send msg [{1}]"\
                        .format(self.get_addr(), out_bytes))
        except Exception as ex:
            trace.error ("fail, {} send [{}]".format(self.get_addr(), ex))

    async def recv (self):
        try :
            in_bytes = await self.__istream.read(CLI_MAX_CMD_REQUEST_LEN)
            if in_bytes is None or len(in_bytes) == 0 :
                return None, None
            trace.debug ("info, {0} recv msg [{1}]"\
                        .format(self.get_addr(), in_bytes))
            return True, in_bytes
        except Exception as ex:
            trace.error ("fail, {0} recv request [{1}]"\
                    .format(self.get_addr(), ex))
            return None, None


class OPClient (cli.CLIClient):
    def __init__(self, reader, writer):
        self.__parser   = None
        self.__protocol = OPProtocol (reader, writer,\
                                      writer.get_extra_info('peername'))
        try :
            cli.CLIClient.__init__(self)
        except Exception as ex:
            trace.error (ex)

    def get_addr (self):
        return self.__protocol.get_addr()
    def open (self):
        self.__protocol.open()

    def close (self):
        self.__protocol.close()

    async def send (self, msg):
        out_msg = None
        response = dict()
        response['result']="OK"
        response['value'] = msg['value']

        try :
            out_msg = json.dumps(response)
        except Exception as ex:
            trace.error ("fail, {} send [{}]".format(self.get_addr(), ex))
            response['result']= "NOK"
            response['value'] = "fail, internal [{0}]".format(ex)
            out_msg = json.dumps(response)
            await self.__protocol.send(out_msg)
        else :
            await self.__protocol.send(out_msg)


    async def recv (self):
        try:
            while True:
                e_code, in_bytes = await self.__protocol.recv()
                if e_code is not True:
                    return None
                parser = OPParser(in_bytes.decode())
                dictionary = parser.do_job (self.get_path())
                if dictionary is None:
                    msg = dict()
                    msg['value'] = parser.get_error_string()
                    await self.send (msg)

                    del msg
                    del parser
                    continue
                else:
                    break
            return dictionary
        except Exception as ex:
            trace.error (ex)


class OPJob ():
    def __init__(self, loop):
        self.__event_loop     = loop
        self.__dict_path      = None
        self.__config         = None

        self.__operator_port   = 5757
        self.__operator_ip     = None
        self.__operator_system = None

        self.__command_ip      = "127.0.0.1"
        self.__command_port    = 5757
        self.__command_system  = None

        self.__trace_ip        = "127.0.0.1"
        self.__trace_port      = 5758
        self.__trace_system    = None

        self.__report_ip       = "127.0.0.1"
        self.__report_port     = 5759
        self.__report_system   = None

        self.__tasks           = None

    def set_config(self, pname):
        try :
            pkg_root = os.environ ['PKG_ROOT']
        except Exception as ex:
            if type(ex).__name__ == "KeyError":
                trace.error ("fail, not found ENV variable [{0}]"\
                             .format('PKG_ROOT'))
            else:
                trace.error (ex)
            return False

        try :
            fname = pkg_root.rstrip('/') + "/config/" + pname + ".INI"
            self.__config = config.ConfigFile()
            self.__config.open (fname)
        except Exception as ex:
            trace.error (ex)
            return False

        self.__operator_ip    = self.__config.get ("OPERATOR", "IP")
        self.__operator_port  = self.__config.get ("OPERATOR", "PORT")

        self.__command_ip     = self.__config.get ("COMMAND", "IP")
        self.__command_port   = self.__config.get ("COMMAND", "PORT")
        self.__command_system = ems.EMSClient (self.__command_ip, \
                                               self.__command_port)

        self.__trace_ip     = self.__config.get ("TRACE", "IP")
        self.__trace_port   = self.__config.get ("TRACE", "PORT")
        self.__trace_system = ems.EMSClient (self.__trace_ip, \
                                             self.__trace_port,
                                             "TRACE")

        self.__report_ip    = self.__config.get ("REPORT", "IP")
        self.__report_port  = self.__config.get ("REPORT", "PORT")
        self.__report_system = ems.EMSClient (self.__report_ip, \
                                             self.__report_port,
                                             "REPORT")

        self.__tasks = [self.__command_system, \
                        self.__trace_system,
                        self.__report_system]

        self.__dict_path = self.__config.get ("DICTIONARY", "PATH")
        return True

    async def __handle_command (self, reader, writer):
        try :
            instance = None
            instance = OPClient(reader, writer)
            instance.set_path (self.__dict_path)

            instance.set_command_system(self.__command_system)
            instance.set_trace_system(self.__trace_system)
            instance.set_report_system(self.__report_system)

            await instance.run()
        except Exception as ex:
            trace.debug (ex)
        finally :
            if instance is not None:
                instance.close()
                instance.set_report_off()
                instance.set_trace_off()
                instance = None

    def do_server_job (self):
        self.__event_loop.run_until_complete (\
                asyncio.start_server(self.__handle_command,\
                self.__operator_ip, self.__operator_port,  \
                loop=self.__event_loop))
        trace.critical ("succ, ({0},{1}) operator server startup complete"\
                        .format(self.__operator_ip, self.__operator_port))
        #
        # NMS SERVER
        #
        #instance = nms.NMSJob()
        #instance.do_job(self.__event_loop)

    async def __run_client (self):
        coros = [task.start_client() for task in self.__tasks]
        await asyncio.gather (*coros)

    def do_client_job (self):
        self.__event_loop.run_until_complete (self.__run_client())

    def do_job (self):
        self.do_server_job()
        self.do_client_job()


def __test_main():

    if len(sys.argv) < 2:
        print ("Usage: {0} cod".format(sys.argv[0]))
        return

    formatter = logging.Formatter ("[%(levelname).1s]" + \
                                   "[%(module)s:%(lineno)04d] %(message)s")
    stream_handle = logging.StreamHandler()
    stream_handle.setFormatter(formatter)
    trace.addHandler(stream_handle)
    trace.setLevel (logging.DEBUG)

    instance   = OPParser (sys.argv[1])
    dictionary = instance.do_job("/home/bychoi/workspace/CLI/commands")
    if dictionary is None:
        trace.error (instance.get_error_string())
    else :
        for name in dictionary:
            trace.debug (json.dumps(name.get_pod_root(), indent=2))
    instance.parser_print()

if __name__ == '__main__':
    __test_main()

