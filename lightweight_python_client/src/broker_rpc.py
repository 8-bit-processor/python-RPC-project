#!/usr/bin/env python3

#
# LICENSE:
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License version 3 (AGPL)
# as published by the Free Software Foundation.
# (c) 2010-2011 caregraf.org
#

"""
 Broker Connection

 Module to provide access to VistA RPCs through either the new style
 VA Broker or IHS's CIA Broker. It provides thread-safe access through a Pool
 class.

 Base Connection for VistA and CIA Brokers with specializations for the
 particulars of those brokers.

brokerRPC3.py was started to provide Python 3 support

"""

__author__ = 'Caregraf'
__copyright__ = "Copyright 2010-2011, Caregraf"
__credits__ = ["Sam Habiel", "Jon Tai", "Andy Purdue",
               "Jeff Apple", "Ben Mehling", "Vernon Oberholzer"]
__license__ = "AGPL"
__version__ = '0.9'
__status__ = "Development"

import re
import socket
from random import randint
import queue

class RPCConnection(object):
    """
    Hardcoded in VistA/RPMS access code.
    """
    CIPHER = ["***************  Place the decryption code here  ***********************"]


    def __init__(self, host, port, access, verify, context, logger,
                 endMark, poolId):
        if logger:
            self.logger = logger
        else:
            self.logger = RPCLogger()
        self.host = host
        self.port = port
        self.access = access
        self.verify = verify
        self.context = context
        self.endMark = endMark
        self.poolId = poolId
        self.sock = None

    def invokeRPC(self, name, params):
        if not self.sock:
            self.logger.logInfo("RPCConnection",
                                "Connecting %d as Socket not initialized" % self.poolId)
            self.connect()
        e = None
        try:
            request = self.makeRequest(name, params)
            self.logger.logInfo("RPCConnection", f"Request: {request}")
            self.sock.send(request.encode('utf-8'))
            msg = self.readToEndMarker()
        except socket.error as e:
            print(e)
            msg = ""
        if not len(msg):
            error_message = "empty reply"
            self.logger.logInfo("RPCConnection",
                                "Forced to reconnect connection %d after reply \
                                failed (%s))" % (self.poolId, error_message))
            self.connect()
            request = self.makeRequest(name, params)
            self.logger.logInfo("RPCConnection", f"Request: {request}")
            self.sock.send(request.encode('utf-8'))
            msg = self.readToEndMarker()
        return msg

    def connect(self):
        if self.sock:
            self.sock.close()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        self.logger.logInfo("RPCConnection", "Connecting to %s %d - Step1 for\
        %d ..." % (self.host, self.port, self.poolId))

    def encrypt(cls, val):
        ra = randint(0, 18)
        rb = randint(0, 18)
        while ((rb == ra) or (rb == 0)):
            rb = randint(0, 18)
        cra = RPCConnection.CIPHER[ra]
        crb = RPCConnection.CIPHER[rb]
        cval = chr(ra + 32)
        for i in range(len(val)):
            c = val[i]
            index = cra.find(c)
            if index == -1:
                cval += str(c)
            else:
                cval += str(crb[index])
        cval += chr(rb + 32)
        return cval.encode("utf-8")

    def readToEndMarker(self):
        msgChunks = []
        noChunks = 0
        msg = ""
        while 1:
            msgChunk = self.sock.recv(256)
            msgChunk = msgChunk.decode('utf-8')
            if not msgChunk:
                break
            if not len(msgChunks):
                if msgChunk[0] == "\x00":
                    msgChunk = msgChunk[2:]
            noChunks += 1
            if msgChunk[-1] == self.endMark:
                msgChunks.append(msgChunk[:-1])
                break
            msgChunks.append(msgChunk)
        if len(msgChunks):
            msg = "".join(msgChunks)
        self.logger.logInfo("RPCConnection", "Message of length %d received in \
        %d chunks on connection %d" % (len(msg), noChunks, self.poolId))
        return msg

    def close(self):
        if self.sock:
            self.sock.send("#BYE#".encode('utf-8'))
            self.sock.close()

class VistARPCConnection(RPCConnection):

    def __init__(self, host, port, access, verify, context, logger, poolId=-1):
        RPCConnection.__init__(self, host, port, access, verify, context,
                               logger, chr(4), poolId)

    def connect(self):
        RPCConnection.connect(self)
        tcpConnect = self.makeRequest("TCPConnect",
                                      [socket.gethostbyname(socket.gethostname
                                                            ()), "0", "FMQL"], True)
        self.sock.send(tcpConnect.encode('utf-8'))
        connectReply = self.readToEndMarker()
        if not re.match(r'accept', connectReply):
            raise Exception("VistARPCConnection", connectReply)
        signOn = self.makeRequest("XUS SIGNON SETUP", [])
        self.sock.send(signOn.encode('utf-8'))
        connectReply = self.readToEndMarker()
        accessVerify = self.encrypt(self.access + ";" + self.verify)
        accessVerify = accessVerify.decode()
        login = self.makeRequest("XUS AV CODE", [accessVerify])
        self.sock.send(login.encode('utf-8'))
        connectReply = self.readToEndMarker()
        if re.search(r'Not a valid ACCESS CODE/VERIFY CODE pair',
                     connectReply):
            raise Exception("VistARPCConnection", connectReply)
        eMSGCONTEXT = self.encrypt(self.context)
        eMSGCONTEXT = eMSGCONTEXT.decode()
        ctx = self.makeRequest("XWB CREATE CONTEXT", [eMSGCONTEXT])
        self.sock.send(ctx.encode('utf-8'))
        connectReply = self.readToEndMarker()
        self.logger.logInfo("CONNECT", "context reply is %s" % connectReply)
        if re.search(r'Application context has not been created',
                     connectReply) or\
                     re.search(r'does not exist on server', connectReply):
            raise Exception("VistARPCConnection", connectReply)
        self.logger.logInfo("VistARPCConnection",
                            "Handshake complete for connection %d" % self.poolId)

    def makeRequest(self, name, params, isCommand=False):
        protocoltoken = "[XWB]1130"
        if isCommand:
            commandtoken = "4"
        else:
            commandtoken = "2" + chr(1) + "1"
        namespec = chr(len(name)) + name
        paramsspecs = "5"
        if not len(params):
            paramsspecs += "4" + "f"
        else:
            for param in params:
                if type(param) is not dict:
                    paramsspecs += "0"
                    paramsspecs += str(len(param)).zfill(3) + str(param)
                    paramsspecs += "f"
                else:
                    paramsspecs += "2"
                    paramIndex = 1
                    for key, val in list(param.items()):
                        if paramIndex > 1:
                            paramsspecs += "t"
                        paramsspecs += str(len(str(key))).zfill(3) + str(key)
                        paramsspecs += str(len(str(val))).zfill(3) + str(val)
                        paramIndex += 1
                    paramsspecs += "f"
        endtoken = chr(4)
        return protocoltoken + commandtoken + namespec + paramsspecs + endtoken


class CIARPCConnection(RPCConnection):

    def __init__(self, host, port, access, verify, context, logger, poolId=-1):
        RPCConnection.__init__(self, host, port, access, verify, context,
                               logger, chr(255), poolId)
        self.sequence = 0
        self.uid = ""

    def connect(self):
        RPCConnection.connect(self)
        uci = ""
        myAddress = "NOTVALID"
        self.logger.logInfo("CIACONNECT", "Sending CIA Connect")
        ciaConnect = self.__makeCIARequest("C", {"IP": myAddress, "UCI": uci,
                                                 "DBG": "0", "LP": "0", "VER": "1.6.5.26"})
        self.sock.send(ciaConnect.encode('utf-8'))
        connectReply = self.readToEndMarker()
        self.logger.logInfo("CIACONNECT", "STEP 1 SUCCESS: " + connectReply)
        accessVerify = self.encrypt(self.access + ";" + self.verify)
        computerName = socket.gethostname()
        self.uid = ""
        ciaConnect = self.makeRequest("CIANBRPC AUTH", ["CIAV VUECENTRIC",
                                                        computerName, "", accessVerify])
        self.sock.send(ciaConnect.encode('utf-8'))
        connectReply = self.readToEndMarker()
        replyLines = connectReply.split("\r")
        if not (len(replyLines) > 1 and re.match(r'\d+\\^', replyLines[1])):
            eMsg = "STEP 2 FAIL"
            self.logger.logError("CIACONNECT", eMsg)
            raise Exception("CIACONNECT", eMsg)
        self.uid = re.match(r'([^\\^]+)', replyLines[1]).group(1)
        self.logger.logInfo("CIACONNECT", "STEP 2 SUCCESS - Connected. UID %s" % self.uid)

    def makeRequest(self, rpcName, params):
        rpcParams = {"CTX": self.context, "UID": self.uid, "VER": "0", "RPC": rpcName}
        for i in range(len(params)):
            rpcParams[str(i+1)] = params[i]
        return self.__makeCIARequest("R", rpcParams)

    def __makeCIARequest(self, rtype, params):
        headerToken = "{CIA}"
        EODToken = chr(255)
        self.sequence += 1
        if self.sequence == 256:
            self.sequence = 1
        sequence = chr(self.sequence)
        if rtype == "R":
            brtype = chr(82)
        else:
            brtype = chr(67)
        paramsspecs = ""
        for paramId, paramValue in params.items():
            paramsspecs += self.__byteIt(paramId) + chr(0) + self.__byteIt(paramValue)
        return headerToken + EODToken + sequence + brtype + paramsspecs + EODToken

    def __byteIt(self, strVal):
        slen = len(strVal)
        low = slen % 16
        slen = slen >> 4
        bytes = bytearray()
        highCount = 0
        while slen != 0:
            bytes.append(slen & 0xFF)
            slen = slen >> 8
            highCount += 1
        fbytes = bytearray()
        fbytes.append((highCount << 4) + low)
        for idx in reversed(range(0, len(bytes))):
            fbytes.append(bytes[idx])
        fbytes.extend(bytearray(strVal))
        return fbytes

import queue

class RPCConnectionPool:

    def __init__(self, brokerType, poolSize, host, port, access,
                 verify, context, logger):
        self.logger = logger
        self.__connectionQueue = queue.LifoQueue()
        self.__prebuildConnections(brokerType, poolSize, host, port,
                                   access, verify, context)

    def __prebuildConnections(self, brokerType, poolSize, host, port,
                              access, verify, context):
        for i in range(poolSize, 0, -1):
            if brokerType == "CIA":
                connection = CIARPCConnection(host, port, access,
                                              verify, context, self.logger, i)
            else:
                connection = VistARPCConnection(host, port, access,
                                                verify, context, self.logger, i)
            self.__connectionQueue.put(connection)
        self.logger.logInfo("CONN POOL", "Initialized %d connections" % poolSize)
        self.poolSize = poolSize

    def invokeRPC(self, name, params):
        connection = self.__connectionQueue.get()
        try:
            reply = connection.invokeRPC(name, params)
        except Exception as e:
            self.logger.logError("CONN POOL", "Basic connectivity problem.\
            Connection was refused so RPC invocation failed.")
            raise e
        self.__connectionQueue.put(connection)
        return reply

    def preconnect(self, number):
        if number > self.poolSize:
            number = self.poolSize
        connections = []
        for i in range(number):
            connection = self.__connectionQueue.get()
            connection.connect()
            connections.append(connection)
        for i in range(number):
            self.__connectionQueue.put(connections[i])

import threading

class ThreadedRPCInvoker(threading.Thread):
    def __init__(self, pool, requestName, requestParameters):
        threading.Thread.__init__(self)
        self.pool = pool
        self.requestName = requestName
        self.requestParameters = requestParameters

    def run(self):
        print("Sending another request ...")
        reply = self.pool.invokeRPC(self.requestName, self.requestParameters)
        print(("First part of reply: %s" % (reply[0:50],)))

class RPCLogger:
    def __init__(self, logger=None):
        self.logger = logger

    def logInfo(self, tag, msg):
        if self.logger:
            self.logger(f"BROKERRPC -- {tag} {msg}")
        else:
            print(f"BROKERRPC -- {tag} {msg}")

    def logError(self, tag, msg):
        if self.logger:
            self.logger(f"BROKERRPC -- {tag} {msg}")
        else:
            print(f"BROKERRPC -- {tag} {msg}")

import getopt, sys
import json
import time

def query_test(conn):
    rpc = input("Enter RPC: ")
    params = input("Enter params: ")
    params = params.strip()
    reply = conn.invokeRPC(rpc.strip(), list(params.split()))
    print(reply)

def main_test():
    opts, args = getopt.getopt(sys.argv[1:], "")
    if len(args) < 1:
        print("Enter <host> <port> <access> <verify>")
        return

    CONNECTION = VistARPCConnection(args[0], int(args[1]),
                                    args[2], args[3], "XUPROGMODE",
                                    RPCLogger())
    MENUCHOICE = {'q': query_test, 'e': exit}
    menu = '''
    Main Menu
    (Q)uery
    (E)xit
    Enter choice: '''

    while True:
        while True:
            try:
                choice = input(menu).strip()[0].lower()
            except (EOFError, KeyboardInterrupt, IndexError):
                choice = 'e'

            print('\nYou picked: [%s]' % choice)
            if choice not in 'qe':
                print('Invalid option, try again')
            else:
                break

        if choice == 'e':
            break
            exit(0)
        MENUCHOICE[choice](conn=CONNECTION)
    
def main():
    opts, args = getopt.getopt(sys.argv[1:], "")
    if len(args) < 0:
        print("Enter <host> <port> <access> <verify>")
        return

    connection = VistARPCConnection("host", 9297,
                                    "ACCESS", "VERIFY", "XUPROGMODE",
                                    RPCLogger())
    reply = connection.invokeRPC("ORWPT ID INFO", ["2"])
    print("reply is of type: %s" % (type(reply),))
    print(reply)
    reply = connection.invokeRPC("XWB EGCHO STRING",["Hello"])
    print(reply)

if __name__ == "__main__":
    main_test()
