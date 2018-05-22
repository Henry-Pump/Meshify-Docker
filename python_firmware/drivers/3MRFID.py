import types
import traceback
import binascii
import threading
import time
import thread
import os
import re
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
        self.auth = False
        self.last_alarm = "Off"
        self.last_din2 = ""

        self.last_door = ""
        self.last_lock = ""

        self.version = "8"
        
        self.finished = threading.Event()
        threading.Thread.start(self)

        #load stored rfid mappings
        try:
            with open('/root/python_firmware/drivers/RFIDMap.p', 'rb') as handle:
                self.RFIDMap = pickle.load(handle)
                
            print "found pickled dictionary"
            print self.RFIDMap
        except:
            print "couldn't load rfid map from pickle"
            self.RFIDMap = {
                   1:{"name":"","id":"","on":""},
                   2:{"name":"","id":"","on":""},
                   3:{"name":"","id":"","on":""},
                   4:{"name":"","id":"","on":""},
                   5:{"name":"","id":"","on":""},
                   6:{"name":"","id":"","on":""},
                   7:{"name":"","id":"","on":""},
                   8:{"name":"","id":"","on":""},
                   9:{"name":"","id":"","on":""},
                   10:{"name":"","id":"","on":""},
                   11:{"name":"","id":"","on":""},
                   12:{"name":"","id":"","on":""},
                   13:{"name":"","id":"","on":""},
                   14:{"name":"","id":"","on":""},
                   15:{"name":"","id":"","on":""},
                   16:{"name":"","id":"","on":""},
                   17:{"name":"","id":"","on":""},
                   18:{"name":"","id":"","on":""},
                   19:{"name":"","id":"","on":""},
                   20:{"name":"","id":"","on":""},
                   21:{"name":"","id":"","on":""},
                   22:{"name":"","id":"","on":""},
                   23:{"name":"","id":"","on":""},
                   24:{"name":"","id":"","on":""},
                   25:{"name":"","id":"","on":""},
                   26:{"name":"","id":"","on":""},
                   27:{"name":"","id":"","on":""},
                   28:{"name":"","id":"","on":""},
                   29:{"name":"","id":"","on":""},
                   30:{"name":"","id":"","on":""},
                }
        self.register()
        
    #this is a required function for all drivers, its goal is to upload some piece of data
    #about your device so it can be seen on the web
    def register(self):
        for number in self.RFIDMap:
            usr = "usr" + str(number)
            name = usr + "_name"
            id = usr + "_id"
            on = usr + "_on"
            self.sendtodb(name, self.RFIDMap[number]["name"], 0)
            self.sendtodb(id, self.RFIDMap[number]["id"], 0)
            self.sendtodb(on, self.RFIDMap[number]["on"], 0)

    def processID(self, cardId, direction):
        sent = False
        for number in self.RFIDMap:

            print cardId.strip(), str(self.RFIDMap[number]["id"])
            if cardId.strip() == str(self.RFIDMap[number]["id"]):
                if str(self.RFIDMap[number]["on"]).lower() == "on":
                    self.sendtodb("log", "opening door", 0)
                    self.sendtodb("aclog", (self.RFIDMap[number]["name"] + "    " + direction), 0)
                    channel = "usr" + str(number) + "_last_entry"
                    self.sendtodb(channel, "Granted Access", 0)
                    self.openDoor()
                    return
                    sent = True
                else:
                    #we know the person but they don't have access
                    self.sendtodb("log", "access denied", 0)
                    self.sendtodb("aclog", (self.RFIDMap[number]["name"] + "    " + self.RFIDMap[number]["id"] + "    Denied Access"), 0)
                    channel = "usr" + str(number) + "_last_entry"
                    self.sendtodb(channel, "Denied Access", 0)
                    sent = True
                    return
        if sent == False:
            self.sendtodb("aclog", ("Unknown User    " + cardId.strip() + "    Denied Access"), 0)

    def GPIOThread(self):
        while True:
            try:
                door = self.mcu.getDict()["din2"]
                if self.last_door != door:
                    if door == "On" or door == "1" or door == "1" or door == "on":
                        door2 = "Closed"
                    else:
                        door2 = "Open"
                    self.sendtodb("door", door2, 0)
                    self.last_door = door

                lock = self.mcu.getDict()["relay1"]
                if self.last_lock != lock:
                    if lock == "On" or lock == "1" or lock == "1" or lock == "on":
                        lock2 = "Unlocked"
                    else:
                        lock2 = "Locked"
                    self.sendtodb("lock", lock2, 0)
                    self.last_lock = lock
                time.sleep(1)
            except Exception,e:
                print e
                time.sleep(2)



    def rs485Thread(self):
        cardId = ''
        while True:
            try:
                cardId += re.sub(r"\s+", "", self.mcu.rs485.read(), flags=re.UNICODE) 
                #print "here is the card id"
                #print cardId
                if "B" in cardId:
                    id = cardId.split("B")[0]
                    self.processID(id, "Entered Site")
                    cardId = ''
                if len(cardId) > 5:
                    self.processID(cardId, "Entered Site")
                    cardId = ''
                    
                                    

                   
                time.sleep(.1)
            except Exception,e:
                print e


    def rs232Thread(self):
        cardId = ''
        while True:
            try:
                cardId += re.sub(r"\s+", "", self.mcu.rs232.read(), flags=re.UNICODE) 
                #print "here is the card id"
                #print cardId
                if "B" in cardId:
                    id = cardId.split("B")[0]
                    self.processID(id, "Exited Site")
                    cardId = ''
                if len(cardId) > 5:
                    self.processID(cardId, "Exited Site")
                    cardId = ''
                    
                                    

                   
                time.sleep(.1)
            except Exception,e:
                print e
        
    def run(self):

        self.mcu.set232Baud(9600)
        self.mcu.set485Baud(9600)
        
        
        thread.start_new_thread(self.rs232Thread, ())
        thread.start_new_thread(self.rs485Thread, ())
        thread.start_new_thread(self.GPIOThread, ())

        self.sendtodb("alarm", "Off", 0)

        while True:

            #door, lock

            try:
                #check and see if you need to trigger the video
                if self.mcu.getDict()["din2"] == "Off":
                    if self.last_din2 == "On":

                        #if its not authorized, turn the alarm on
                        if self.auth == False:
                            self.sendtodb("alarm", "On", 0)
                            self.last_alarm = "On"

                        self.mcu.digitalOut4(str(1))
                        time.sleep(5)
                        self.mcu.digitalOut4(str(0))
                        self.last_din2 = "Off"
                        time.sleep(30)

                        #reset the alarm if its on
                        if self.last_alarm == "On":
                            time.sleep(5)
                            self.sendtodb("alarm", "Off", 0)
                            self.last_alarm = "Off"
                else:
                    self.last_din2 = "On"
                    time.sleep(1)
            except:
                time.sleep(1)
        
    def genericSet(self, name, value, id):

        try:

            if name == "open":

                self.openDoor()
                return True

            #usr1_id usr1_on usr1_name
            if name.split("_")[0][:-1] == "usr":
                number = int(name.split("_")[0].replace("usr", ""))
                self.RFIDMap[number][name.split("_")[1]] = value
                #update persistant dictionary
                with open('/root/python_firmware/drivers/RFIDMap.p', 'wb') as handle:
                    pickle.dump(self.RFIDMap, handle)
            

            self.sendtodb(name, value, 0)
        except Exception,e:
            print e

        return True
    def takeVideo(self):
        self.mcu.digitalOut1(str(1))
        time.sleep(5)
        self.mcu.digitalOut1(str(0))

    def openDoor(self):
        thread.start_new_thread(self.takeVideo, ())
        self.auth = True
        try:
            success = False
            tries = 0 
            while success == False:
                success = self.mcu.relay1(1)
                tries += 1
                if tries > 10:
                    break
                time.sleep(1)
            time.sleep(1)
            success = False
            tries = 0 
            while success == False:
                success = self.mcu.relay1(0)
                tries += 1
                if tries > 10:
                    break
                time.sleep(1)
        except:
            pass
        self.auth = False

    def rf3m_open(self, name, value):
        self.openDoor()
        return True
    def poc_sync(self, name, value):
        self.sendtodb("connected", "true", 0)
        self.last_wlevel = 0
        self.last_olevel = 0
        self.last_temp = 0
        return True
    

   
