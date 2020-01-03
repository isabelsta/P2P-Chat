import socket
import struct
import sys
import threading

def connect():
    #threading
    x = threading.Thread(target=send_function, args=())
    x.start()

    y = threading.Thread(target=receive_function, args=())
    y.start()


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
                    print('received "%s" from %s' % (data, server))
            

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
        print(address, ": ", data)

        #print('\nsending acknowledgement to', address)
        sock.sendto('ack'.encode(), address)



if __name__ == "__main__":
    connect()