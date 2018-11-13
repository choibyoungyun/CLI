#!/usr/bin/python3

import asyncio
import json
import logging
import time
import signal
import os
import sys
import re
from JDIN.CLI import pod
from JDIN.CLI import ems
from JDIN     import util
from abc import *

trace = logging.getLogger(__name__)

COD_CMD_DICTIONARY_PATH = os.environ['PKG_ROOT'] + "/config/command/"
COD_CMD_FILE_SUFFIX     = ".json"
COD_CMD_INTERNAL_LIST   =['help', 'set-rpt-mode']


class CLIHelp ():
    def __init__(self):
        pass

    def help_list (self, dictionary):
        path      = os.path.dirname(dictionary.get_pod_fname())
        file_list = os.listdir (path)
        file_list.sort()

        response  = dictionary.get_pod_response_body()
        short = response['BRIEF']

        for file in file_list:
            # only usef alpha prefix file name
            if not re.match('^[a-zA-Z]', file) :
                continue

            sub_fname = path.rstrip('/')+'/'+ file
            sub_dic   = pod.CommandDictionary()
            sub_dic.set_pod_fname(sub_fname)
            sub_dic.open_pod()
            brief = sub_dic.get_pod_help_brief ()

            short.append ({'NAME':file.split('.')[0], 'DESC':brief})

        # delete template value
        del short[0]
        output = dictionary.get_pod_display_help_brief ()
        return output

    def __get_command_fname (self, dictionary, name):
        path  = os.path.dirname(dictionary.get_pod_fname())
        fname = path.rstrip('/') + '/' + name.lower() + ".json"

        if os.path.exists(fname) is True:
            return fname

        fname = path.rstrip('/') + '/' + name.upper() + ".json"
        if os.path.exists (fname) is True:
            return fname
        return None

    def help_detail (self, dictionary, fname):
        cmd_dict = pod.CommandDictionary ()
        cmd_dict.set_pod_fname (fname)
        cmd_dict.open_pod ()

        output = cmd_dict.get_pod_display_help()
        if output is None:
            dictionary.set_pod_error_string(cmd_dict.get_pod_error_string())
            return None

        response = dictionary.get_pod_response_body()
        response ['DETAIL'] = output
        output = dictionary.get_pod_display_help_detail()
        return output


    def do_job (self, dictionary):
        parameter = dictionary.get_pod_request_body()
        if parameter is None:
            return None

        if 'COMMAND' in parameter.keys():
            fname = self.__get_command_fname (dictionary, parameter['COMMAND'])
            if fname is not None:
                output = self.help_detail (dictionary, fname)
            else :
                output="undefined command [{0}]".format(parameter['COMMAND'])
        else :
            output = self.help_list (dictionary)

        return output

class CLIClient ():
    def __init__(self):
        self.__path          = COD_CMD_DICTIONARY_PATH
        self.__suffix        = COD_CMD_FILE_SUFFIX
        self.__key           = 0
        self.__cmd_system    = None
        self.__trace_system  = None
        self.__report_system = None
        self.__help          = CLIHelp()

    def __del__(self):
        pass

    @abstractmethod
    def open  (self): pass
    @abstractmethod
    def close (self): pass
    @abstractmethod
    async def recv  (self): pass
    @abstractmethod
    async def send  (self): pass
    @abstractmethod
    def get_addr (self): pass

    def set_command_system (self, server):
        self.__cmd_system    = server

    def set_trace_system (self, server):
        self.__trace_system  = server

    def set_report_system (self, server):
        self.__report_system = server

    def set_trace_on (self):
        self.__trace_system.insert_client (self)

    def set_trace_off (self):
        self.__trace_system.delete_client (self)

    def set_report_on (self):
        self.__report_system.insert_client (self)

    def set_report_off (self):
        self.__report_system.delete_client (self)

    def get_report_status (self):
        try :
            if self.__report_system.select_client (self) == True:
                return "ON"
            else:
                return "OFF"
        except Exception as ex:
            trace.error (ex)


    def internal_exception (self, ex, return_value=False, help = None):
        err_string = "fail, {0} internal exception : {1}"\
                .format(self.get_addr(), ex)
        return return_value, err_string

    def set_path (self, dirname):
        self.__path = dirname

    def get_path (self):
        return (self.__path)

    def set_suffix (self, suffix):
        self.__suffix = suffix

    def get_suffix (self):
        return self.__suffix


    def __get_key (self):
        self.__key += 1
        return (self.__key)

    def __set_cmd_result (self, code, name, value):
        result = dict()
        result['code']  = code
        result['key']   = name
        result['value'] = value
        trace.debug ("info, {0} cmd result {1}"\
                .format (self.get_addr(),result))
        return result

    def __set_cmd_response (self, command_dict, err_string = None):
        try :
            if err_string is None:
                result = command_dict.get_pod_display_response()
                if result is None:
                    result = command_dict.get_pod_error_string()
                return self.__set_cmd_result (\
                        command_dict.get_pod_response_result(),   \
                        command_dict.get_pod_response_key(),   \
                        result)
            else :
                return self.__set_cmd_result (999, \
                                      command_dict.get_pod_response_key(),\
                                      err_string)
        except Exception as ex :
            err = "fail, {0} internal exception : {1}".format(ex)
            trace.error (err)
            return self.__set_cmd_result (999, 1, err)

    def __set_cmd_request (self, command_dict):
        try:
            key = command_dict.get_pod_request_key()
            command_dict.set_pod_response_key(key)
            command_dict.set_pod_request_key (self.__get_key())
            return True, None
        except Exception as ex :
            err = "fail, {0} internal exception : {1}".format(ex)
            trace.error (err)
            return False, err


    async def  __internal_command_report (self, dictionary):
        try :
            request = dictionary.get_pod_request_body()
            if request['MODE'].lower() == "on":
                self.set_report_on()
                response = dictionary.get_pod_response_body()
                response['MESSAGE'] = self.get_report_status()
                dictionary.set_pod_response_result(0)
            elif request['MODE'].lower() == "off":
                self.set_report_off()
                response = dictionary.get_pod_response_body()
                response['MESSAGE'] = self.get_report_status()
                dictionary.set_pod_response_result(0)
            else :
                dictionary.set_pod_response_result(1)
                dictionary.set_pod_error_string ("UNKNONW MODE")

            result = self.__set_cmd_response (dictionary)
            await self.send (result)
        except Exception as ex:
            trace.error (ex)

    async def  __internal_command_help (self, dictionary):
        try :
            output = ""
            output = self.__help.do_job(dictionary)
            if output is None:
                output = dictionary.get_error_string()
            result = self.__set_cmd_result (0, 0, output)
            await self.send (result)
        except :
            pass

    async def __internal_command (self, dictionary):
        command_name = dictionary.get_pod_name()
        if  command_name.lower () == 'help':
            await self.__internal_command_help (dictionary)
        elif command_name.lower() == 'set-rpt-mode':
            await self.__internal_command_report (dictionary)
        else:
            result = self.__set_cmd_result (999, 1, "info, undefined command")
            await self.send (result)

    async def __forward_command (self, request_dict):
        try:
            e_code, err = self.__set_cmd_request (request_dict)
            if e_code is not True:
                return self.__set_cmd_result (999, \
                                              request_dict.get_pod_request_key(),\
                                              err)
            e_code, err_string = \
                    await self.__cmd_system.send (request_dict, self)
            if e_code is not True:
                trace.debug (err_string)
                result = self.__set_cmd_result (999, 1, err_string)
                await self.send (result)
        except Exception as ex :
            return None

    async def response(self, dictionary):
        try :
            result = None
            result = self.__set_cmd_response (dictionary)
            trace.debug (result)
            await self.send (result)
        except Exception as ex:
            trace.error(json.dumps(dictionary.get_pod_root(), indent=2))
            err_string = "fail, {0} notify exception [name:{0}, args:{1}"\
                    .format(self.get_addr(), type(ex).__name__, ex.args)
            trace.error (err_string)
            await self.send (self.__set_cmd_result (999, 999, err_string))

    async def run (self):
        """
        name   : run
        param  : command client object
        return : value
        desc   : process client command
        """
        try :
            while True:
                commands = await self.recv()
                trace.debug ("info, {0} command pod instance [{1}]"\
                        .format (self.get_addr(), commands))
                if commands is None:
                    break

                for command in commands:
                    command.set_pod_node(self.get_addr())
                    if command.get_pod_scope() != 0:
                        await self.__internal_command (command)
                    else :
                        await self.__forward_command (command)

        except Exception as ex:
            trace.error ("fail, {0} run [{1}]".format(self.get_addr(),ex))
