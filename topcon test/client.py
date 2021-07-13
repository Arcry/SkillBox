#!/usr/bin/env python
# -*- coding: utf-8 -*-

import socket
import hashlib
import matplotlib.pyplot as plt
from fpdf import FPDF
import math
import csv
import sys
import os
import argparse
from socket import error as socket_error



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


def remove_null(string):
    '''removes zeros from start of string before #'''
    return string.split(b'#')[1]
    
def nmea_to_dec_degrees(pos):
    ''' NMEA values of latitude (lontitude) to degrees'''
    dd = pos // 100
    mm = pos - dd*100
    return dd + mm / 60

def byte_to_int_parse(string, n):
    '''
    string is message;
    n is number of  field in message
    '''
    return float((string.split(b',')[n]).decode('utf-8'))

def mean(lst):
    '''counts mean of array'''
    summ = 0
    for num in lst:
        summ += num
    return summ / len(lst)

def variance(lst):
    '''counts variance of array'''
    var = 0
    m = mean(lst)
    for num in lst:
        var += (num - m)**2 / (len(lst) - 1)
    return var

def gps_to_ecef(lat, lon, alt):
    '''transfors gps coords to ECEF (X, Y, Z)'''
    rad_lat = math.radians(lat)
    rad_lon = math.radians(lon)

    a = 6378137.0
    finv = 298.257223563
    f = 1 / finv
    e2 = 2*f - f**2
    v = a / math.sqrt(1 - e2 * math.sin(rad_lat)**2)

    x = (v + alt) * math.cos(rad_lat) * math.cos(rad_lon)
    y = (v + alt) * math.cos(rad_lat) * math.sin(rad_lon)
    z = (v * (1 - e2) + alt) * math.sin(rad_lat)

    return [x, y, z]

def create_pdf(path, mean, var):
    '''save PDF file with statistics'''
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=16)
    pdf.cell(200, 10, txt='Statistics of orthometric height', ln=1, align='C')
    pdf.image(path + '/hist_gga.png', x=50, y=20, w=120, h=80)
    pdf.ln(85)
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 5, txt=f'Expected value = {round(mean, 3)}', ln=1)
    pdf.cell(200, 5, txt=f'Variance = {round(var, 3)}', ln=1)

    pdf.output(path + '/add_hist.pdf')
        

def connect(host, port):
    '''connecting to server'''
    sock = socket.socket()

    try:
        sock.connect((host, port))
        print(f'connected to {host}:{port}')
    except socket_error as serr:
        print(serr)
        sock = None
        print('failed connection to ' + host)
    return sock


def recv_from_server(path, sock):
    '''recieves data from server'''

    b = []
    l = []
    oh = []

    sock.send(bytearray('ready', 'utf-8')) # sending to server that client ready for recieving data
    data = sock.recv(5)
    if data == b'ready': # check that server is ready for sending data
        print('server is ready')
        md5sum_recv = sock.recv(16) # get md5 sum of recieving file
        f = open(path + '/NMEA_GGA_rcvd.tps', 'wb')
        print('start of receiving')
        while True:
            data = sock.recv(100)
            if data[-3:] == b'end': # if server sent 'end' it means sending is over
                print('receiving is over')
                f.close()
                sock.close()
                print("connection is closed")
                break
            else:
                data = remove_null(data)
                f.write(data) # write recieved data to file
                # append data for count statistics, transform nmea to degrees for b and l
                b.append(nmea_to_dec_degrees(byte_to_int_parse(data, 2)))
                l.append(nmea_to_dec_degrees(byte_to_int_parse(data, 4)))
                oh.append(byte_to_int_parse(data, 9))
    else:
        print('error')

    return b, l, oh, md5sum_recv

   
def check_md5(md5sum_recv, path):
    '''checking md5 summs of sent and recieved files''' 
    if md5sum_recv == md5_for_file(path + '/NMEA_GGA_rcvd.tps'):
      print('checksums are equal')
    else:
      print('checksums are not equal')


parser = argparse.ArgumentParser(prog='client.py'
    , formatter_class=argparse.RawTextHelpFormatter
    , description=
    """
    Run client for recieving NMEA_GGA data from server
    ---
    Create PDF file fith statistics
    ---
    Save X, Y, Z coordinates
    """
        )

parser.add_argument("hostport"
    , help="enter host:port, example: 127.0.0.1:9090"
)

parser.add_argument("-d"
    , "--dir"
    , help="set directory where files will be saved, example: /home/client"
)

if __name__ == '__main__':

    args = parser.parse_args()

    host, port = (args.hostport).split(':')
    path = os.path.abspath(os.getcwd())

    if args.dir:
        path = args.dir


    sock = connect(host, int(port))
    if not sock:
        print ("connection error")
        sys.exit(1)

    b, l, oh, md5sum_recv = recv_from_server(path, sock)

    check_md5(md5sum_recv, path)

    # plot and save histogram of orthometric height 

    plt.figure(figsize=(12, 8))
    plt.hist(oh)
    plt.xlabel('Orthometric height',  fontsize=15)
    plt.ylabel('Counts', fontsize=15)
    plt.title('Histogram of orthometric height', fontsize=16)
    plt.xticks(fontsize=12)
    plt.yticks(fontsize=12)
    plt.grid()
    plt.savefig(path + '/hist_gga.png')

    print('hist saved')

    # count expected value (mean for big data) and variance
    exp_val = mean(oh)
    var = variance(oh)

    create_pdf(path, exp_val, var)
    print('pdf saved')

    # save ECEF coords to .csv
    with open(path + '/x_y_z.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        for lat, lon, alt in zip(b, l, oh):
            writer.writerow(gps_to_ecef(lat, lon, alt))

    print('x, y, z coordinates saved')

    sys.exit(0)
