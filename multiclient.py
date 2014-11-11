#!/usr/bin/python

import getopt
import socket
import sys
import threading
import random
import string
from threading import Thread

# This is the multi-threaded client.  This program should be able to run
# with no arguments and should connect to "127.0.0.1" on port 8765.  It
# should run a total of 1000 operations, and be extremely likely to
# encounter all error conditions described in the README.

host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
port = int(sys.argv[2]) if len(sys.argv) > 2 else 8765
toaddr = sys.argv[3] if len(sys.argv) > 3 else "nobody@example.com"
fromaddr = sys.argv[4] if len(sys.argv) > 4 else "nobody@example.com"

counter = 0
counter_lock = threading.Lock()
socket_lock  = threading.Lock()


# Reference:http://stackoverflow.com/questions/2257441/random-string-generation-with-upper-case-letters-and-digits-in-python

def id_gen(size, chars = string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

def id_gen_space(size, chars = string.ascii_lowercase + string.digits + ' '):
    return ''.join(random.choice(chars) for _ in range(size))
    
def addr_gen():
    return id_gen(random.randint(1,8))+'@'+id_gen(random.randint(1,6))

def addr_gen_space():
    return id_gen(random.randint(1,8))+'@'+id_gen(random.randint(1,6))

def send(socket, message):
    # In Python 3, must convert message to bytes explicitly.
    # In Python 2, this does not affect the message.
    socket.send(message.encode('utf-8'))
    
class Send_Worker(Thread):
    
    def __init__(self, thread_id):
        Thread.__init__(self)
        self.start()
        self.thread_id = thread_id
        
    
    def run(self):
        
        global host, port, toaddr, fromaddr
        global socket_lock, counter_lock, counter
        
        while True:
            
            with socket_lock:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect((host, port))
                if random.randint(1,100) < 60:
                    # 60% chance to generate normal sequence
                    send(s, "HELO %s\r\n" % id_gen(random.randint(1,8)))
                    print(s.recv(500))
                    send(s, "MAIL FROM: %s\r\n" % addr_gen())
                    print(s.recv(500))
                    N = random.randint(1,5)
                    for i in range(1,N):
                        send(s, "RCPT TO: %s\r\n" % addr_gen())
                    print(s.recv(500))
                    send(s, 'DATA\r\n')
                    print(s.recv(500))
                    N = random.randint(1,15)
                    for i in range(1,N):
                        send(s, "%s\r\n" % id_gen(random.randint(1,15)))
                    send(s, '.\r\n')
                    print(s.recv(500))    
                else:
                    N = random.randint(5,25)
                    for i in range(1,N):
                        
                        commands = {
                            0 : 'HELO ',
                            1 : 'MAIL FROM: ',
                            2 : 'RCPT TO: ',
                            3 : 'DATA',
                            4 : ''
                        }
                        k = random.randint(1,4)
                        if k == 1 or k == 2:
                            para = addr_gen_space()
                        else:
                            para = id_gen_space(random.randint(1,15)) 
                        send(s, commands[k] + para + '\r\n')
                        print(s.recv(500))
                    
                    with counter_lock:
                        if counter >= 1000:
                            return
                        else:
                            counter += 1
                            
                            
                            
                            
for i in range(32):
    Send_Worker(i)
                        
                        
                        
                        
                        
                        
                        
                        
                        
                        
                        
                        
                        
                        
                        
                        
                    
                    