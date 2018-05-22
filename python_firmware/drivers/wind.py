import types
import traceback
import binascii
import threading
import time
import thread
import os
import struct
import sys
import serial
import minimalmodbus
import pickle
from device_base import deviceBase



class start(threading.Thread, deviceBase):

    def __init__(self, name=None, number=None, mac=None, Q=None, mcu=None, companyId=None, offset=None, mqtt=None, Nodes=None):
        threading.Thread.__init__(self)
        deviceBase.__init__(self, name=name, number=number, mac=mac, Q=Q, mcu=mcu, companyId=companyId, offset=offset, mqtt=mqtt, Nodes=Nodes)
        
        self.daemon = True
        
        self.version = "1"
        
        self.finished = threading.Event()

        self.direction = ""
        self.speed = ""
        #

        threading.Thread.start(self)


        
    #this is a required function for all drivers, its goal is to upload some piece of data
    #about your device so it can be seen on the web
    def register(self):
        #send some peice of data to let meshify know you are there
        pass




    def run(self):
        self.mcu.set232baud(4800)
        extra_data = ""
        while True:
            data = self.mcu.rs232.read()
            if len(data) > 1:
                data = data.split("\r\n")
                for i in data:
                    if len(i.split(",")) == 6:
                        direction = i.split(",")[1]
                        speed = i.split(",")[3]
            else:
                time.sleep(.5)
            pass
            #do something forever
        pass
        


    
    def wind_sync(self, name, value):
        self.sendtodb("connected", "true", 0)
        #do anything here you want to synce your data (channel name is sync)
        return True
    

   
