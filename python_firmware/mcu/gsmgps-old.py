#!/usr/bin/python
import serial
import time
import re


def reader():

    ser = serial.Serial(port='/dev/ttyACM0', baudrate=115200, bytesize=8, timeout=0.1)
    ser.open()


    buf = "ate0\r"
    ser.write(buf)
    dummy_str = ser.read(1000)

    buf = "at+csq\r"
    ser.write(buf)
    gsm_signal_str = ser.read(1000)
    gsm_signal_str = gsm_signal_str.split("\r\n")

    print gsm_signal_str

    buf = "at$gpsacp\r"
    ser.write(buf)
    gps_str = ser.read(1000)
    gps_str = gps_str.split("\r\n")

    buf = "at$gpsp=1\r"
    ser.write(buf)

    ser.close()
    status = []
    status.append(gsm_signal_str[1])
    status.append(gps_str[1])
    return status

def parse_csq(status):

    status = re.findall(r'\d+',status)
    signal = int(status[0])
    print signal
    # actual CSQ signal can be reported between 2 - 30
    # 99 means no signal in any carrier
    if (signal < 1) and (signal > 40):
        return -1
    signal = 113 - (signal * 2)
    print signal
    percent = ((2*(109.00-float(signal)))/113.00) * 100
    print percent
    if percent > 100:
        percent = 100
    #signal = signal - 2;
    #signal = signal * 100 / 28
    return round(percent)

def parse_gps(status):
    coordinates = []

    status = status.split(",")
    if status[1] == ''  or status[2] == '' or status[5] == '' or status[10] == '':
        status[1] = "0000.0000N"
        status[2] = "000.0000W"
        status[5] = "0"
        status[10] = "0"

    # latitude
    degrees = int(status[1][:2])
    minutes = float(status[1][2:-1])
    degrees = degrees + (minutes / 60)
    if status[1][-1:] == "S":
        degrees = - degrees
    coordinates.append(degrees)

    #longitude
    degrees = int(status[2][:3])
    minutes = float(status[2][3:-1])
    degrees = degrees + (minutes / 60)
    if status[2][-1:] == "W":
        degrees = - degrees
        coordinates.append(degrees)


    # fix status
    # valid fix 2 or 3
    if (int(status[5]) < 2):
        status[5] = 0
    else:
        status[5] = 1

    coordinates.append(int(status[5]))
    # sattelite count
    coordinates.append(int(status[10]))

    return coordinates

def main():

    return_list = []

    status = reader()
    #print status

    gsm_signal = parse_csq(status[0])
    gps_loc = parse_gps(status[1])
    #gps_loc = parse_gps("122330.000,5942.8106N,043.2720W,2.25,338.0,3,0.0,0.02,0.01,240613,04")

    return_list.append(gsm_signal)
    return_list.append(gps_loc)

    #print "GSM signal %d %%" % gsm_signal
    #print "Latitude: %f , longitude: %f , fix: %d , sattelites: %d" % (gps_loc[0],gps_loc[1],gps_loc[2],gps_loc[3])
    return return_list

if __name__ == '__main__':    
    status = main()
    print "GSM signal %d %%" % status[0]
    print "Latitude: %f , longitude: %f , fix: %d , sattelites: %d" % (status[1][0],status[1][1],status[1][2],status[1][3])