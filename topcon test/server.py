#!/usr/bin/env python
# -*- coding: utf-8 -*-

import socket
import os
import hashlib
import sys
import argparse
from time import sleep

def md5_for_file(path, block_size=2**20):
    '''count md5 summ for file '''

    md5 = hashlib.md5()
    with open(path,"rb") as f:
        while True:
            data = f.read(block_size)
            if not data:
                break
            md5.update(data)
    return md5.digest()

def add_null(string):
    '''appends zeros to a string up to 100 bytes 
    and appends # for split'''
    return b'0'*(99 - len(string))+ b'#' + string


def bind(host, port):
        '''bind socket to host'''
        sock = socket.socket()
        sock.bind((host, port))
        sock.listen(1)
        print('socket is listening')
        conn, addr = sock.accept()
        return conn

def mysend(path, conn):
    '''sending data to client'''
    while True:
        data = conn.recv(5)
        if data == b'ready':  # check that client is ready for recieving data
            print('client is_ready')
            conn.send(bytearray('ready', 'utf-8')) # sending massage that server is ready for sending data

            conn.send(md5_for_file(path + '/NMEA_GGA.tps')) # sending md5 sum of sending file

            with open(path + '/NMEA_GGA.tps', 'rb') as f:
                chunk = f.readline()
                print('start_of sending')
                conn.send(add_null(chunk))
                
                while True:
                    chunk = f.readline()
                    if not chunk:
                        break
                    conn.send(add_null(chunk))
                    sleep(1) # set to 1, for speed 100 bytes/sec, better set 0.00005
            conn.send(bytearray('end', 'utf-8'))

        else:
            print('end')
            conn.close()
            break


parser = argparse.ArgumentParser(prog='server.py'
    , formatter_class=argparse.RawTextHelpFormatter
    , description=
    """
    Run server for sending NMEA_GGA data to client
    """
        )

parser.add_argument("hostport"
    , help="enter host:port example: 127.0.0.1:9090"
)

parser.add_argument("-d"
    , "--dir"
    , help="set dir for file to be sent to client example: /home/client"
)

if __name__ == '__main__':

    args = parser.parse_args()

    host, port = (args.hostport).split(':')
    path = os.path.abspath(os.getcwd())

    if args.dir:
        path = args.dir
   
   # makes infinite loop for connections
    while True:
        conn = bind(host, int(port))
        mysend(path, conn)


    sys.exit(0)