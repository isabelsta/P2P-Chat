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

def connect():
    #threading
    #x = threading.Thread(target=send_function, args=())
    #x.start()

    #y = threading.Thread(target=receive_function, args=())
    #y.start()

    # handles output for chat members in console
    ui = threading.Thread(target=ui_function, args=())
    ui.start()

    # handles received messages in multicast
    recv_multi = threading.Thread(target=receive_multi, args=(ui))
    recv_multi.start()

    # handles received messages in unicast (leoder only)
    # will be started when member becomes leader
    recv_uni = threading.Thread(target=receive_uni, args=())
    recv_uni.start()

    


def receive_multi(ui):
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

    # Receive loop
    while True:
        data, address = sock.recvfrom(1024)
        jsonData = data.decode()

        # leader logik fehlt
        if jsonData.type == HEARTBEAT and not leader:
            sent = sock.sendto("{ type: 'ACK' , data: ''}".encode(), address)
        elif jsonData.type == LEADER:
            pass
        elif jsonData.type == MESSAGE:
            # TODO send to ui
        elif jsonData.type == ELECTION:
            # handles election when multicast receives election message
            election = threading.Thread(target=elec_function, args=())
            election.start()
            # parameter übergeben
            
        

        # if heartbeat -> send ack
        # if no heartbeat -> send election
        # if leader -> nothing
        # if message & i am leader -> send to ui
        # if election -> send highest oder wait
        # if highest -> send highest or wait

# only leader
def receive_uni():
    # if message_request -> add id to message and send to multicast
    # if ack -> nothing


def ui_function():
    # parse and print messages

def elec_function():
    if address > socket.getsockname():
                pass
            else:
                sent = sock.sendto("{ type: 'HIGHEST', data: ''}".encode(), (multicast_group, 10000))
                while True:
                    try:
                        data, address = sock.recvfrom(1024)
                        jsonData = data.decode()
                        if jsonData.type == HIGHEST:
                            break
                    except socket.timeout:
                        sent = sock.sendto("{ type: 'LEADER', data: ''}".encode(), (multicast_group, 10000))
                        break
        elif jsonData.type == HIGHEST:
            if address > socket.getsockname():
                pass
            else:
                sent = sock.sendto("{ type: 'HIGHEST', data: ''}".encode(), (multicast_group, 10000))
                while True:
                    try:
                        data, address = sock.recvfrom(1024)
                        jsonData = data.decode()
                        if jsonData.type == HIGHEST:
                            break
                    except socket.timeout:
                        sent = sock.sendto("{ type: 'LEADER', data: ''}".encode(), (multicast_group, 10000))
                        break
    # thread beenden


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
        while True:
            print('\nEnter your message:')
            message = input()

            if message == "exit":
                sent = sock.sendto("i leave".encode(), (multicast_group, 10000))
                break
            # Send data to the multicast group
            sent = sock.sendto(message.encode(), (multicast_group, 10000))
            #print('\nsending "%s"' % message)

            # Look for responses from all recipients
            while True:
                try:
                    data, server = sock.recvfrom(16)
                except socket.timeout:
                    break
                else:
                    print('received "%s" from %s' % (data, server[0]))
            

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
        
        #print('\nreceived %s bytes from %s' % (len(data), address))
        print(address[0], ": ", data)

        #print('\nsending acknowledgement to', address)
        sock.sendto('ack'.encode(), address)



if __name__ == "__main__":
    connect()