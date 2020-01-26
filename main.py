#! /usr/bin/env python

import socket
import struct
import sys
import os
import argparse
import threading
import json
import time
import random
from enum import Enum
from threading import Timer

VERBOSITY = 0
VERBOSE = 4
DEBUG = 3
INFO = 2
WARN = 1
ERROR = 0
def debugPrint(verbosity, msg):
    if verbosity <= VERBOSITY:
        print("{}: {}".format(verbosity, str(msg)))

FETCHED_IP = None
def getOwnIp():
    global FETCHED_IP
    if FETCHED_IP:
        return FETCHED_IP
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    our_ip = s.getsockname()[0]
    debugPrint(VERBOSE, "My own ip is: {}".format(our_ip))
    FETCHED_IP = our_ip
    return FETCHED_IP

# define types of messages
class MessageType(Enum):
    HEARTBEAT = 1
    LEADER = 2
    MESSAGE_REQUEST = 3
    MESSAGE = 4
    ELECTION = 5
    HIGHEST = 6
    ACK = 7
    WELCOME = 8

# constants
HEARTBEAT_INTERVAL = 8
HEARTBEAT_TIMEOUT = 15
HEARTBEAT_TIMEOUT_JITTER = 5
HIGHEST_WRONG_JITTER = 3
HIGHEST_TIMEOUT = HEARTBEAT_TIMEOUT_JITTER * 1.5
PORT_UNICAST = 10000
PORT_MULTICAST = 20000
MULTICAST_ADDR = ('224.3.29.71', PORT_MULTICAST)
UNICAST_ADDR = ('', PORT_UNICAST)

# messages_to_be_printed = []

# globals
iamleader = False
memberlist = []
eyedie = 0
ip_leader = ""
heartbeat_died = False
receive_uni_died = False
multicast_group = "224.3.29.71"

# main method
# creates multicast socket & starts threads
def connect():
     # Create the socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Bind to the server address
    sock.bind(('', PORT_MULTICAST))

    # Tell the operating system to add the socket to the multicast group
    # on all interfaces.
    group = socket.inet_aton(multicast_group)
    mreq = struct.pack('4sL', group, socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    
    # handles received messages in multicast
    recv_multi = threading.Thread(target=receive_multi, args=(sock,))
    recv_multi.setName("receive_multi")
    recv_multi.start()

    # handles output for chat members in console
    ui = threading.Thread(target=ui_function, args=(sock,))
    ui.setName("ui")
    ui.start()
    ui.deamon = True

    recv_multi.join()

# sends a message of type to dest through sock with data
def send(sock, dest, type, data=None):
    # FIXME check types of arguments
    msg = {
        "type": type.name,
        "data": data,
    }
    debugPrint(VERBOSE, "Send to {}: {}".format(dest[0], msg))
    sock.sendto(json.dumps(msg).encode(), dest)

# receives and handles all multicast messages
def receive_multi(sock):
    # globals
    global iamleader
    global eyedie
    global ip_leader
    global memberlist

    sock.settimeout(HEARTBEAT_TIMEOUT + random.randrange(0, HEARTBEAT_TIMEOUT_JITTER))
    send(sock, MULTICAST_ADDR, MessageType.WELCOME)
    # Receive loop
    first_run = True
    while True: 
        try:
            global eyedie
            data, server = sock.recvfrom(1024)
            jsonData = data.decode()
            jsonData = json.loads(jsonData)
            msgType = jsonData["type"]
            if server[0] != ip_leader and msgType != MessageType.ELECTION.name:
                debugPrint(WARN, "Received multicast from {} when {} is the leader.".format(server[0], ip_leader))
            # heartbeat ack
            debugPrint(VERBOSE, "Got {} from {}".format(msgType, server[0]))
            if msgType == MessageType.HEARTBEAT.name:
                send(sock, server, MessageType.ACK)
                ip_leader = server[0]
                if not iamleader:
                    memberlist = jsonData["data"]["memberlist"]
                    eyedie = jsonData["data"]["id"]
            elif msgType == MessageType.WELCOME.name:
                print("Welcome, ", server[0])
            # start election process
            elif msgType == MessageType.ELECTION.name:
                print("election because of {}".format(jsonData["data"]))
                # handles election when multicast receives election message
                elec_function(sock)
                sock.settimeout(HEARTBEAT_TIMEOUT + random.randrange(0, HEARTBEAT_TIMEOUT_JITTER))
            # receive message 
            elif msgType == MessageType.MESSAGE.name:
                print_message(jsonData["data"]["sender"], jsonData["data"]["msg"])
                # messages_to_be_printed.append(jsonData)
            elif msgType == MessageType.LEADER.name:
                if iamleader:
                    continue
                elif first_run:
                    ip_leader = server[0]
                else:
                    raise BaseException("something wrong with leader") 
            elif msgType == MessageType.HIGHEST.name:
                if first_run:
                    elec_function(sock)
                    sock.settimeout(HEARTBEAT_TIMEOUT + random.randrange(0, HEARTBEAT_TIMEOUT_JITTER))
            else:
                raise BaseException("Wrong message type on multicast {}".format(msgType))
        except socket.timeout:
            if iamleader:
                continue
            send(sock, MULTICAST_ADDR, MessageType.ELECTION, data="no heartbeat")
            elec_function(sock)
            sock.settimeout(HEARTBEAT_TIMEOUT + random.randrange(0, HEARTBEAT_TIMEOUT_JITTER))
        first_run = False
    
# prints message to console
def print_message(sender, msg):
    print("{} says: {}".format(sender, msg))

# only leader
# sends heartbeat to multicast
def heartbeat(sock):
    print("heartbeat")
    global memberlist
    global eyedie
    global hb_died
    our_ip = getOwnIp()
    while iamleader:
        # if ack -> nothing 
        # FIXME maybe lock here
        # FIXME or buffer memberlist before clearing
        
        # Because multicast to own ip gets lost sometimes
        # Just add own ip anyway
        memberlist.append(our_ip)
        data = {
            "memberlist": list(set(memberlist)),
            "id":eyedie,
        }
        memberlist = []
        debugPrint(DEBUG, data)
        send(sock, MULTICAST_ADDR, MessageType.HEARTBEAT, data=data)
        time.sleep(HEARTBEAT_INTERVAL)
    hb_died = True


# only leader
# receives unicast messages
# handles acks and message_request
def receive_uni(sock):
    # TODO übergebe richtigen Socket
    print("receive uni")
    global receive_uni_died
    global memberlist
    # if message_request -> add id to message and send to multicast
    while iamleader:
        try:
            global eyedie
            data, server = sock.recvfrom(1024)
            jsonData = data.decode()
            jsonData = json.loads(jsonData)
            msgType = jsonData["type"]
            # send message to multicast
            if msgType == MessageType.MESSAGE_REQUEST.name:
                eyedie += 1
                data = {
                    "id": eyedie,
                    "msg": jsonData["data"],
                    "sender": server[0]
                }
                send(sock, MULTICAST_ADDR, MessageType.MESSAGE, data=data)
            # create memberlist
            elif msgType == MessageType.ACK.name:
                memberlist.append(server[0])
            else:
                raise BaseException("Wrong message type on unicast {}".format(msgType))
        except socket.timeout:
            pass
    receive_uni_died = True

# starts leader threads
# makes a new socket connection
def start_leader_thread():
    global hb_thread
    global receive_uni_died
    global heartbeat_died
    global receive_uni_thread
    # make sure leader is dead and there is no heartbeat
    if receive_uni_died and heartbeat_died:
        raise BaseException("the old leader threads should be dead")
    # TODO maybe join threads
    if not (iamleader):
        raise BaseException("That is unexpected")
    receive_uni_died = False
    heartbeat_died = False

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Bind to the server address
    sock.bind(('', PORT_UNICAST))

    # Tell the operating system to add the socket to the multicast group
    # on all interfaces.
    group = socket.inet_aton(multicast_group)
    mreq = struct.pack('4sL', group, socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    hb_thread = threading.Thread(target=heartbeat, args=(sock,))
    hb_thread.setName("heartbeat")
    hb_thread.start()
    receive_uni_thread = threading.Thread(target=receive_uni, args=(sock,))
    receive_uni_thread.setName("receive_uni")
    receive_uni_thread.start()

# stops leader threads aka unsets globals
def stop_leader_thread():
    global iamleader
    iamleader = False

# handles console input
def ui_function(sock):
    print("Welcome to the P2P Chat!")
    print("Connecting...")
    leader = None
    if ip_leader:
        leader = ip_leader
    print("Aktueller Leader: ", leader)
    while True:
        try: 
            message = input()
            print(ip_leader)
            send(sock, (ip_leader, 10000), MessageType.MESSAGE_REQUEST, data=message)
        except:
            pass


# compares IP addresses
def compareIP(ip1, ip2):
    ip1 = ip1.split(".")
    ip2 = ip2.split(".")
    ip1 = [int(i) for i in ip1]
    ip2 = [int(i) for i in ip2]
    if len(ip1) != len(ip2):
        raise BaseException("Length of IPs is not equal {} != {}".format(len(ip1), len(ip2)))
    for i in range(len(ip1)):
        if ip1[i] < ip2[i]:
            return -1
        elif ip1[i] > ip2[i]:
            return 1
    return 0

# handles messages receiving through sock connection
# This is called during election
def receive(sock):
    global memberlist
    while True:
        data, address = sock.recvfrom(1024)
        jsonData = data.decode()
        jsonData = json.loads(jsonData)
        msgType = jsonData["type"]
        debugPrint(VERBOSE, "Got {} from {}".format(msgType, address[0]))
        if compareIP(address[0], getOwnIp()) == 0:
            debugPrint(VERBOSE, "Got message from own ip. Skipping it")
            continue
        if msgType == MessageType.HIGHEST.name or msgType == MessageType.LEADER.name:
            break
        debugPrint(VERBOSE, "Ignoring {} from {} during election process.".format(msgType, address[0]))
        #FIXME adjust timeout to compensate that we received something
    memberlist.append(address[0])
    return (data, msgType, address[0])

# starts the voting algorithm
def elec_function(sock):
    global iamleader
    stop_leader_thread()
    if election(sock):
        iamleader = True
        start_leader_thread()

# voting algorithm
# Return True if we are the leader now
def election(sock):
    global iamleader
    global memberlist
    global ip_leader
    our_ip = getOwnIp()
    local_memberlist = memberlist
    current_highest = None
    sock.settimeout(HIGHEST_TIMEOUT)
    i = 0
    while True: # FIXME Maybe not endless...
        i += 1
        if i % 20 == 0:
            print("Election is taking very long. Consider pressing <c-c>")
        i_am_the_highest = True
        if local_memberlist:
            for ip in local_memberlist:
                if ip > our_ip:
                    i_am_the_highest = False
        if i_am_the_highest and current_highest == None:
            send(sock, MULTICAST_ADDR, MessageType.HIGHEST)
            current_highest = our_ip
            # TODO maybe wait a little bit less then highest timeout
            try:
                data, msgType, addr = receive(sock)
                if msgType == MessageType.HIGHEST.name:
                    if compareIP(addr, our_ip) == -1:
                        print("WTF. Someone didn't listen. I am the highest")
                        time.sleep(random.randrange(0,HIGHEST_WRONG_JITTER))
                        current_highest = None
                        local_memberlist = []
                    elif compareIP(addr, our_ip) == 1:
                        current_highest = addr
                        local_memberlist.append(addr)
                        continue
                    else:
                        print("WTF. Someone sent my ip...")
                elif msgType == MessageType.LEADER.name:
                    print("New leader {} found".format(addr))
                    ip_leader = addr
                    return False
                else:
                    raise BaseException("Expected HIGHEST got {}".format(msgType))
            except socket.timeout:
                #sent = sock.sendto('{ "type": "LEADER", "data": ""}'.encode(), (multicast_group, PORT))
                send(sock, MULTICAST_ADDR, MessageType.LEADER)
                print("You are the leader now")
                iamleader = True
                ip_leader = our_ip
                return True
        elif current_highest != None:
            try:
                data, msgType, addr = receive(sock)
                if msgType == MessageType.HIGHEST.name:
                    if compareIP(addr, current_highest) == -1:
                        print("WTF are you kiding me")
                        time.sleep(random.randrange(0,HIGHEST_WRONG_JITTER))
                        current_highest = None
                        local_memberlist = []
                    elif compareIP(addr, current_highest) == 1:
                        current_highest = addr
                        local_memberlist.append(addr)
                        continue
                    else:
                        print("WTF. Someone send highest twice...")
                elif msgType == MessageType.LEADER.name:
                    print("New leader {} found".format(addr))
                    ip_leader = addr
                    return False
                else:
                    raise BaseException("Expected HIGHEST got {}".format(msgType))
            except socket.timeout:
                local_memberlist = pop_highest(local_memberlist) # TODO
                current_highest = None
        else:
            try:
                data, msgType, addr = receive(sock)
                if msgType == MessageType.HIGHEST.name:
                    if compareIP(addr, our_ip) == -1:
                        send(sock, MULTICAST_ADDR, MessageType.HIGHEST)
                        current_highest = None
                        # TODO maybe wait a little bit less then highest timeout
                        try:
                            data, msgType, addr = receive(sock)
                            if msgType == MessageType.HIGHEST.name:
                                if compareIP(addr, our_ip) == -1:
                                    print("WTF. Someone didn't listen. I am the highest")
                                    local_memberlist = []
                                elif compareIP(addr, our_ip) == 1:
                                    current_highest = addr
                                    local_memberlist.append(addr)
                                    continue
                                else:
                                    #print("WTF. Someone send my ip...")
                                    continue
                            elif msgType == MessageType.LEADER.name:
                                print("New leader {} found".format(addr))
                                ip_leader = addr
                                return False
                            else:
                                raise BaseException("Expected HIGHEST got {}".format(msgType))
                        except socket.timeout:
                            #sent = sock.sendto('{ "type": "LEADER", "data": ""}'.encode(), (multicast_group, PORT))
                            send(sock, MULTICAST_ADDR, MessageType.LEADER)
                            print("You are the leader now")
                            iamleader = True
                            ip_leader = our_ip
                            return True
                        local_memberlist = []
                    elif compareIP(addr, our_ip) == 1:
                        current_highest = addr
                        local_memberlist.append(addr)
                        continue
                    else:
                        print("WTF. Someone send highest twice...")
                elif msgType == MessageType.LEADER.name:
                    # raise BaseException("Unlikely: New leader {} found".format(addr)) # This case is highly unlikely and may be an error state
                    # Adjust timeout to fix this case
                    ip_leader = addr
                    return False
                else:
                    raise BaseException("Expected HIGHEST got {}".format(msgType))
            except socket.timeout:
                local_memberlist = pop_highest(local_memberlist)
                current_highest = None
    if current_highest == our_ip:
        send(sock, MULTICAST_ADDR, MessageType.LEADER)
        print("You are the leader now")
        iamleader = True
        ip_leader = our_ip
        return True
    else:
        raise BaseException("No leader found")


# deletes highest member in list
def pop_highest(plist):
    if plist:
        plist.remove(max(plist))
    return plist

def main():
    global VERBOSITY
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', '-v', action='count', default=0)
    args = parser.parse_args()
    VERBOSITY = args.verbose
    if VERBOSITY:
        print("Verbose: {}".format(VERBOSITY))
    connect()

# main
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted")
        os._exit(1) # A bit ungraceful but it works
