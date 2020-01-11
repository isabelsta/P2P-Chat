import socket
import struct
import sys
import threading
import json
from enum import Enum

# define types of messages
class Message(Enum):
    HEARTBEAT = 1
    LEADER = 2
    MESSAGE_REQUEST = 3
    MESSAGE = 4
    ELECTION = 5
    HIGHEST = 6
    ACK = 7

iamleader = 0
memberlist = []
eyedie = 0
ip_leader = ""

def connect():
    # handles received messages in multicast
    recv_multi = threading.Thread(target=receive_multi, args=())
    recv_multi.start()    


def receive_multi():
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

    # handles output for chat members in console
    ui = threading.Thread(target=ui_function, args=(sock))
    ui.start()

    # Receive loop
    while True:
        data, address = sock.recvfrom(1024)
        jsonData = data.decode()

        if jsonData.type == HEARTBEAT:
            sent = sock.sendto('{ "type": "ACK" , "data": ""}'.encode(), address)
        elif jsonData.type == LEADER:
            election.exit()
            ip_leader = address
            if iamleader:
                # handles received messages in unicast (leoder only)
                # will be started when member becomes leader
                recv_uni = threading.Thread(target=receive_uni, args=(sock, multicast_group))
                recv_uni.start()
                heartbeat = threading.Thread(target=heartbeat, args=(sock, multicast_group))
                heartbeat.start()
        elif jsonData.type == MESSAGE:
            memberlist = jsonData.data.memberlist
            eyedie = jsonData.data.id
        elif jsonData.type == ELECTION:
            # TODO grund der election abfragen -> fehlender heartbeat oder 2 heartbeats??
            if iamleader:
                receive_uni.exit()
                iamleader = 0
            # handles election when multicast receives election message
            election = threading.Thread(target=elec_function, args=(address, sock, multicast_group))
            election.start()
            
        

        # if heartbeat -> send ack
        # if no heartbeat -> send election -> fehlt
        # if leader -> nothing
        # if message & i am leader -> send to ui
        # if election -> send highest oder wait
        # if highest -> send highest or wait

# only leader
# TODO
def heartbeat(sock, multicast_group):
    # if ack -> nothing        
    while True:
        sent = sock.sendto('{ "type": "HEARTBEAT", "data": [{ "memberlist":' + memberlist + ', "id": ' + eyedie + '}]}'.encode(), (multicast_group, 10000))
        memberlist = []
        try:
            data, server = sock.recvfrom(16)
            jsonData = data.decode()
            if jsonData.type == ACK:
                memberlist.append(server[0])
        except:
            pass


# only leader
def receive_uni(sock, multicast_group):
    # if message_request -> add id to message and send to multicast
    while True:
        try:
            data, server = sock.recvfrom(1024)
            jsonData = data.decode()
            if jsonData.type == MESSAGE_REQUEST:
                eyedie += 1
                message = '{ "type": "MESSAGE", "data": [{ "id": ' + eyedie + ', "msg": ' + jsonData.data + ', "sender": ' + server[0] + '}]}
                sent = sock.sendto(message.encode(), (multicast_group, 10000))


def ui_function(sock):
    print("Welcome to the P2P Chat!")
    print("To get started, just enter your message")
    while True:
        try: 
            message = input()
            sent = sock.sendto('{"type": "MESSAGE_REQUEST", "data": ' + message + '}'.encode(), ip_leader)
        except:
            pass
        try:
            data, server = sock.recvfrom(1024)
            jsonData = data.decode() 
            if jsonData.type == MESSAGE:
                print(jsonData.data.sender, ": ", jsonData.data.msg)
        except:
            pass


def elec_function(address, sock, multicast_group):
    higher = False
    for ip in memberlist:      
        if ip > socket.getsockname():
            higher = True
    if higher = True:
        pass
    else:
        sent = sock.sendto('{ "type": "HIGHEST", "data": ""}'.encode(), (multicast_group, 10000))
        while True:
            try:
                data, address = sock.recvfrom(1024)
                jsonData = data.decode()
                if jsonData.type == HIGHEST:
                    higher = False
                    for ip in memberlist:      
                        if ip > socket.getsockname():
                            higher = True
                    if higher = True:
                        pass
                    else:
                        sent = sock.sendto('{ "type": "HIGHEST", "data": ""}'.encode(), (multicast_group, 10000))
                        while True:
                            try:
                                data, address = sock.recvfrom(1024)
                                jsonData = data.decode()
                                if jsonData.type == HIGHEST:
                                    break
                            except socket.timeout:
                                sent = sock.sendto('{ "type": "LEADER", "data": ""}'.encode(), (multicast_group, 10000))
                                iamleader = 1
                                break
            except socket.timeout:
                    sent = sock.sendto('{ "type": "LEADER", "data": ""}'.encode(), (multicast_group, 10000))
                    iamleader = 1
                    break


















def send_function():
    multicast_group = '224.3.29.71'

    # Create the datagram socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Set a timeout so the socket does not block indefinitely when trying
    # to receive data.
    sock.settimeout(0.2)

    # Set the time-to-live for messages to 1 so they do not go past the
    # local network segment.
    ttl = struct.pack('b', 1)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
    try:
        sent = sock.sendto("hello".encode(), (multicast_group, 10000))
        while True:
                try:
                    data, server = sock.recvfrom(16)
                except socket.timeout:
                    leader = 1
                    break
                else:
                    print('received "%s" from %s' % (data.decode(), server[0]))
                    break
        while True:
            print('\nEnter your message:')
            message = input()

            if message == "exit":
                sent = sock.sendto("left the chat".encode(), (multicast_group, 10000))
                break
            # Send data to the multicast group
            sent = sock.sendto(message.encode(), (multicast_group, 10000))
            #print('\nsending "%s"' % message)

            # nur wenn er leader ist
            # Look for responses from all recipients
            while True:
                try:
                    data, server = sock.recvfrom(16)
                except socket.timeout:
                    break
                else:
                    print('received "%s" from %s' % (data.decode(), server[0]))
            

    finally:
        print('closing socket')
        sock.close()
        # programm beenden


def receive_function():
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

    # Receive/respond loop
    while True:
        data, address = sock.recvfrom(1024)
        # answer new member
        if data.decode() == "hello" and address[0] is not socket.IPPROTO_IP and leader == 1:
            sock.sendto('i am leader'.encode(), address)
        
        #print('\nreceived %s bytes from %s' % (len(data), address))
        print(address[0], ": ", data.decode())

        # ack nur wenn heartbeat empfangen wird
        #print('\nsending acknowledgement to', address)
        sock.sendto('ack'.encode(), address)



if __name__ == "__main__":
    connect()