import socket
import struct
import sys
import threading
import json
import time
from enum import Enum
from threading import Timer

# define types of messages
class Message(Enum):
    HEARTBEAT = 1
    LEADER = 2
    MESSAGE_REQUEST = 3
    MESSAGE = 4
    ELECTION = 5
    HIGHEST = 6
    ACK = 7

iamleader = False
memberlist = []
eyedie = 0
ip_leader = ""

def connect():
    # handles received messages in multicast
    recv_multi = threading.Thread(target=receive_multi, args=())
    recv_multi.start()    


def receive_multi():
    # globals
    global iamleader
    global eyedie
    global ip_leader
    global memberlist

    multicast_group = '224.3.29.71'
    server_address = ('', 10000)

    # Create the socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Bind to the server address
    sock.bind(server_address)

    # Tell the operating system to add the socket to the multicast group
    # on all interfaces.
    group = socket.inet_aton(multicast_group)
    mreq = struct.pack('4sL', group, socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    sock.settimeout(0.2)

    # handles output for chat members in console
    ui = threading.Thread(target=ui_function, args=(sock, ))
    ui.start()

    # Receive loop
    timeout = time.time() + 10 
    while True:
        try:
            data, address = sock.recvfrom(1024)
            jsonData = data.decode()
            print(jsonData)
            jsonData = json.loads(jsonData)

            if jsonData["type"] == "HEARTBEAT":
                sent = sock.sendto('{ "type": "ACK" , "data": ""}'.encode(), address)
            elif jsonData["type"] == "MESSAGE":
                memberlist = jsonData["data"]["memberlist"]
                eyedie = jsonData["data"]["id"]
            elif jsonData["type"] == "ELECTION" and jsonData["data"] == "no_hb":
                print("election")
                # TODO grund der election abfragen -> fehlender heartbeat oder 2 heartbeats??
                # handles election when multicast receives election message
                election = threading.Thread(target=elec_function, args=(address, sock, multicast_group))
                election.start()
            elif jsonData["type"] == "LEADER":
                #election.stop()
                #election.join()
                ip_leader = address
                print(ip_leader, " is the leader now")
                if iamleader:
                    # handles received messages in unicast (leoder only)
                    # will be started when member becomes leader
                    recv_uni = threading.Thread(target=receive_uni, args=(sock, multicast_group))
                    recv_uni.start()
                    #heartbeat = threading.Thread(target=heartbeat, args=(sock, multicast_group))
                    #heartbeat.start()
        except socket.timeout:
            pass
        if time.time() > timeout:
            sent = sock.sendto('{ "type": "ELECTION" , "data": "no_hb"}'.encode(), (multicast_group, 10000))

# only leader
def heartbeat(sock, multicast_group):
    global memberlist
    while True:
        # if ack -> nothing  
        sent = sock.sendto('{ "type": "HEARTBEAT", "data": [{ "memberlist":' + memberlist + ', "id": ' + eyedie + '}]}'.encode(), (multicast_group, 10000))
        memberlist = []  
        timeout = time.time() + 8   
        while True:
            if time.time() > timeout:
                break
            try:
                data, server = sock.recvfrom(16)
                jsonData = data.decode()
                jsonData = json.loads(jsonData)
                if jsonData["type"] == "ACK":
                    memberlist.append(server[0])
            except:
                pass


# only leader
def receive_uni(sock, multicast_group):
    # if message_request -> add id to message and send to multicast
    while True:
        hb = threading.Thread(target=heartbeat, args=(sock, multicast_group))
        hb.start()
        try:
            data, server = sock.recvfrom(1024)
            jsonData = data.decode()
            jsonData = json.loads(jsonData)
            if jsonData["type"] == "MESSAGE_REQUEST":
                eyedie += 1
                message = '{ "type": "MESSAGE", "data": [{ "id": ' + eyedie + ', "msg": ' + jsonData["data"] + ', "sender": ' + server[0] + '}]}'
                sent = sock.sendto(message.encode(), (multicast_group, 10000))
        except:
            pass


def ui_function(sock):
    print("Welcome to the P2P Chat!")
    print("Connecting...")
    while True:
        try: 
            message = input()
            sent = sock.sendto('{"type": "MESSAGE_REQUEST", "data": ' + message + '}'.encode(), ip_leader)
        except:
            pass
        try:
            data, server = sock.recvfrom(1024)
            jsonData = data.decode() 
            jsonData = json.loads(jsonData)
            if jsonData["type"] == "MESSAGE":
                print(jsonData["data"]["sender"], ": ", jsonData["data"]["msg"])
        except:
            pass


def elec_function(address, sock, multicast_group):
    higher = False
    if memberlist:
        for ip in memberlist:      
            if ip > socket.gethostname:
                higher = True
    if higher is True:
            pass
    else:
        sent = sock.sendto('{ "type": "HIGHEST", "data": ""}'.encode(), (multicast_group, 10000))
        timeout = time.time() + 10
        while True:
            try:
                data, address = sock.recvfrom(1024)
                jsonData = data.decode()
                jsonData = json.loads(jsonData)
                if jsonData["type"] == "HIGHEST":
                    higher = False
                    for ip in memberlist:      
                        if ip > socket.gethostname():
                            higher = True
                    if higher is True:
                        pass
                    else:
                        sent = sock.sendto('{ "type": "HIGHEST", "data": ""}'.encode(), (multicast_group, 10000))
                        timeout = time.time() + 10
                        while True:
                            try:
                                data, address = sock.recvfrom(1024)
                                jsonData = data.decode()
                                jsonData = json.loads(jsonData)
                                if jsonData["type"] == "HIGHEST":
                                    break
                                if time.time() > timeout:
                                    sent = sock.sendto('{ "type": "LEADER", "data": ""}'.encode(), (multicast_group, 10000))
                                    print("You are the leader now")
                                    iamleader = 1
                                    break
                            except socket.timeout:
                                pass
                if time.time() > timeout:
                    sent = sock.sendto('{ "type": "LEADER", "data": ""}'.encode(), (multicast_group, 10000))
                    print("You are the leader now")
                    iamleader = 1
                    break
            except socket.timeout:
                pass
                    


if __name__ == "__main__":
    connect()