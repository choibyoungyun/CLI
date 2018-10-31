#!/usr/bin/python3


import logging
import sys

trace = logging.getLogger(__name__)

class OPCommandParser ():
    def __init__(self, command_line):
        self.__command_terminator = ';'
        self.__name_delimiter     = ":"
        self.__para_separator     = ","
        self.__value_delimiter    = "="
        self.__command_line       = command_line
        self.__command_list       = list()
        self.__error_string       = ""
        self.__except_string      = ""

    def __parser_command_list (self):
        command_list = \
                [item.strip() for item \
                 in  self.__command_line.split(self.__command_terminator)]

        for token in command_list:
            command = dict()
            command['line'] = token.strip()
            self.__command_list.append (command)


    def __parser_command_line (self, command):
        """
        command = {'line'     : "command line",
                   'name'     : "name",
                   'parameter : {"field1" : "value1",
                                 "faile2" : "value2", ...}}
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
        if (len (tokens) > 1) and (self.__para_separator is not None) :
            parameter = dict()
            tokens = [item.strip() \
                      for item     \
                      in  tokens[1].split(self.__para_separator)]

            for item in tokens:
                try :
                    key, value = None, None
                    key, value = item.split(self.__value_delimiter)
                    parameter[key.lower()] = value
                except Exception as ex:
                    self.__error_string  = "fail, command parameter {0}"\
                                            .format(command['line'])
                    self.__except_string += "[exception [name:{0}, args:{1}]"\
                                            .format(type(ex).__name__, ex.args)
                    trace.error (self.__except_string)
                    return False
            command['parameter'] = parameter

        return True


    def parser_command (self):
        self.__parser_command_list ()
        for item in self.__command_list:
            if self.__parser_command_line (item) != True:
                return False
        return True

    def get_error_string (self):
        return self.__error_string

    def parser_print (self):
        trace.critical ("{0}".format (self.__command_list))


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

    instance = OPCommandParser (sys.argv[1])
    if instance.parser_command() != True:
        trace.error (instance.get_error_string())
    instance.parser_print()

if __name__ == '__main__':
    __test_main()

