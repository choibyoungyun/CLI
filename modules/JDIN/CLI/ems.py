#!/usr/bin/python3

import asyncio
import logging
import json
import struct
from abc import *
from JDIN import util
from JDIN.CLI import pod

trace = logging.getLogger(__name__)
EMS_MAX_NOTI_PUSH_LEN    = 4096
EMS_MAX_CMD_RESPONSE_LEN = 4096

class EMSProtocol ():
    def __init__(self, ip, port):
        self.__addr        = (ip, port)
        self.__istream     = None
        self.__ostream     = None
        self.__is_connectd = False

    def __internal_exception (self, ex, return_value = False):
        err_string = "fail, {0} internal exception : {1}"\
                    .format(self.get_addr(), ex)
        trace.error (err_string)
        return return_value, err_string

    def get_addr (self):
        return self.__addr

    async def open  (self):
        try :
            self.__istream, self.__ostream = \
                    await asyncio.open_connection (self.__addr[0],
                                                   self.__addr[1])
            self.__is_connectd = True
            return True
        except :
            return False

    def close (self):
        try:
            self.__ostream.close ()
            self.__istream  = None
            self.__ostream  = None
            self.__is_connectd = False
        except Exception as ex:
            trace.error (ex)

    async def recv (self):
        try :
            in_bytes = await self.__istream.readexactly(8)
            if not in_bytes:
                trace.error ("fail, {0} recv bytes from EMS (disconect)"\
                            .format(self.get_addr()))
                self.__is_connectd = False
                return None, None
            in_bytes, = struct.unpack("8s",in_bytes)
            len = int(in_bytes)
            trace.debug ("succ, {0} recv bytes from EMS [{1},length({2})]"\
                    .format(self.get_addr(), in_bytes, len))

            in_bytes = await self.__istream.readexactly (len)
            if in_bytes is None:
                trace.error ("fail, {0} recv bytes from EMS (disconect)"\
                            .format(self.get_addr()))
                self.__is_connectd = False
                return None, None
            trace.debug ("succ, {0} recv bytes from EMS [{1}]"\
                    .format(self.get_addr(), in_bytes))
            return in_bytes.decode(), None
        except Exception as ex:
            trace.error ("fail, {0} recv bytes from EMS [name:{0}, args:{1}"\
                       .format(self.get_addr(), type(ex).__name__, ex.args))
            return None, None


    async def send (self, msg):
        try :
            if self.__is_connectd is False:
                return False, "fail, not connect server"

            out_bytes = msg.encode()
            self.__ostream.write (out_bytes)
            await self.__ostream.drain()
            trace.debug ("succ, {0} send request to EMS CMD [{1}]"\
                         .format(self.get_addr(), out_bytes))
            return True, None
        except Exception as ex:
            return self.__internal_exception(ex, None)


class EMSClient ():

    def __init__(self, ip, port, server_type = "COMMAND"):
        self.__type     = server_type
        self.__addr     = (ip, port)
        self.__protocol = EMSProtocol(ip, port)
        self.__key      = 0
        self.__queue    = util.PendingQueue()

        self.__pod      = pod.CommandDictionary()
        self.__clients  = set()

    def __get_key (self):
        self.__key += 1
        return (self.__key)

    def __internal_exception (self, ex, return_value = False):
        err = "fail, {0} internal exception : {1}"\
                .format(self.get_addr(), ex)
        trace.error (err)
        return return_value, err

    def get_addr (self):
        return self.__addr

    async def open (self):
        try :
            e_code = await self.__protocol.open()
            if e_code is True:
                trace.info ("succ, connect to server ({0})"\
                             .format(self.get_addr()))
            else :
                trace.error ("fail, connect to server ({0})"\
                             .format(self.get_addr()))
            return e_code
        except Exception as ex:
            return False

    def close (self):
        self.__protocol.close()


    async def recv (self):
        in_string, err = await self.__protocol.recv()
        if in_string is None:
            return self.__internal_exception(err, None)

        try :
            msg = json.loads(in_string)
            rkey = msg ['header']['Key']
            try :
                index, item = self.__queue.select (rkey)
            except Exception as ex:
                return self.__internal_exception(ex, None)

            if item is None :
                trace.error ("fail, {0} not found req   [key:{0}]"\
                            .format(self.get_addr(), rkey))
                trace.error ("fail, {0} discard message [key:{0}]"\
                            .format(self.get_addr(), rkey))
            else:
                e_code, err = self.__queue.delete (index)
                if e_code is not True:
                    return self.__internal_exception (err, None)
                else :
                    key = item['value']['dictionay'].get_pod_response_key()
                    item ['value']['dictionay'].set_pod_response_raw (\
                            json.dumps(msg, indent=2))
                    item ['value']['dictionay'].set_pod_response (msg)
                    item ['value']['dictionay'].set_pod_response_key (key)

            return item, None
        except Exception as ex:
            return self.__internal_exception(ex, None)


    async def send (self, command_dict, client):
        """
        desc : send json message to EMS COMMAND SERVER
        param: msg [dictionary]
        """
        try :
            #
            # store message for transaction
            #
            key = self.__get_key()
            item = dict()
            item['key']   = key
            item['value'] = {'client':client, 'dictionay':command_dict}
            e_code, err_string = self.__queue.insert (item)
            if e_code is not True:
                return self.__internal_exception (err_string, False)

            command_dict.set_pod_request_key(key)
            msg = command_dict.get_pod_request()
            command_dict.set_pod_request_raw(json.dumps(msg, indent=2))
            e_code, err_string = await self.__protocol.send (json.dumps(msg))
            if e_code != True:
                index, err = self.__queue.select (key)
                self.__queue.delete(index)
            return e_code, err_string
        except Exception as ex:
            return self.__internal_exception(ex, False)

    def insert_client (self, client):
        self.__clients.add(client)

    def delete_client (self, client):
        try :
            self.__clients.remove(client)
        except :
            pass

    def select_client (self, client):
        try :
            now = set([client])
            if len (now & self.__clients) > 0:
                return True
            else:
                return False
        except Exception as ex:
            trace.error (ex)

    async def __handle_command  (self):
        trace.critical ("info, {0} startup {1} handle"\
                .format (self.get_addr(), self.__type))
        try :
            while True:
                item, err = await self.recv ()
                client    = item['value']['client']
                dictionay = item['value']['dictionay']

                await client.response (dictionay)
        except Exception as ex:
            pass


    def __do_verify_notify (self, dest, template):
        for key in dest.keys():
            if key in template.keys():
                continue
            if template[key]['default'] in template[key].keys():
                desc[key] = template[key]['default']

    async def __do_notify (self, in_string):
        msg        = None
        fname      = None
        client     = None
        try:
            for client in self.__clients:
                msg = json.loads(in_string)
                fname = client.get_path() \
                        + str(msg['header']['CmdID']) + ".json"
                trace.debug ("info, notify pod fname [{0}]".format(fname))
                self.__pod.set_pod_fname (fname)
                e_code = self.__pod.open_pod()
                if e_code is not True:
                    trace.error ("fail, {0} do_notify [{1}]"\
                                .format(self.get_addr(),    \
                                self.__pod.get_pod_error_string()))
                    return
                self.__pod.set_pod_node (self.get_addr())
                e_code = self.__pod.set_pod_notify (msg)
                trace.debug (self.__pod.get_pod_root())
                if e_code is not True:
                    trace.error ("fail, {0} do_notify [{1}]"\
                                .format(self.get_addr(),    \
                                self.__pod.get_pod_error_string()))
                    return

                await client.response (self.__pod)
        except Exception as ex:
            trace.error ("fail, {0} notify exception [name:{0}, args:{1}"\
               .format(self.get_addr(), type(ex).__name__, ex.args))

    async def __handle_notify  (self):
        trace.critical ("info, {0} startup {1} handle"\
                .format (self.get_addr(), self.__type))
        try :
            while True:
                in_string = None
                in_string, err = await self.__protocol.recv()
                if in_string is None:
                    break
                trace.info ("info, {0} recv notify {1}"\
                            .format(self.get_addr(), in_string))
                await self.__do_notify(in_string)
                self.__pod.reset_pod_error_string()
        except Exception as ex:
            trace.error ("fail, {0} notify exception [name:{0}, args:{1}"\
               .format(self.get_addr(), type(ex).__name__, ex.args))


    async def start_client (self):
        try:
            while True:
                e_code = await self.open()
                if e_code != True:
                    await asyncio.sleep (1.0)
                    continue
                if self.__type == "COMMAND":
                    await self.__handle_command ()
                else :
                    await self.__handle_notify ()
                self.close()
                continue
        except Exception as ex:
            pass


