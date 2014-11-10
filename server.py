#!/usr/bin/python

import getopt
import socket
import sys

# STOP!  Don't change this.  If you do, we will not be able to contact your
# server when grading.  Instead, you should provide command-line arguments to
# this program to select the IP and port on which you want to listen.  See below
# for more details.
host = "127.0.0.1"
port = 8765

recv_block_size = 500
message_count = 0


# handle a single client request

class ConnectionHandler:
    
    # server's FSM
    
    def helo(self):
        
        global message_count
        
        self.message_send = '220 mw828 SMTP CS4410MP3'
        self.send(self.message_send)
        print('server> waiting for HELO')
        
        self.message_receive = self.receive()
        self.message_receive = self.message_receive.strip()
        space = self.message_receive.find(' ')
        command = self.message_receive[0:space].strip().upper()
        client = self.message_receive[space: ].strip()
        print('client> '+ self.message_receive)
        if command == 'HELO' and client.find(' ') == -1:
             self.mailbox_buf.append('Received: from ' + client + ' by mw828 (CS4410MP3)')
             message_count += 1
             self.mailbox_buf.append('Number ' + str(message_count))
             self.state = 'mail_from'
             self.message_send = '250 mw828'
             self.send(self.message_send)
                 
    def mail_from(self):
        
        print('server> waiting for MAIL FROM')
        
        self.message_receive = self.receive()
        self.message_receive = self.message_receive.strip()
        colon = self.message_receive.find(':')
        command = self.message_receive[0:colon].strip().upper()
        from_addr = self.message_receive[colon+1: ].strip()
        print('client> '+ self.message_receive)
        if command == 'MAIL FROM':
            self.mailbox_buf.append('From: ' + from_addr)
            self.state = 'rcpt_to'
            self.message_send = '250 OK'
            self.send(self.message_send)
                
    def rcpt_to(self):
        
        print('server> Waiting for RCPT TO')
        
        self.message_receive = self.receive()
        self.message_receive = self.message_receive.strip()
        colon = self.message_receive.find(':')
        command = self.message_receive[0:colon].strip().upper()
        to_addr = self.message_receive[colon+1: ].strip()
        print('client> '+ self.message_receive)
        if command == 'RCPT TO':
            self.mailbox_buf.append('To: ' + to_addr)
            self.message_send = '250 OK'
            self.send(self.message_send)
            self.state = 'rcpt_to_set'
                
    def rcpt_to_set(self):
        
        print('server> Waiting for DATA or another RCPT TO')
        
        self.message_receive = self.receive()
        self.message_receive = self.message_receive.strip()
        print('client> '+ self.message_receive)
        
        if self.message_receive.upper() == 'DATA':
            self.state = 'data'
            return
            
        colon = self.message_receive.find(':')
        command = self.message_receive[0:colon].strip().upper()
        to_addr = self.message_receive[colon+1: ].strip()  

        if command == 'RCPT TO':
            self.mailbox_buf.append('To: ' + to_addr)
            self.message_send = '250 OK'
            self.send(self.message_send)
    
    def data(self):
        
        self.message_send = '354 End data with <CR><LF>.<CR><LF>'
        self.send(self.message_send)
        print('server> Receiving data')
        
        self.message_receive = self.receive()
        while self.message_receive != '.':
            self.mailbox_buf.append(self.message_receive)
            self.message_receive = self.receive()
            
        print('client> '+ self.message_receive)
        self.state = 'deliver'
        
                
    def deliver(self):
        
        global message_count
        
        self.message_send = '250 OK: delivered message ' + str(message_count)
        self.send(self.message_send)
        
        mailbox_file = open('mailbox','a')
        for i in self.mailbox_buf:
            mailbox_file.write(i + '\n')
        mailbox_file.write('\n')
        mailbox_file.close()
        self.state = 'closed'
        print('server> mail #' + str(message_count) +' delivered')
    
    def __init__(self, socket):
        self.socket  = socket
        self.state   = 'closed'
        self.message         = ''
        self.message_receive = ''
        self.message_send    = ''
        self.mailbox_buf     = list()
        self.message_count   = 0
        
        # Pythonic implementation of the switch-case statement

        self.switch = {
            'helo'          : self.helo,
            'mail_from'     : self.mail_from,
            'rcpt_to'       : self.rcpt_to,
            'rcpt_to_set'   : self.rcpt_to_set,
            'data'          : self.data,
            'deliver'       : self.deliver
        }
        
    def handle(self):
        
        self.state = 'helo'
        while self.state != 'closed':
            self.switch[self.state]()
        self.socket.close()
    
    def send(self, msg):
        
        try:
            self.socket.send(msg+'\r\n')
        except socket.error:
            print('server> Send error: socket closed')
            return
        
    def receive(self):
        
        while True:
            if self.message.find('\r\n') != -1:
                break
            else:
                try:
                    self.socket.settimeout(10)
                    self.message += self.socket.recv(recv_block_size)
                    self.socket.settimeout(None)
                except socket.error:
                    self.timeout();
                    return
                    
        message_return = self.message[0:self.message.find('\r\n')]
        self.message = self.message[self.message.find('\r\n')+2: ]
        return message_return
        
    def timeout(self):
        
        self.message_send = '421 4.4.2 mw828 Error: timeout exceeded'
        self.send(self.message_send)
        self.socket.close()
        
    
                        
                
                    

# the main server loop
def serverloop():
    serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # mark the socket so we can rebind quickly to this port number
    # after the socket is closed
    serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # bind the socket to the local loopback IP address and special port
    serversocket.bind((host, port))
    # start listening with a backlog of 5 connections
    serversocket.listen(5)

    while True:
        # accept a connection
        (clientsocket, address) = serversocket.accept()
        ct = ConnectionHandler(clientsocket)
        ct.handle()

# You don't have to change below this line.  You can pass command-line arguments
# -h/--host [IP] -p/--port [PORT] to put your server on a different IP/port.
opts, args = getopt.getopt(sys.argv[1:], 'h:p:', ['host=', 'port='])

for k, v in opts:
    if k in ('-h', '--host'):
        host = v
    if k in ('-p', '--port'):
        port = int(v)

print("Server coming up on %s:%i" % (host, port))
serverloop()
