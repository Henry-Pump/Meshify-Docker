#!/usr/bin/python
import serial
import time
import re

class gsmgps:
    #handles the serial connection from linux to the MCU to the xbee

    def __init__(self):
        self.ser = serial.Serial(port='/dev/ttyACM0', baudrate=115200, bytesize=8, timeout=0.1)
        self.ser.open()
        

    def reader(self):

        


        buf = "ate0\r"
        self.ser.write(buf)
        dummy_str = self.ser.read(1000)

        buf = "at+csq\r"
        self.ser.write(buf)
        gsm_signal_str = self.ser.read(1000)
        gsm_signal_str = gsm_signal_str.split("\r\n")

        #print gsm_signal_str

        buf = "at$gpsacp\r"
        self.ser.write(buf)
        gps_str = self.ser.read(1000)
        gps_str = gps_str.split("\r\n")

        buf = "at$gpsp=1\r"
        self.ser.write(buf)

        #self.ser.close()
        status = []
        status.append(gsm_signal_str[1])
        status.append(gps_str[1])
        return status

    def parse_csq(self, status):

        status = re.findall(r'\d+',status)
        signal = int(status[0])
        # actual CSQ signal can be reported between 2 - 30
        # 99 means no signal in any carrier
        if (signal < 1) and (signal > 40):
            return -1
        signal = 113 - (signal * 2)
        percent = ((2*(109.00-float(signal)))/113.00) * 100
        if percent > 100:
            percent = 100
        #signal = signal - 2;
        #signal = signal * 100 / 28
        return round(percent)

    def parse_gps(self, status):
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

    def main(self):

        return_list = []

        status = self.reader()
        #print status

        gsm_signal = self.parse_csq(status[0])
        gps_loc = self.parse_gps(status[1])
        #gps_loc = parse_gps("122330.000,5942.8106N,043.2720W,2.25,338.0,3,0.0,0.02,0.01,240613,04")

        return_list.append(gsm_signal)
        return_list.append(gps_loc)

        #print "GSM signal %d %%" % gsm_signal
        #print "Latitude: %f , longitude: %f , fix: %d , sattelites: %d" % (gps_loc[0],gps_loc[1],gps_loc[2],gps_loc[3])
        return return_list
