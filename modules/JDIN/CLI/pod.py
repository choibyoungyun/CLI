#!/usr/bin/python3

# ------------------------------------------------------------------------
# MODULE NAME : POD (PRINT OUT DESCRIPTION)
# ------------------------------------------------------------------------

import json
import logging
import time
import os

trace = logging.getLogger(__name__)

"""
DISPLAY JSON KEYWORD
"""
# -------------------------------------------------------------------
# SECTION KEYWORD
# -------------------------------------------------------------------
POD_KEYWORD_COMMAND     = 'command'
POD_KEYWORD_REQUEST     = 'request'
POD_KEYWORD_RESPONSE    = 'response'
POD_KEYWORD_HEADER      = 'header'
POD_KEYWORD_BODY        = 'body'
POD_KEYWORD_DISPLAY     = 'display'
POD_KEYWORD_SUCCESS     = 'success'
POD_KEYWORD_FAILURE     = 'failure'
POD_KEYWORD_HELP_BRIEF  = 'help_brief'
POD_KEYWORD_HELP_DETAIL = 'help_detail'

# -------------------------------------------------------------------
# DISPLAY KEYWORD
# -------------------------------------------------------------------
POD_KEYWORD_COMMENT     = 'comment'
POD_KEYWORD_LINE        = 'line'
POD_KEYWORD_TABLE       = 'table'
POD_KEYWORD_NAME        = 'name'
POD_KEYWORD_FORMAT      = 'format'
POD_KEYWORD_VALUE       = 'value'

# -------------------------------------------------------------------
# value operartor
# -------------------------------------------------------------------
POD_KEYWORD_DEFAULT          = 'default'

# casting data type
POD_KEYWORD_VALUE_TYPE       = 'type'
POD_KEYWORD_VALUE_STRING      = 'string'
POD_KEYWORD_VALUE_INTEGER     = 'int'
POD_KEYWORD_VALUE_FLOAT       = 'float'

# madatory filed
POD_KEYWORD_MANDATORY        = 'mandatory'
POD_KEYWORD_CONSTRAINTS      = 'constraints'
POD_KEYWORD_CONSTRAINTS_ENUM = 'enum'
POD_KEYWORD_CONSTRAINTS_MIN  = 'min'
POD_KEYWORD_CONSTRAINTS_MAX  = 'max'


# -------------------------------------------------------------------
# value delimiter
# -------------------------------------------------------------------
POD_VALUE_SEPARATOR   = ","


class CommandDictionary ():
    def __init__ (self, fname = None):
        self.__node         = None
        self.__root         = dict()
        self.__fname        = None
        self.__error_string = ""
        if fname is not None:
            try:
                self.open_pod()
            except Exception as ex:
                self.__error_string += "[exception [name:{0}, args:{1}]"\
                                        .format(type(ex).__name__, ex.args)
                trace.error (self.__error_string)

    # -------------------------------------------------------------------
    #  COMMAND LINE API
    # -------------------------------------------------------------------
    def get_pod_fname  (self) :
        return self.__fname
    def set_pod_fname  (self, filename):
        self.__fname = filename


    def open_pod (self):
        # load dict from JSON
        try :
            with open(self.__fname, 'r') as f:
                lines = None
                lines = f.readlines()

                data = ""
                for line in lines:
                    data += line.strip()
                self.__root = json.loads(data)
            return True
        except Exception as ex :
            self.__error_string += "fail, open command file [{0}]"\
                                   .format(self.__fname)
            self.__error_string += "[exception [name:{0}, args:{1}]"\
                                    .format(type(ex).__name__, ex.args)
            return False


    def set_pod_node (self, nodename):
        self.__node = nodename

    def get_pod_root (self):
        return self.__root

    def set_pod_root (self, root):
        self.__root = root

    def get_pod_name (self):
        return self.__root['name']

    def set_pod_scope (self, scope):
        self.__root['scope'] = scope

    def get_pod_scope (self):
        if 'scope' not in self.__root.keys():
            return 0
        else :
            return self.__root['scope']

    def set_pod_command (self, command):
        self.__root[POD_KEYWORD_COMMAND] = command

    def get_pod_command (self):
        return self.__root[POD_KEYWORD_COMMAND]

    # -------------------------------------------------------------------
    #  ERROR STRING API
    # -------------------------------------------------------------------
    def reset_pod_error_string (self):
        self.__error_string = ""

    def set_pod_error_string (self, err_string):
        self.__error_string += err_string

    def get_pod_error_string (self):
        return self.__error_string

    # -------------------------------------------------------------------
    #  HELP API
    # -------------------------------------------------------------------
    def get_pod_help (self):
        pass

    def get_pod_help_brief (self):
        if POD_KEYWORD_HELP_BRIEF in self.__root [POD_KEYWORD_DISPLAY].keys():
            return self.__root [POD_KEYWORD_DISPLAY][POD_KEYWORD_HELP_BRIEF]
        else:
            return "NONE"

    # -------------------------------------------------------------------
    #  REQUEST API
    # -------------------------------------------------------------------
    def get_pod_request (self):
        return self.__root[POD_KEYWORD_REQUEST]
    def get_pod_request_key (self):
        return self.__root[POD_KEYWORD_REQUEST][POD_KEYWORD_HEADER]['Key']
    def set_pod_request_key (self, key):
        self.__root[POD_KEYWORD_REQUEST][POD_KEYWORD_HEADER]['Key'] = key
    def get_pod_request_body (self):
        try :
            return self.__root[POD_KEYWORD_REQUEST][POD_KEYWORD_BODY]
        except Exception as ex:
            self.set_pod_error_string ("[exception [name:{0}, args:{1}]"\
                                       .format(type(ex).__name__, ex.args))
            return None
    def get_pod_request_raw (self):
        return self.__root['raw_request']
    def set_pod_request_raw (self, message):
        self.__root['raw_request'] = message



    def __check_request_constraint (self, template, key, value):
        error_string = ""
        if POD_KEYWORD_CONSTRAINTS not in template[key].keys():
            return True

        constraint_dict = template[key][POD_KEYWORD_CONSTRAINTS]
        if POD_KEYWORD_CONSTRAINTS_ENUM in constraint_dict.keys():
           constraints = [item.strip() \
                          for item  in \
                          constraint_dict[POD_KEYWORD_CONSTRAINTS_ENUM]\
                          .split(POD_VALUE_SEPARATOR)]
           if value not in constraints:
                error_string = \
                        "fail, invalid constraint value [{0}:{1}, enum:{2}]"\
                             .format(key, value, constraints)
                self.set_pod_error_string (error_string)
                return False

        if POD_KEYWORD_CONSTRAINTS_MIN in constraint_dict.keys():
            constraint = constraint_dict[POD_KEYWORD_CONSTRAINTS_MIN]
            if type(constraint) is "str":
                constraint = constraint.strip()
            else :
                constraint = str(constraint)

            if value < constraint:
                error_string = \
                        "fail, invalid constraint value [{0}:{1}, min:{2}]"\
                             .format(key, value, constraint)
                self.set_pod_error_string (error_string)
                return False

        if POD_KEYWORD_CONSTRAINTS_MAX in constraint_dict.keys():
            constraint = constraint_dict[POD_KEYWORD_CONSTRAINTS_MAX]
            if type(constraint) is "str":
                constraint = constraint.strip()
            else :
                constraint = str(constraint)

            if value > constraint:
                error_string = \
                        "fail, invalid constraint value [{0}:{1}, max:{2}]"\
                             .format(key, value, constraint)
                self.set_pod_error_string (error_string)
                return False

        return True


    def __set_pod_request_value (self, template, key, value):
        error_string = ""
        try :
            if self.__check_request_constraint (template, key, value) is False:
                return False

            vtype = None
            vtype = template[key]['type']
            if vtype == "int" :
                template[key] = int(value)
            elif vtype == "float":
                template[key] = float(value)
            else :
                template[key] = value
            return True
        except Exception as ex:
            error_string = "exception : name:{0}, args:{1}"\
                            .format(type(ex).__name__, ex.args)
            if type(ex).__name__ == "ValueError":
                error_string += \
                  "fail, invalid argument type [arg:{0}, vtype:{1}, value:{2}]"\
                  .format(key, vtype, value)
            self.set_pod_error_string (error_string)
            return False

    def set_pod_request  (self, in_dict):
        e_code     = True
        err_string = ""
        value      = None
        template   = self.__root[POD_KEYWORD_REQUEST][POD_KEYWORD_BODY]
        remove_key = list()

        for key in template.keys():
            if POD_KEYWORD_MANDATORY in template[key].keys() \
                    and \
               template[key][POD_KEYWORD_MANDATORY].lower() == "TRUE".lower():
                if key.lower() not in in_dict.keys()                \
                        or in_dict[key.lower()] is None \
                        or len (in_dict[key.lower()]) is 0 :
                    err_string = \
                        "fail, required mandatory value [{0}]".format(key)
                    self.set_pod_error_string (err_string)
                    return False
                else:
                    value = in_dict[key.lower()]
                    e_code = self.__set_pod_request_value (template, key, value)
            else:
                if key.lower() not in in_dict.keys():
                    if POD_KEYWORD_DEFAULT in template[key].keys():
                        template[key] = template[key][POD_KEYWORD_DEFAULT]
                    else :
                        remove_key.append(key)
                else :
                    value = in_dict[key.lower()]
                    if value is not None:
                        e_code = self.__set_pod_request_value (template, \
                                                               key, value)
                    else :
                        remove_key.append(key)

            if e_code is not True:
                return False

        for rkey in remove_key:
            del self.__root[POD_KEYWORD_REQUEST][POD_KEYWORD_BODY][rkey]

        return True


    # -------------------------------------------------------------------
    #  RESPONSE API
    # -------------------------------------------------------------------
    def get_pod_response (self):
        return self.__root[POD_KEYWORD_RESPONSE]
    def set_pod_response(self, response):
        self.__root[POD_KEYWORD_RESPONSE] = response
    def set_pod_response_key (self, key):
        self.__root[POD_KEYWORD_RESPONSE][POD_KEYWORD_HEADER]['Key'] = key
    def set_pod_response_result (self, result):
        try :
            self.__root[POD_KEYWORD_RESPONSE][POD_KEYWORD_HEADER]['result'] = result
        except Exception as ex:
            trace.error (ex)
    def get_pod_response_key (self):
        return self.__root[POD_KEYWORD_RESPONSE][POD_KEYWORD_HEADER]['Key']
    def get_pod_response_body (self):
        return self.__root[POD_KEYWORD_RESPONSE][POD_KEYWORD_BODY]
    def get_pod_response_result (self):
        try :
            return self.__root[POD_KEYWORD_RESPONSE][POD_KEYWORD_HEADER]['result']
        except :
            return self.__root[POD_KEYWORD_RESPONSE][POD_KEYWORD_HEADER]['Result']
    def get_pod_response_raw (self):
        return self.__root['raw_response']
    def set_pod_response_raw (self, message):
        self.__root['raw_response'] = message


    # -------------------------------------------------------------------
    #  NOTIFICATION API
    # -------------------------------------------------------------------
    def __set_pod_notify_value (self, dictionary, in_value):
        try :
            value = None
            if in_value is None:
                if type (dictionary) is dict:
                    if POD_KEYWORD_DEFAULT in dictionary.keys():
                        value = dictionary[POD_KEYWORD_DEFAULT]
                    else :
                        self.__error_string += \
                                "fail, undefined notification key in msg"
                        trace.error (self.__error_string)
                        return None
            else :
                value = in_value

            if type (dictionary) is dict :
                if POD_KEYWORD_VALUE_TYPE in dictionary.keys():
                    field_type = dictionary[POD_KEYWORD_VALUE_TYPE]
                    if field_type.lower() == POD_KEYWORD_VALUE_STRING:
                        return str(value)
                    elif field_type.lower() == POD_KEYWORD_VALUE_INTEGER:
                        return int(value)
                    elif field_type.lower() == POD_KEYWORD_VALUE_FLOAT:
                        return float(value)
                    else:
                        return value
            return value
        except Exception as ex:
            self.__error_string += \
                    "fail, set notification value {0}".format(in_value)
            self.__error_string += "[exception [name:{0}, args:{1}]"\
                                    .format(type(ex).__name__, ex.args)
            trace.error (self.__error_string)
            return None



    def __set_pod_notify_table (self, template, src):
        dictionary = template[0]
        dest       = list()
        try:
            for row in src:
                item = dict()
                for key in dictionary.keys():
                    value = None
                    if key is row.keys():
                        value = row[key]
                    item[key] = self.__set_pod_notify_value (dictionary[key],
                                                             value)
                    if item[key] is None:
                        return None
                dest.append(item)
            return dest
        except Exception as ex:
            self.__error_string += "fail, set notification table"
            self.__error_string += "[exception [name:{0}, args:{1}]"\
                                    .format(type(ex).__name__, ex.args)
            trace.error (self.__error_string)
            return None


    def set_pod_notify  (self, notification):
        template = self.get_pod_response_body()
        in_dict  = notification[POD_KEYWORD_BODY]

        try :
            for key in template.keys():
                if key in in_dict.keys():
                    if type(in_dict[key]) is list:
                        lvalue = None
                        lvalue = self.__set_pod_notify_table (template[key],\
                                                              in_dict[key])
                        if lvalue is None:
                            return False
                        template[key] = lvalue
                    else:
                        template[key] = \
                                self.__set_pod_notify_value (template[key],
                                                             in_dict[key])
                else :
                    template[key] = \
                            self.__set_pod_notify_value (template[key],
                                                         None)
                if template[key] is None:
                    return False
            return True
        except Exception as ex:
            self.__error_string += "fail, set notification"
            self.__error_string += "[exception [name:{0}, args:{1}]"\
                                    .format(type(ex).__name__, ex.args)
            trace.error (self.__error_string)
            return False


    # -------------------------------------------------------------------
    #  DISPLAY API
    # -------------------------------------------------------------------
    def __get_reserved_value (self, keyword):
        """
        name   : __get_reserved_value
        param  : keyword      (keyword string
        return : value
        """
        if keyword == "$TIME":
            return time.asctime(time.localtime())
        elif keyword == "$NODE_NAME":
            return self.__node
        elif keyword == "$RAW_RESPONSE":
            return self.get_pod_response_raw()
        elif keyword == "$RAW_REQUEST":
            return self.get_pod_request_raw()
        elif keyword == "$COMMAND":
            return self.get_pod_command()
        elif keyword == "$ERROR":
            return self.__error_string()
        else:
            return "NULL"




    def __get_key_value (self, root_values, key_list, row_num=0):
        """
        name   : get_key_value
        param  : response_dict (response json dictionary),
                 key_list      (json key list)
                 row_num       (json array index. only used array type)
        return : json value
        """
        key   = key_list[0].strip()
        value = root_values[key]
        if type(value) is dict:
            del key_list[0]
            return self.__get_key_value (value, key_list, row_num)
        elif type(value) is list:
            value = value[row_num]
            del key_list[0]
            return self.__get_key_value (value, key_list, row_num)
        else :
            return value


    def __get_line_values (self, root_values, output_format, output_value, row_num = 0):
        value_list= list()
        for value in output_value.split(POD_VALUE_SEPARATOR):
            value = value.strip()
            if value[0] == '$':
                value_list.append (self.__get_reserved_value (value))
            else :
                value_list.append (self.__get_key_value (root_values,value.split('.'), row_num))

        return output_format.format(*value_list)


    def __get_table_values (self, out_format, root_values):
        result_string   = ""
        line_delimiter  = None

        # get table row outformat && out values
        key = None
        key = [s for s in list(out_format.keys()) \
                if s.startswith(POD_KEYWORD_LINE) is True]
        if not key :
            return "fail, pod temlate file. not found table line keyword"
        o_format = out_format[key[0]][POD_KEYWORD_FORMAT]
        o_value  = out_format[key[0]][POD_KEYWORD_VALUE]

        # get table row comment value 
        key = None
        key = [s for s in list(out_format.keys()) \
                if s.startswith(POD_KEYWORD_COMMENT) is True]
        if key :
            line_delimiter = out_format[key[0]]

        # get value's object from table name
        # ex) body.table_name -> root_value['body']['table_name]
        table_values = root_values
        for key in out_format[POD_KEYWORD_NAME].strip().split('.'):
            table_values = table_values[key];

        row_num = 0
        for line in table_values:
            result_string += self.__get_line_values (root_values, o_format, o_value, row_num)
            if line_delimiter:
                result_string += line_delimiter
            row_num += 1
        return result_string



    def __get_pod_template (self, cond_value):
        if cond_value == 0:
            return self.__root[POD_KEYWORD_DISPLAY][POD_KEYWORD_SUCCESS]
        elif cond_value == 999:
            return self.__root[POD_KEYWORD_DISPLAY][POD_KEYWORD_HELP_DETAIL]
        else :
            return
        self.__root[POD_KEYWORD_DISPLAY][POD_KEYWORD_FAILURE]



    def __get_object_values (self, now_template, pod_object):
        pod_string=""
        trace.debug ('POD TEMPLATE: {0}'\
                     .format (json.dumps(now_template,indent=2)))
        trace.debug ('POD VALUES  : {0}'\
                   .format (json.dumps(self.get_pod_response_body(),indent=2)))
        try :
            for key in now_template.keys():
                if key.startswith(POD_KEYWORD_COMMENT):
                    #'COMMENT' KEYWORD PROCESSING
                    pod_string += now_template[key]
                elif key.startswith (POD_KEYWORD_LINE):
                    #'LINE' KEYWORD PROCESSING
                    pod_string += \
                    self.__get_line_values ( \
                            pod_object,              \
                            now_template[key][POD_KEYWORD_FORMAT],\
                            now_template[key][POD_KEYWORD_VALUE],0)
                elif key.startswith (POD_KEYWORD_TABLE):
                    #'TABLE' KEYWORD PROCESSING
                    pod_string += \
                    self.__get_table_values (now_template[key], pod_object)

            trace.debug ('POD STRING (last): {0}'.format (pod_string))
            return pod_string
        except Exception as ex:
            self.set_pod_error_string ("fail, [{}]".format(ex))
            return None

    def get_pod_display_response (self):
        if self.get_pod_response_result() == 0:
            template = \
            self.__root[POD_KEYWORD_DISPLAY][POD_KEYWORD_SUCCESS]
        else :
            template = \
            self.__root[POD_KEYWORD_DISPLAY][POD_KEYWORD_FAILURE]

        pod_object = self.get_pod_root()
        return self.__get_object_values (template, pod_object)

    def get_pod_display_help (self):
        template = \
        self.__root[POD_KEYWORD_DISPLAY][POD_KEYWORD_HELP_DETAIL]
        pod_object = self.get_pod_root()
        return self.__get_object_values (template, pod_object)

    def get_pod_display_help_detail (self):
        template = \
        self.__root[POD_KEYWORD_DISPLAY]['detail']
        pod_object = self.get_pod_root()
        return self.__get_object_values (template, pod_object)

    def get_pod_display_help_brief (self):
        template = \
        self.__root[POD_KEYWORD_DISPLAY]['brief']
        pod_object = self.get_pod_root()
        return self.__get_object_values (template, pod_object)

    def validate_pod_request (self, request):
        template = self.__root[POD_KEYWORD_REQUEST][POD_KEYWORD_BODY]
        try :
            for key in template.keys():
                if key not in request.keys():
                    raise KeyError

                if type (template [key]) == type("str"):
                    template[key] = request[key]
                else :
                    template[key] = (int)(request[key])
            return True, template
        except KeyError:
            return False, "undefined argument {}".format(key)
        except Exception as ex:
            return False, "fail,{0}".format(ex)

