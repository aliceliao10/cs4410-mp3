#!/usr/bin/python

import getopt
import socket
import sys
import threading
from shutil import copyfile
from threading import Thread

# STOP!  Don't change this.  If you do, we will not be able to contact your
# server when grading.  Instead, you should provide command-line arguments to
# this program to select the IP and port on which you want to listen.  See below
# for more details.
host = "127.0.0.1"
port = 8765

# Global variables

num_threads = 32

task_lock          = threading.Lock()
task_add_cv        = threading.Condition(task_lock)
task_finished_cv   = threading.Condition(task_lock)
ready_clientsocket = None

mailbox_lock      = threading.Lock()
backup_lock       = threading.Lock()
mailbox_backup_cv = threading.Condition(backup_lock)
mailbox_write_cv  = threading.Condition(backup_lock)
backing_up        = False
message_count     = 0

# Worker

class Backup_Worker(Thread):
    
    def __init__(self):
        Thread.__init__(self)
        self.start()
        
    def run(self):
        
        global backup_lock, backing_up, mailbox_backup_cv, mailbox_write_cv, message_count
        
        while True:
            with backup_lock:
                while backing_up == False:
                    mailbox_backup_cv.wait()
                backing_up = False
                copyfile('./mailbox', './mailbox.' + str(message_count-31) + '-' + str(message_count) )
                # emptying current mailbox
                mailbox = open('mailbox','w')
                mailbox.write('')
                mailbox.close()
                print('server> Mailbox has been backed up and emptied')
                mailbox_write_cv.notify()
                
class SMTP_Worker(Thread):
    
    def __init__(self):
        Thread.__init__(self)
        self.start()
    
    def run(self):
        
        global task_lock, task_add_cv, task_finished_cv
        global ready_clientsocket
        
        while True:
            with task_lock:
                while ready_clientsocket == None:
                    task_add_cv.wait()
                handler = ConnectionHandler(ready_clientsocket)
                ready_clientsocket = None
                task_finished_cv.notify()
                
            handler.handle()
            

# The thread pool

class ThreadPool:
    
    def __init__(self):
        
        global task_lock
        global num_threads
        
        with task_lock:
            for i in range(num_threads):
                SMTP_Worker()
        Backup_Worker()
        
    def push_task(self, clientsocket):
        
        global task_lock, task_add_cv, task_finished_cv
        global ready_clientsocket
        
        with task_lock:
            while ready_clientsocket != None:
                task_finished_cv.wait()
            ready_clientsocket = clientsocket
            task_add_cv.notify()

# handle a single client request

class ConnectionHandler:
    
    def __init__(self, socket):
        
        global message_count
        
        self.socket          = socket
        self.state           = 'closed'
        self.message_buf     = ''
        self.message_receive = ''
        self.mailbox_buf     = list()
        self.error_count     = 0
        
        # Temporary message buffer
        
        self.from_addr = ''
        self.to_addrs  = list()
        self.client    = ''
        self.data_buf  = list()
        
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
        
        self.send('220 mw828 SMTP CS4410MP3')
        print('server> 220 mw828 SMTP CS4410MP3')
        self.state = 'helo'
        while self.state != 'closed':
            self.switch[self.state]()
            if self.error_count >= 20:
                self.timeout()
        self.socket.close()
    
    def send(self, msg):
        
        try:
            self.socket.send(msg.encode('utf-8')+'\r\n')
        except socket.error:
            self.error_count += 1
            self.socket.close()
            print('server> Send error: socket closed')
            return
        
    def receive(self):
        
        while True:
            if self.message_buf.find('\r\n') != -1:
                break
            else:
                try:
                    self.socket.settimeout(10)
                    self.message_buf += self.socket.recv(500)
                    self.socket.settimeout(None)
                except socket.error:
                    self.timeout()
                    print('server> Receive error: socket closed')
                    self.socket.close()
                    return
                    
        message_return = self.message_buf[0:self.message_buf.find('\r\n')]
        self.message_buf = self.message_buf[self.message_buf.find('\r\n')+2: ]
        return message_return
        
    def timeout(self):
        print('server> 421 4.4.2 mw828 Error: timeout exceeded')
        self.send('421 4.4.2 mw828 Error: timeout exceeded')
        self.state = 'closed'
        
    
    
    # server's FSM
    
    def helo(self):
        
        global message_count, mailbox_lock
        
        self.message_receive = self.receive()
        if self.message_receive == None:
            self.error_count += 1
            return
        self.message_receive = self.message_receive.strip()
        space = self.message_receive.find(' ')
        command_t = self.message_receive[0:space].strip().upper()
        client_t  = self.message_receive[space: ].strip()
        print('client> '+ self.message_receive)
            
        # Command correct, proceed to the next state
        
        if space != -1 and command_t == 'HELO' and client_t.find(' ') == -1:
            # self.mailbox_buf.append('Received: from ' + client + ' by mw828 (CS4410MP3)')
            self.client = client_t
            # self.mailbox_buf.append('Number ' + str(self.count))
            self.state = 'mail_from'
            print('server> 250 mw828')
            self.send('250 mw828')
            
        # Error command handling
        
        elif command_t == 'HELO' or self.message_receive.upper() == 'HELO':
            print('server> 501 Syntax: HELO yourhostname')
            self.send('501 Syntax: HELO yourhostname')
            self.error_count += 1
        elif command_t == 'MAIL' or command_t == 'RCPT' or self.message_receive.upper() == 'DATA':
            print('server> 503 Error: need HELO command')
            self.send('503 Error: need HELO command')
            self.error_count += 1
        else:
            print('server> 500 Error: command not recognized')
            self.send('500 Error: command not recognized')
            self.error_count += 1
        return
                 
    def mail_from(self):
        
        self.message_receive = self.receive()
        if self.message_receive == None:
            self.error_count += 1
            return
        self.message_receive = self.message_receive.strip()
        if self.message_receive.upper() == 'HELO':
            print('server> 503 Error: duplicate HELO')
            self.send('503 Error: duplicate HELO')
            self.error_count += 1
            return
        elif self.message_receive.upper() == 'DATA':
            print('server> 503 Error: need MAIL FROM command')
            self.send('503 Error: need MAIL FROM command')
            self.error_count += 1
            return
        colon       = self.message_receive.find(':')
        command_t   = self.message_receive[0:colon].strip().upper()
        from_addr_t = self.message_receive[colon+1: ].strip()
        print('client> '+ self.message_receive)
        if command_t == 'MAIL FROM' and from_addr_t.find(' ') == -1 and colon != -1 and from_addr_t:
            # self.mailbox_buf.append('From: ' + from_addr)
            self.from_addr = from_addr_t
            self.state = 'rcpt_to'
            print('server> 250 OK')
            self.send('250 OK')
            
        # Error command handling
        
        elif command_t == 'MAIL FROM' and colon != -1:
            print('server> 555 <'+from_addr_t+'>: Sender address rejected')
            self.send('555 <'+from_addr_t+'>: Sender address rejected')
            self.error_count += 1
        elif command_t == 'MAIL FROM' or self.message_receive.upper().find('MAIL FROM') != -1:
            print('server> 501 Syntax: MAIL FROM: youremail@yourhost.com')
            self.send('501 Syntax: MAIL FROM: youremail@yourhost.com')
            self.error_count += 1
        elif command_t == 'RCPT TO':
            print('server> 503 Error: need MAIL FROM command')
            self.send('503 Error: need MAIL FROM command')
            self.error_count += 1
        else:
            print('server> 500 Error: command not recognized')
            self.send('500 Error: command not recognized')
            self.error_count += 1
                
    def rcpt_to(self):
        
        self.message_receive = self.receive()
        if self.message_receive == None:
            self.error_count += 1
            return
        self.message_receive = self.message_receive.strip()
        if self.message_receive.upper() == 'HELO':
            print(('server> 503 Error: duplicate HELO'))
            self.send('503 Error: duplicate HELO')
            self.error_count += 1
            return
        elif self.message_receive.upper() == 'DATA':
            print('server> 503 Error: need RCPT TO command')
            self.send('503 Error: need RCPT TO command')
            self.error_count += 1
            return
        
        colon     = self.message_receive.find(':')
        command_t = self.message_receive[0:colon].strip().upper()
        to_addr_t = self.message_receive[colon+1: ].strip()
        print('client> '+ self.message_receive)
        if command_t == 'RCPT TO' and to_addr_t.find(' ') == -1 and colon != -1 and to_addr_t:
            # self.mailbox_buf.append('To: ' + to_addr)
            self.to_addrs.append(to_addr_t)
            print('server> 250 OK')
            self.send('250 OK')
            self.state = 'rcpt_to_set'
            
        # Error commands
        
        elif command_t == 'RCPT TO' and colon != -1:
            print('server> 555 <'+to_addr_t+'>: Recepient address invalid')
            self.send('555 <'+to_addr+'>: Recepient address invalid')
            self.error_count += 1
        elif command_t == 'RCPT TO' or self.message_receive.upper().find('RCPT TO') != -1:
            print('server> 501 Syntax: RCPT TO: youremail@yourhost.com')
            self.send('501 Syntax: RCPT TO: youremail@yourhost.com')
            self.error_count += 1
        elif command_t == 'MAIL FROM':
            print('server> 503 Error: nested MAIL command')
            self.send('503 Error: nested MAIL command')
            self.error_count += 1
        else:
            print('server> 500 Error: command not recognized')
            self.send('500 Error: command not recognized')
            self.error_count += 1
                
    def rcpt_to_set(self):
        
        self.message_receive = self.receive()
        if self.message_receive == None:
            self.error_count += 1
            return
        self.message_receive = self.message_receive.strip()
        if self.message_receive == 'HELO':
            print('server> 503 Error: duplicate HELO')
            self.send('503 Error: duplicate HELO')
            self.error_count += 1
            return
        print('client> '+ self.message_receive)
        
        if self.message_receive.upper() == 'DATA':
            self.state = 'data'
            return
            
        colon = self.message_receive.find(':')
        command_t = self.message_receive[0:colon].strip().upper()
        to_addr_t = self.message_receive[colon+1: ].strip()  
        
        if command_t == 'DATA':
            self.state = 'data'
        elif command_t == 'RCPT TO' and to_addr_t.find(' ') == -1 and colon != -1:
            self.to_addrs.append(to_addr_t)
            print('server> 250 OK')
            self.send('250 OK')
            
        # Error commands
        
        elif command_t == 'RCPT TO' and colon != -1:
            print('server> 555 <'+to_addr_t+'>: Recepient address invalid')
            self.send('555 <'+to_addr_t+'>: Recepient address invalid')
            self.error_count += 1
        elif command_t == 'RCPT TO':
            print('server> 501 Syntax: RCPT TO: youremail@yourhost.com')
            self.send('501 Syntax: RCPT TO: youremail@yourhost.com')
            self.error_count += 1
        elif command_t == 'MAIL FROM':
            print('server> 503 Error: nested MAIL command')
            self.send('503 Error: nested MAIL command')
            self.error_count += 1
        else:
            print('server> 500 Error: command not recognized')
            self.send('500 Error: command not recognized')
            self.error_count += 1


    def data(self):
        
        print('server> 354 End data with <CR><LF>.<CR><LF>')
        self.send('354 End data with <CR><LF>.<CR><LF>')
        
        # recieving data until <CR><LF>.<CR><LF> reached
        
        self.message_receive = self.receive()
        if self.message_receive == None:
            self.error_count += 1
            return
        while self.message_receive != '.':
            self.data_buf.append(self.message_receive)
            self.message_receive = self.receive()
            
        print('client> '+ self.message_receive)
        self.state = 'deliver'
        
                
    def deliver(self):
        
        global mailbox_lock, backup_lock, mailbox_backup_cv, mailbox_write_cv, backing_up, message_count
        
        with mailbox_lock:
            
            # invoke the backup thread if necessary
            # note that during backup it does not give up the lock to 
            # wirte file
            
            with backup_lock:
                if message_count >= 32 and message_count % 32 == 0:
                    backing_up = True
                    mailbox_backup_cv.notify()
                    while backing_up == True:
                        mailbox_write_cv.wait()

            message_count += 1
            
            self.mailbox_buf.append('Received: from ' + self.client + ' by mw828 (CS4410MP3)')
            self.mailbox_buf.append('Number: ' + str(message_count))
            self.mailbox_buf.append('From: ' + self.from_addr)
            for i in self.to_addrs:
                self.mailbox_buf.append('To:' + i)
            for i in self.data_buf:
                self.mailbox_buf.append(i)        
        
            mailbox_file = open('mailbox','a')
            for i in self.mailbox_buf:
                mailbox_file.write(i + '\n')
            mailbox_file.write('\n')
            mailbox_file.close()     
            print('server> 250 OK: delivered message ' + str(message_count))
            self.send('250 OK: delivered message ' + str(message_count))
            
        self.state = 'closed'
        
    
# the main server loop
def serverloop():
    
    global mailbox_lock
    
    with mailbox_lock:
        mailbox = open('mailbox','w')
        mailbox.write('')
        mailbox.close()
        print('server> New mailbox file created')
    
    serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # mark the socket so we can rebind quickly to this port number
    # after the socket is closed
    serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # bind the socket to the local loopback IP address and special port
    serversocket.bind((host, port))
    # start listening with a backlog of 5 connections
    serversocket.listen(5)
    
    thread_pool = ThreadPool()
    
    while True:
        # accept a connection
        (clientsocket, address) = serversocket.accept()
        thread_pool.push_task(clientsocket)

# You don't have to change below this line.  You can pass command-line arguments
# -h/--host [IP] -p/--port [PORT] to put your server on a different IP/port.
opts, args = getopt.getopt(sys.argv[1:], 'h:p:', ['host=', 'port='])

for k, v in opts:
    if k in ('-h', '--host'):
        host = v
    if k in ('-p', '--port'):
        port = int(v)

print("server> Server coming up on %s:%i" % (host, port))
serverloop()
