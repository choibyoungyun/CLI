#!/usr/bin/env python3
import sys
import asyncio
import struct
import logging
from JDIN import util
from JDIN import logger


trace = logging.getLogger(__name__)


class JDINIPCProtocolHeader():
    def __init__(self, raw_bytes=None):
        self.raw_bytes         = raw_bytes

        self.__header_format   = '!HHIIIIcc2s'
        self.__header_size     = struct.calcsize(self.__header_format)
        self.length            = 0
        self.signal_id         = 0
        self.source_node       = 0
        self.destination_node  = 0
        self.source_block      = 0
        self.destination_block = 0
        self.source_area       = 0
        self.destination_area  = 0

    def encode (self):
        try:
            self.raw_bytes  = struct.pack(self.__header_format,
                                     self.length,
                                     self.signal_id,
                                     self.source_node,
                                     self.source_block,
                                     self.destination_node,
                                     self.destination_block,
                                     self.source_area.to_bytes(1, 'big'),
                                     self.destination_area.to_bytes(1, 'big'),
                                     b'\x00\x00')

            trace.debug ("succ, encode [length: {0}, signal:{1}, snode:{2}, dnode:{3},sblock:{4}, dblock:{5}]"\
                        .format(self.length, hex(self.signal_id), \
                                self.source_node, self.destination_node,
                                self.source_block, self.destination_block))
            return True

        except Exception as ex:
            trace.error ("fail, {0} [name:{1}, args:{2}"  \
                         .format(self.__class__.__name__, \
                                 type(ex).__name__, ex.args))
            return False

    def decode (self):
        try:
            self.length,
            self.signal_id,
            self.source_node,
            self.source_block,
            self.destination_node,
            self.destination_block,
            self.source_area,
            self.destination_area,
            self.reserved = struct.unpack(self.__header_format,
                                          self.raw_bytes[0:self.__header_size])
            return True
        except Exception as ex:
            trace.error ("fail, {0} [name:{1}, args:{2}"
                         .format(self.__class__.__name__, type(ex).__name__, ex.args))
            return False

    def set_packet (self, signal_id,
                          source_node,  destination_node,
                          source_block, destination_block,
                          source_area,  destination_area,
                          body_length):

        self.length            = self.__header_size + body_length
        self.signal_id         = signal_id
        self.source_node       = source_node
        self.destination_node  = destination_node
        self.source_block      = source_block
        self.destination_block = destination_block
        self.source_area       = source_area
        self.destination_area  = destination_area
        self.encode()

    def get_packet(self):
        return self.raw_bytes


class JDINIPCProtocol ():
    def __init__(self, raw_bytes=None):
        self.raw_bytes  = raw_bytes
        self.header     = JDINIPCProtocolHeader()
        self.body       = None

    def encode (self):
        self.raw_bytes = self.header.get_packet()
        if self.body:
            self.raw_bytes += self.body


    def set_packet (self, signal_id,
                          source_node,  destination_node,
                          source_block, destination_block,
                          source_area,  destination_area,
                          body=None):
        # set protocol body
        self.body = body

        # set protocol header
        body_length = 0
        if self.body:
            body_length = len(self.body)
        self.header.set_packet (signal_id,
                                source_node,  destination_node,
                                source_block, destination_block,
                                source_area,  destination_area,
                                body_length)
        self.encode()

    def get_packet(self):
        return self.raw_bytes
