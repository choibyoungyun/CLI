#!/usr/bin/env python3

import asyncio
import os
import sys
import logging
import time

from JDIN import config
from JDIN import logger
from JDIN import BaseProtocol

trace = logging.getLogger(__name__)


class Tester():
    def __init__(self, ip, port):
        self.tcase         = dict()
        self.__addr        = (ip, port)
        self.__base        = BaseProtocol.JDINBaseProtocol()
        self.__event_loop  = asyncio.get_event_loop()


    def load_tcase (self, fname):
        handle = config.ConfigFile()
        handle.open (fname)
        handle.load ()
        self.tcase = handle.get_dictionary ()

    def print_tcase(self):
        for section in self.tcase.keys():
            for option in self.tcase[section].keys():
                if self.tcase[section][option].startswith("0x") :
                    self.tcase[section][option] \
                            = int(self.tcase[section][option],16)
                trace.debug ("{0}: {1} : {2}"\
                        .format(section, option, self.tcase[section][option]))

    def get_message_request(self):
        return self.__base.get_packet()

    async def send(self):
        return await self.__base.send()

    async def recv(self):
        return await self.__base.recv()

    async def open(self):
        self.__base.set_transport(None, None, self.__addr)
        await self.__base.open()

    def close(self):
        self.__base.close()

    async def send_message_request(self, packet):
        field = self.tcase['MESSAGE']
        return await self.__base.send (1, int(field['msg_name']),
                                       int(field['gw_route']),
                                       int(field['return']),
                                       packet)


    async def request_login (self):
        try:
            field = self.tcase['LOGIN']
            login = BaseProtocol.JDINBaseProtocolLogin()
            login.set_packet (int(field['node_id']),
                              int(field['block_id']),
                              int(field['area_id']))
            await self.__base.send(1,300,0,0, login.get_packet())

            await self.__base.recv()
            return True
        except Exception as ex:
            trace.error ("fail, {0} [name:{1}, args:{2}"  \
                         .format(self.__class__.__name__,
                                 type(ex).__name__, ex.args))
            return False

    async def __run_client (self, packet):
        try:
            await self.open()

            if await self.request_login() != True:
                self.stop_client()
                return False

            await self.send_message_request (packet)
            await self.recv()
        except Exception as ex:
            trace.error ("fail, {0} [name:{1}, args:{2}"  \
                         .format(self.__class__.__name__, \
                                 type(ex).__name__, ex.args))

    def run_client (self, packet):
        self.__event_loop.run_until_complete(self.__run_client(packet))


    def stop_client (self):
        self.__event_loop.stop()
        self.__event_loop.close()

    async def __run_server (self, reader, writer):
        try :
            self.set_transport(reader, writer)
            if await self.__base.do_login() is not True:
                return False
            else:
                await self.send_message_request ("/home/bychoi/tsuit/tcase.in")
        except Exception as ex:
            trace.error ("fail, {0} [name:{1}, args:{2}"\
                       .format(self.__class__.__name__, type(ex).__name__,\
                               ex.args))
        finally :
            pass

    def run_server (self):
        self.__event_loop.run_until_complete (\
                asyncio.start_server(self.__run_server,\
                self.__addr[0], self.__addr[1],             \
                loop=self.__event_loop))
        trace.critical ("succ, ({0},{1}) server startup complete"\
                        .format(self.__addr[0], self.__addr[1]))

