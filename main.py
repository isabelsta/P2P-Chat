import socket
import struct
import sys
import threading
import json
import time
import random
from enum import Enum
from threading import Timer

# define types of messages
class MessageType(Enum):
    HEARTBEAT = 1
    LEADER = 2
    MESSAGE_REQUEST = 3
    MESSAGE = 4
    ELECTION = 5
    HIGHEST = 6
    ACK = 7

HEARTBEAT_INTERVAL = 8
HEARTBEAT_TIMEOUT = 15
HEARTBEAT_TIMEOUT_JITTER = 5
HIGHEST_TIMEOUT = HEARTBEAT_TIMEOUT_JITTER * 1.5
PORT_UNICAST = 10000
PORT_MULTICAST = 20000
MULTICAST_ADDR = ('224.3.29.71', PORT_MULTICAST)
UNICAST_ADDR = ('', PORT_UNICAST)

# messages_to_be_printed = []

iamleader = False
memberlist = []
eyedie = 0
ip_leader = ""
heartbeat_died = False
receive_uni_died = False
multicast_group = "224.3.29.71"

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
    recv_multi.start()
    # handles output for chat members in console
    ui = threading.Thread(target=ui_function, args=(sock,))
    ui.start()
    ui.deamon = True

    recv_multi.join()

def send(sock, dest, type, data=None):
    # FIXME check types of arguments
    msg = {
        "type": type.name,
        "data": data,
    }
    sock.sendto(json.dumps(msg).encode(), dest)

def receive_multi(sock):
    # globals
    global iamleader
    global eyedie
    global ip_leader
    global memberlist

    sock.settimeout(HEARTBEAT_TIMEOUT + random.randrange(0, HEARTBEAT_TIMEOUT_JITTER))

    # Receive loop
    while True:
        try:
            global eyedie
            data, server = sock.recvfrom(1024)
            jsonData = data.decode()
            jsonData = json.loads(jsonData)
            msgType = jsonData["type"]
            if server[0] != ip_leader and msgType != MessageType.ELECTION.name:
                print("Warning: Received multicast from {} when {} is the leader.".format(server[0], ip_leader))
            # heartbeat ack
            if msgType == MessageType.HEARTBEAT.name:
                send(sock, server, MessageType.ACK)
                memberlist = jsonData["data"]["memberlist"]
                eyedie = jsonData["data"]["id"]
            # start election process
            elif msgType == MessageType.ELECTION.name:
                print("election because of {}".format(jsonData["data"]))
                # handles election when multicast receives election message
                elec_function(sock)
                sock.settimeout(HEARTBEAT_TIMEOUT + random.randrange(0, HEARTBEAT_TIMEOUT_JITTER))
            # receive message 
            elif msgType == MessageType.MESSAGE.name:
                # TODO
                print_message(jsonData)
                # messages_to_be_printed.append(jsonData)
            elif msgType == MessageType.LEADER.name:
                if iamleader:
                    continue
                else:
                    raise BaseException("someone sent leader") 
            else:
                raise BaseException("Wrong message type on multicast {}".format(msgType))
        except socket.timeout:
            if iamleader:
                continue
            send(sock, MULTICAST_ADDR, MessageType.ELECTION, data="no heartbeat")
            #elec_function(sock)
            #sock.settimeout(HEARTBEAT_TIMEOUT + random.randrange(0, HEARTBEAT_TIMEOUT_JITTER))
    

def print_message(msg):
    print("message: {}".format(json.dumps(msg)))

# only leader
def heartbeat(sock):
    print("heartbeat")
    global memberlist
    global eyedie
    global hb_died
    while iamleader:
        # if ack -> nothing 
        # FIXME maybe lock here
        # FIXME or buffer memberlist before clearing
        #memberlist = []
        data = {
            "memberlist": memberlist,
            "id":eyedie,
        }
        print(data)
        send(sock, MULTICAST_ADDR, MessageType.HEARTBEAT, data=data)
        time.sleep(HEARTBEAT_INTERVAL)
    hb_died = True


# only leader
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
    hb_thread.start()
    receive_uni_thread = threading.Thread(target=receive_uni, args=(sock,))
    receive_uni_thread.start()

def stop_leader_thread():
    global iamleader
    iamleader = False

def ui_function(sock):
    print("Welcome to the P2P Chat!")
    print("Connecting...")
    while True:
        try: 
            message = input()
            send(sock, UNICAST_ADDR, MessageType.MESSAGE_REQUEST, data=message)
            #sent = sock.sendto('{"type": "MESSAGE_REQUEST", "data": ' + message + '}'.encode(), ip_leader)
        except:
            pass
        try:
            data, server = sock.recvfrom(1024)
            jsonData = data.decode() 
            jsonData = json.loads(jsonData)
            if jsonData["type"] == "MESSAGE":
                print(jsonData["data"]["sender"], ": ", jsonData["data"]["msg"])
        except socket.timeout:
            pass

# If ip1 < ip2: -1
# If ip1 = ip2: 0
# If ip1 > ip2: 1
def compareIP(ip1, ip2):
    if ip1 < ip2:
        return -1
    elif ip1 == ip2:
        return 0
    elif ip1 > ip2:
        return 1
    raise BaseException("Not yet implemented")

def receive(sock):
    global memberlist
    data, address = sock.recvfrom(1024)
    jsonData = data.decode() 
    data = json.loads(jsonData)
    msgType = data['type']
    memberlist.append(address[0])
    return (data, msgType, address[0])

def elec_function(sock):
    global iamleader
    stop_leader_thread()
    if election(sock):
        iamleader = True
        start_leader_thread()

# Return True if we are the leader now
def election(sock):
    global iamleader
    global memberlist
    global ip_leader
    our_name = socket.gethostname() 
    our_ip = socket.gethostbyname(our_name)
    local_memberlist = memberlist
    current_highest = None
    sock.settimeout(HIGHEST_TIMEOUT)
    i = 0
    while i < 5: # FIXME Maybe not endless...
        i += 1
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
                        local_memberlist = []
                    elif compareIP(addr, our_ip) == 1:
                        current_highest = addr
                        local_memberlist.append(addr)
                        continue
                    else:
                        print("WTF. Someone sent my ip...")
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
                    raise BaseException("Unlikely: New leader {} found".format(addr)) # This case is highly unlikely and may be an error state
                    # Adjust timeout to fix this case
                    ip_leader = addr
                    return False
                else:
                    raise BaseException("Expected HIGHEST got {}".format(msgType))
            except socket.timeout:
                local_memberlist = pop_highest(local_memberlist) # TODO
                current_highest = None
    if current_highest == our_ip:
        send(sock, MULTICAST_ADDR, MessageType.LEADER)
        print("You are the leader now")
        iamleader = True
        ip_leader = our_ip
        return True


def pop_highest(plist):
    plist.remove(max(plist))
    return plist

if __name__ == "__main__":
    connect()