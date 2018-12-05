#!/usr/bin/python3
import sys
import asyncio
import struct
import time
import logging
import socket
from JDIN import util
from JDIN import logger

trace = logging.getLogger(__name__)

JDIN_BASE_MSG_NAME_LOGIN     = 300
JDIN_BASE_MSG_NAME_HEARTBEAT = 301
JDIN_BASE_MSG_NAME_DATA      = 302
JDIN_BASE_MSG_NAME_DISP      = 303
JDIN_BASE_MSG_NAME_FAULT     = 304

JDIN_BASE_MSG_TYPE_REQ       = 1
JDIN_BASE_MSG_TYPE_RSP       = 2
JDIN_BASE_MSG_TYPE_RPT       = 3


class JDINTransportProtocol ():
    def __init__(self, reader, writer, addr=None):
        self.__istream     = reader
        self.__ostream     = writer
        if addr is None:
            self.__addr = writer.get_extra_info('peername')
        else :
            self.__addr = addr

    def get_addr (self):
        return self.__addr

    async def open (self):
        try :
            trace.debug ("info, try connection {0}".format(self.__addr))
            self.__istream, self.__ostream = \
                    await asyncio.open_connection (self.__addr[0],
                                                   self.__addr[1])
            trace.debug ("succ, transport connection {0}".format(self.__addr))
            return True
        except Exception as ex:
            trace.error ("fail, {0} open [name:{1}, args:{2}"  \
                         .format(self.__class__.__name__,       \
                                 type(ex).__name__, ex.args))
            return False


    def close (self):
        try:
            self.__ostream.close ()
            self.__istream  = None
            self.__ostream  = None
        except Exception as ex:
            trace.error ("fail, {0} close [name:{1}, args:{2}"  \
                         .format(self.__class__.__name__,       \
                                 type(ex).__name__, ex.args))

    async def recv (self):
        try :
            trace.debug ("info, wait packet")
            in_header   = None
            header_size = struct.calcsize('2sHILIhcc')
            in_header   = await self.__istream.readexactly(header_size)
            if not in_header:
                trace.error ("fail, {0} recv header from peer [{1}]"\
                            .format(self.get_addr(), in_header))
                return None

            trace.debug ("succ, {0} recv header from peer [{1}]"\
                        .format(self.get_addr(), in_header))

            total_size = struct.unpack('!H', in_header[2:4])[0]
            if total_size > header_size:
                body_size = total_size - header_size
                in_body   = None
                in_body   = await self.__istream.readexactly (body_size)
                if in_body is None:
                    trace.error ("fail, {0} recv body   from peer [{1}]"\
                            .format(self.get_addr(), in_body))
                    return None
                trace.debug ("succ, {0} recv body   from peer [{1}]"\
                        .format(self.get_addr(), in_body))
                return in_header + in_body
            else :
                return in_header

        except Exception as ex:
            trace.error ("fail, {0} recv bytes from peer [name:{0}, args:{1}"\
                       .format(self.get_addr(), type(ex).__name__, ex.args))
            return None


    async def send (self, out_bytes):
        try :
            self.__ostream.write (out_bytes)
            await self.__ostream.drain()
            trace.debug ("succ, {0} send bytes to peer [length({1}):{2}]"\
                         .format(self.get_addr(), len(out_bytes), out_bytes))
        except Exception as ex:
            trace.error ("fail, {0} send bytes from peer [name:{0}, args:{1}"\
                       .format(self.get_addr(), type(ex).__name__, ex.args))


class JDINBaseProtocolLogin():
    def __init__(self, raw_bytes=None):
        self.__raw_bytes     = raw_bytes
        self.__packet_format = 'III'
        self.__packet_size   = struct.calcsize(self.__packet_format)
        self.node_id         = 0
        self.block_id        = 0
        self.area_id         = 0

    def encode (self):
        try:
            self.__raw_bytes = None
            self.__raw_bytes = struct.pack(self.__packet_format, \
                                           self.node_id,
                                           self.block_id,
                                           self.area_id)
            trace.debug ("succ, login [node: {0}, block: {1}, area: {2}]"\
                        .format(self.node_id, self.block_id, self.area_id))
        except Exception as ex:
            trace.error ("fail, {0} encode [name:{1}, args:{2}"  \
                         .format(self.__class__.__name__,       \
                                 type(ex).__name__, ex.args))


    def decode (self):
        try :
            if len(self.__raw_bytes) != self.__packet_size :
                trace.error ("fail, invalid size [raw_bytes length:{0}, format length: {1}"\
                        .format(len(self.__raw_bytes) ,self.__packet_size))

                return False

            self.node_id, self.block_id, self.area_id = \
                    struct.unpack(self.__packet_format, self.__raw_bytes)
            trace.dbug ("succ, decode [node: {0}, block: {1}, area: {2}"\
                        .format(self.node_id, self.block_id, self.area_id))

            return True
        except Exception as ex:
            trace.error ("fail, {0} decode [name:{1}, args:{2}"  \
                         .format(self.__class__.__name__,       \
                                 type(ex).__name__, ex.args))
            return False

    def set_packet(self, node_id, block_id, area_id):
        self.node_id  = node_id
        self.block_id = block_id
        self.area_id  = area_id
        return self.encode ()

    def get_packet (self):
        return self.__raw_bytes


class JDINBaseProtocolHeartBeat():
    def __init__(self, raw_bytes = None):
        self.__raw_bytes = raw_bytes

    def encode (self):
        pass

    def decode (self):
        pass

    def request (self):
        pass

    def response (self):
        pass



class JDINBaseProtocolHeader ():
    def __init__(self, raw_bytes=None):
        self.raw_bytes= raw_bytes

        self.__header_format = '2sHILIhcc'
        self.__header_size   = struct.calcsize(self.__header_format)
        self.frame     = b'\xFE\xFE'
        self.total_len = None
        self.name      = None
        self.seq       = None
        self.gw        = None
        self.ret       = None
        self.version   = b'\x00'
        self.reserved  = b'\x00'

    def get_msg_type(self):
        return ((self.name >> 28) & 0x0F)


    def set_msg_type(self, mtype):
        return ((mtype & 0x0F) << 28)

    def get_msg_name(self):
        return (self.name & 0xFFFF)

    def set_msg_name(self, name):
        return (name & 0xFFFF)

    def get_msg_seq (self):
        if self.seq is None:
            self.seq = 1
        else :
            self.seq += 1
        return self.seq


    def encode (self):
        try:
            self.total_len = socket.htons(self.total_len)
            self.version  = b'\x00'
            self.reserved = b'\x00'

            self.raw_bytes  = struct.pack(self.__header_format,
                                        self.frame,
                                        self.total_len,
                                        self.name,
                                        self.seq,
                                        self.gw,
                                        self.ret,
                                        self.version,
                                        self.reserved)

            trace.debug ("succ, encode [len:{0}, name:{1}, seq:{2}, gw:{3}, ret:{4}]"\
                        .format(socket.ntohs(self.total_len),
                                hex(self.name),
                                self.seq,
                                self.gw,
                                self.ret))
        except Exception as ex:
            trace.error ("fail, {0} encode [name:{1}, args:{2}"\
                        .format(self.__class__.__name__,
                                type(ex).__name__, ex.args))



    def set_packet (self, mtype, name, gw, ret, body_length):
        self.name    = self.set_msg_name(name)
        self.name    = self.name | self.set_msg_type(mtype)

        if mtype == JDIN_BASE_MSG_TYPE_REQ:
            self.seq = self.get_msg_seq()
        self.gw      = gw
        self.ret     = ret
        self.total_len  = self.__header_size + body_length
        self.encode()

    def get_packet (self):
        return self.raw_bytes

    def decode (self, raw_bytes):
        try:
            self.raw_bytes = raw_bytes

            self.frame,     \
            self.total_len, \
            self.name,      \
            self.seq,       \
            self.gw,        \
            self.ret,       \
            self.version,   \
            self.reserved = struct.unpack(self.__header_format,
                                          self.raw_bytes)
            self.total_len = socket.ntohs(self.total_len)

            trace.debug ("succ, decode [len:{0} name:{1} seq:{2} gw:{3} ret:{4}]"
                        .format(self.total_len,
                                hex(self.name),
                                self.seq,
                                self.gw,
                                self.ret))
        except Exception as ex:
            trace.error ("fail, {0} decode [name:{1}, args:{2}"  \
                         .format(self.__class__.__name__,       \
                                 type(ex).__name__, ex.args))

class JDINBaseProtocol ():
    def __init__(self, raw_bytes = None):
        self.raw_bytes = raw_bytes
        # protocaol transport object
        self.__transport     = None
        self.header   = JDINBaseProtocolHeader()
        self.body     = None

    def set_transport (self, reader, writer, addr=None):
        self.__transport = JDINTransportProtocol(reader, writer, addr)


    def __set_packet (self, mtype, name, gw, ret, body=None):
        # set protocol body
        self.body = body

        # set protocol header
        body_length = 0
        if self.body:
            body_length = len(self.body)

        self.header.set_packet(mtype, name, gw, ret, body_length)
        self.raw_bytes = self.header.get_packet()
        if self.body:
            self.raw_bytes += self.body

    def get_packet (self):
        return self.raw_bytes

    async def open(self):
        await self.__transport.open()

    def close (self):
        self.__transport.close()

    async def send (self,mtype, name, gw, ret, body=None):
        try:
            self.__set_packet(mtype, name, gw, ret, body)
            await self.__transport.send(self.raw_bytes)
            return True
        except Exception as ex:
            trace.error ("fail,  send bytes [name:{0}, args:{1}"\
                       .format(type(ex).__name__, ex.args))
            return False

    async def recv (self):
        try:
            while True:
                self.raw_bytes = await self.__transport.recv()
                if not self.raw_bytes :
                    return False

                self.header.decode(self.raw_bytes)
                if self.header.get_msg_name() == JDIN_BASE_MSG_NAME_HEARTBEAT:
                    if self.header.get_msg_type() == JDIN_BASE_MSG_TYPE_REQ:
                        await self.send (2,
                                         self.header.name,
                                         self.header.gw,
                                         self.header.ret, None)
                        continue
                else :
                    break
            return True
        except Exception as ex:
            trace.error ("fail, {0} recv [name:{1}, args:{2}"  \
                         .format(self.__class__.__name__,       \
                                 type(ex).__name__, ex.args))
            return False


    '''
    async def do_server(self):
        if await self.recv() != True:
            return False

        e_code = False
        body   = None
        name   = self.get_msg_name()
        if name == JDIN_BASE_MSG_NAME_LOGIN:
            msg = JDINBaseProtocolLogin(self.body)
            e_code, body = msg.do_job()
            del msg
        elif name == JDIN_BASE_MSG_NAME_HEARTBEAT:
            pass
        elif name == JDIN_BASE_MSG_NAME_DATA:
            pass
        elif name == JDIN_BASE_MSG_NAME_DISP:
            pass
        elif name == JDIN_BASE_MSG_NAME_JSON:
            pass
        else :
            e_code = False
            body   = None

        await self.response (name, e_code, body)
        return True
    '''


class JDINTestServer ():
    def __init__(self, ip, port, loop):
        self.__event_loop  = loop
        self.__addr        = (ip, port)


    async def do_job (self, reader, writer):
        try :
            instance = None
            instance = JDINBaseProtocol (reader, writer)

            while True:
                await instance.do_server()

        except Exception as ex:
            trace.error ("fail, {0} [name:{1}, args:{2}"\
                       .format(self.__class__.__name__, type(ex).__name__, ex.args))
        finally :
            trace.critical ("info, disconnect peer [{0}]"\
                    .format(writer.get_extra_info('peername')))
            if instance is not None:
                instance.close()
                instance = None

    def run (self):
        self.__event_loop.run_until_complete (\
                asyncio.start_server(self.do_job,\
                self.__addr[0], self.__addr[1],             \
                loop=self.__event_loop))
        trace.critical ("succ, ({0},{1}) server startup complete"\
                        .format(self.__addr[0], self.__addr[1]))


def __test_main():
    trace.setLevel (logging.DEBUG)

    loop = asyncio.get_event_loop()
    server = JDINTestServer (None, 8990, loop)
    server.run()
    loop.run_forever()

if __name__ == '__main__':
    __test_main()
