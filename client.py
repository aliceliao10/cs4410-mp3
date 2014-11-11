#!/usr/bin/python
import sys
import socket
import datetime

host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
port = int(sys.argv[2]) if len(sys.argv) > 2 else 8765
toaddr = sys.argv[3] if len(sys.argv) > 3 else "nobody@example.com"
fromaddr = sys.argv[4] if len(sys.argv) > 4 else "nobody@example.com"

def send(socket, message):
    # In Python 3, must convert message to bytes explicitly.
    # In Python 2, this does not affect the message.
    try:
        socket.send(message.encode('utf-8'))
    except socket.error:
        print('client> Send error')
        return

message_buf = ''

def receive(socket):
    
    global message_buf
    
    while True:
        if message_buf.find('\r\n') != -1:
            break
        else:
            try:
                socket.settimeout(10)
                message_buf += socket.recv(500)
                socket.settimeout(None)
            except socket.error:
                print('client> time out')
                return
                
    message_return = message_buf[0:message_buf.find('\r\n')]
    message_buf    = message_buf[message_buf.find('\r\n')+2: ]
    return message_return
        
def sendmsg(msgid, hostname, portnum, sender, receiver):
    
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((hostname, portnum))
    except socket.error:
        print('client> connection error')
        return

    send(s, "HELO %s\r\n" % socket.gethostname())
    print('server> ' + receive(s))
    send(s, "MAIL FROM: %s\r\n" % sender)
    print('server> ' + receive(s))
    send(s, "RCPT TO: %s\r\n" % receiver)
    print('server> ' + receive(s))
    send(s, "DATA\r\n")
    print('server> ' + receive(s))    
    send(s, "Date: %s -0500\r\nSubject: msg %d\r\n\n\nContents of message %d end here." % (datetime.datetime.now().ctime(), msgid, msgid))
    print('server> ' + receive(s))    
    send(s, "\r\n.\r\n")
    print('server> ' + receive(s))
    
for i in range(1, 20):
    sendmsg(i, host, port, fromaddr, toaddr)
