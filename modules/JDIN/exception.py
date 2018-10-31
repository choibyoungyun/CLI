#!/usr/bin/python3

import logging

trace = logging.getLogger(__name__)

def internal_exception (ex, return_value = False):
    err_string = "fail, {0} internal exception : {1}"\
                 .format(self.get_addr(), ex)
    trace.error (err_string)
    return return_value, err_string

