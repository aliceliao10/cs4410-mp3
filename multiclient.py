#!/usr/bin/python

import getopt
import socket
import sys
import threading
import random
import string
from threading import Thread
from random import randint
# This is the multi-threaded client.  This program should be able to run
# with no arguments and should connect to "127.0.0.1" on port 8765.  It
# should run a total of 1000 operations, and be extremely likely to
# encounter all error conditions described in the README.

host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
port = int(sys.argv[2]) if len(sys.argv) > 2 else 8765
toaddr = sys.argv[3] if len(sys.argv) > 3 else "nobody@example.com"
fromaddr = sys.argv[4] if len(sys.argv) > 4 else "nobody@example.com"

counter = 0
sender_lock      = threading.Lock()
task_add_cv      = threading.Condition(sender_lock)
task_finished_cv = threading.Condition(sender_lock)
wait             = False
ready_socket     = None

# generate random array
# Reference:http://stackoverflow.com/questions/2257441/random-string-generation-with-upper-case-letters-and-digits-in-python

def id_gen(size, chars = string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))
    
def addr_gen():
    return id_gen(random.randint(1,10))+'@'+id_gen(random.randint(1,6))

class Send_Handler:
    
    def __init__(self, socket):
        self.message_buf = ''
        self.socket      = socket
     
    def send(self, message):
        
        try:
            self.socket.send(message.encode('utf-8')+'\r\n')
        except socket.error:
            print('client> Send error')
            self.socket.close()
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
                    print('client> Receive error')
                    self.socket.close()
                    return
                    
        message_return = self.message_buf[0:self.message_buf.find('\r\n')]
        self.message_buf = self.message_buf[self.message_buf.find('\r\n')+2: ]
        return message_return
        
    def handle(self):
        
        k = randint(1,100)
        
        if k <= 70:
            # 70 percent of chance generate correct command sequence
            self.send('HELO ' + id_gen(5))
            print('server> ' + self.receive())
            self.send('MAIL FROM:' + addr_gen())
            print('server> ' + self.receive())
            n = randint(1,6)
            for i in range(n):
                self.send('RCPT TO: ' + addr_gen())
                print('server> ' + self.receive())
            self.send("DATA\r\n")
            print('server> ' + self.receive())    
            self.send(id_gen( randint(20, 100) ))
            print('server> ' + self.receive())    
            self.send('\r\n.\r\n')
            print('server> ' + self.receive())
        else:
            # generate random command sequence
            command = {
                1 : 'HELO ',
                2 : 'MAIL FROM: ',
                3 : 'MAIL FROM ',
                4 : 'RCPT TO: ',
                5 : 'RCPT TO ',
                6 : 'DATA',
                7 : 'HELO'
            }
            addr = {
                1 : addr_gen(),
                # invalide address (with space)
                2 : id_gen(randint(1,8)) + '@' + id_gen(randint(1,3)) + ' ' + id_gen(randint(1,5)),
                3 : '',
                4 : id_gen(randint(1,30))
            }

            N = randint(1,20)
            for i in range(N):
                r1 = randint(1,7)
                r2 = randint(1,4)
                self.send(command[r1] + addr[r2])
                print('server> ' + self.receive())
            self.send('\r\n.\r\n')
            print('server> ' + self.receive())

class Worker(Thread):
    
    def __init__(self):
        Thread.__init__(self)
        self.start()
    
    def run(self):
        
        global sender_lock, task_add_cv, ready_socket, counter
        
        while True:
            with sender_lock:
                while ready_socket == None:
                    task_add_cv.wait()
                counter += 1
                print('client> send counter = ' + str(counter))
                handler = Send_Handler(ready_socket)
                ready_socket = None
                task_finished_cv.notify()                   
            handler.handle()
                       
class ThreadPool:
    
    def __init__(self):
        
        global sender_lock

        with sender_lock:
            for i in range(32):
                Worker()
        
    def push_task(self, clientsocket):
        
        global sender_lock, task_add_cv, task_finished_cv
        global ready_socket, counter
        
        with sender_lock:
            while ready_socket != None or counter >= 1000:
                task_finished_cv.wait()
            ready_socket = clientsocket
            task_add_cv.notify()                            



thread_pool = ThreadPool()
                            
while True:
    try:
        clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        clientsocket.connect((host, port))
    except socket.error:
        print('connection error')
        clientsocket.close()
    thread_pool.push_task(clientsocket)

                        
                        
                        
                        
                        
                        
                        
                        
                        
                        
                        
                        
                        
                        
                        
                        
                    
                    