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
import pickle
from device_base import deviceBase
import json
import requests
import binascii
import copy

nodeDefaults = { 
                "a1":{"uval":10,
                       "lval":0,
                       "uvolts":10,
                       "lvolts":0,
                       "low":0,
                       "high":10,
                       "last_value":[],
                       "last_send_time":0,
                       "type":None,
                       "diameter-ft":"",
                       "width-ft":"",
                       "length-ft":"",
                       "diameter-in":"",
                       "width-in":"",
                       "length-in":"",
                       "watertype":"",
                       "gallons":"",
                       "vn":"Analog Input 1",
                       "units":"Volts"
                    },
                "cl1":{"uval":20,
                       "lval":0,
                       "uvolts":20,
                       "lvolts":0,
                       "low":0,
                       "high":20,
                       "last_value":[],
                       "last_send_time":0,
                       "type":None,
                       "diameter-ft":"",
                       "width-ft":"",
                       "length-ft":"",
                       "diameter-in":"",
                       "width-in":"",
                       "length-in":"",
                       "watertype":"",
                       "gallons":"",
                       "vn":"Current Loop 1",
                       "units":"ma"
                    },
                "a2":{"uval":10,
                       "lval":0,
                       "uvolts":10,
                       "lvolts":0,
                       "low":0,
                       "high":10,
                       "last_value":[],
                       "last_send_time":0,
                       "type":None,
                       "diameter-ft":"",
                       "width-ft":"",
                       "length-ft":"",
                       "diameter-in":"",
                       "width-in":"",
                       "length-in":"",
                       "watertype":"",
                       "gallons":"",
                       "vn":"Analog Input 2",
                       "units":"Volts"
                    },
                "cl2":{"uval":20,
                       "lval":0,
                       "uvolts":20,
                       "lvolts":0,
                       "low":0,
                       "high":20,
                       "last_value":[],
                       "last_send_time":0,
                       "type":None,
                       "diameter-ft":"",
                       "width-ft":"",
                       "length-ft":"",
                       "diameter-in":"",
                       "width-in":"",
                       "length-in":"",
                       "watertype":"",
                       "gallons":"",
                       "vn":"Current Loop 2",
                       "units":"ma"
                    }

                
                }


class start(threading.Thread, deviceBase):

    def __init__(self, name=None, number=None, mac=None, Q=None, mcu=None, companyId=None, offset=None, mqtt=None, Nodes=None):
        threading.Thread.__init__(self)
        deviceBase.__init__(self, name=name, number=number, mac=mac, Q=Q, mcu=mcu, companyId=companyId, offset=offset, mqtt=mqtt, Nodes=Nodes)
        
        self.daemon = True
        
        self.version = "4"
        
        self.finished = threading.Event()

        self.firstRun = True
        #
        self.idDIct = {}

        #look for tank set up data
        try:
            with open('/root/python_firmware/drivers/tanksetup.p', 'rb') as handle:
                self.tanksetup = pickle.load(handle)
                
            print "found pickled tank set up data"
            print self.tanksetup
        except:
            print "couldn't load tank set up from pickle"
            self.tanksetup = {}

        #load stored analog input data
        self.analogLock = threading.Lock()
        try:
            with open('/root/python_firmware/drivers/LoRa_analogData.p', 'rb') as handle:
                self.analogData = pickle.load(handle)
                
            print "found analogData dictionary"
            print self.analogData
        except:
            print "couldn't load analogData from pickle"
            self.analogData = { }

        self.analogDataSync(True)
        threading.Thread.start(self)


        
    #this is a required function for all drivers, its goal is to upload some piece of data
    #about your device so it can be seen on the web
    def register(self):
        #send some peice of data to let meshify know you are there
        pass
    def analogDataSync(self, all=True):

        with self.analogLock:
            for id in self.analogData:
                for item in self.analogData[id]:
                    self.analogData[id][item]["last_value"] = []

                    if all:
                        knownChannels = ["uval","lval","uvolts","lvolts","low","high","type","diameter-ft","width-ft","length-ft","diameter-in","width-in","length-in","watertype","gallons","units","vn"]
                        for channel in self.analogData[id][item]:
                            name = None
                            if item == "a1" and channel in knownChannels:
                                name = "a1-" + channel
                            elif item == "cl1" and channel in knownChannels:
                                name = "cl1-" + channel
                            elif item == "a2" and channel in knownChannels:
                                name = "a2-" + channel
                            elif item == "cl2" and channel in knownChannels:
                                name = "cl2-" + channel
                       

                            if name is not None:
                                self.sendtodbLora(id, name, str(self.analogData[id][item][channel]), 0, "ilora")
                            

    def set(self, ser, cmd):
        count = 0
        resp = ""
        while not "ok" in resp.lower():
            count += 1
            ser.write(cmd +  '\r\n')
            time.sleep(.005)
            resp = ser.readline()
            if count > 10:
                print "FAILED", cmd
                return False
        print cmd, "success"
        return True
    def getsnr(self, ser):
        ser.readline()
        ser.write("radio get snr" + '\r\n')
        time.sleep(.05)
        print "here is the snr"
        snr = ser.readline()
        print snr
        return snr.replace("\r\n","").strip()
    def killOtherRadio(self, ser2):
        while True:
            ser2.write("sys sleep 1000000" + '\r\n')
            print ser2.readline()
            time.sleep(600)

    def bin_to_float(self, b):
        """ convert binary string to float """
        return struct.unpack('<f', b)

    def makeIntervalACK(self, id, ackData):
        period = ackData.split(",")[0]
        ackCount = ackData.split(",")[1]
        warmup = ackData.split(",")[2]
        inputs = ackData.split(",")[3]
        try:
            if int(period) > 16777215 or int(ackCount) > 255:
                return None
            if int(inputs,2) > 255: 
                return None
            if int(warmup) > 100:
                return None
        except:
            return None

        val = hex(int(period)).replace('0x','').upper()
        while len(val) < 6:
            val = "0" + val
        val2 = hex(int(ackCount)).replace('0x','').upper()
        while len(val2) < 2:
            val2 = "0" + val2
        val3 = hex(int(warmup)).replace('0x','').upper()
        while len(val3) < 2:
            val3 = "0" + val3
        inputs = hex(int(inputs,2)).replace("0x","").upper()
        while len(inputs) < 2:
            inputs = "0" + inputs


        if len(id + val + val2 + val3 + inputs) == 16:
            return ("53" + id + val + val2 + val3 + inputs)
        else:
            return None

        

    def run(self):

        lastMsgTime = time.time()
    

        ser = serial.Serial(port='/dev/ttyUSB0', baudrate=57600, bytesize=8, timeout=5)
        ser2 = serial.Serial(port='/dev/ttyUSB1', baudrate=57600, bytesize=8, timeout=5)
        thread.start_new_thread(self.killOtherRadio, (ser2,))
        ser.readline()
        







        ser.write("mac pause" +  '\r\n')
        self.gatewayTimes = {}
        self.gatewayNewTimes = {}

        lst = ["radio set mod lora",
        "radio set sf sf12",
        "radio set afcbw 41.7",
        "radio set rxbw 125",
        "radio set fdev 5000",
        "radio set prlen 8",
        "radio set crc on",
        "radio set cr 4/8",
        "radio set wdt 0",
        "radio set sync 12",
        "radio set bw 125",
        "radio set pwr 20"]

        for i in lst:
            self.set(ser, i)
        while True:
            ser.write("radio rx 0\r\n")
            count = 0
            try:
                while True:
                    
                    ser.write("radio rx 0\r\n")
                    time.sleep(1)
                    count +=1
                    a = ser.readline()
                    a = a.strip().replace("busy", "")
                    if len(a) == 0:
                        a = ser.readline()
                    if len(a) > 0:
                        print a
                        if "radio_err" in a:
                            break
                        if "radio_rx" in a:
                            lastMsgTime = time.time()
                            #snr = self.getsnr(ser)

                            last_time = time.time()
                            mainObj = {}
                            values = {}


                            try:
                                id = self.parseLoraData(a[10:-2], ser)
                                if id not in self.idDIct:
                                    self.idDIct[id[0:2]] = id

                                if id in self.gatewayTimes:
                                    lastTime = self.gatewayTimes[id]
                                else:
                                    lastTime = time.time()
                                self.gatewayTimes[id] = time.time()
                                print "time since last  ", time.time() - lastTime
                                

                                
                            except Exception,e:
                                print "buffer too short", e
                                continue
                           


                    if count > 3000:
                        ser.write("mac pause" +  '\r\n')
                        for i in lst:
                            self.set(ser, i)
                        time.sleep(.05)
                        if time.time() - lastMsgTime > 1860:
                            ser.close()
                            time.sleep(2)
                            ser = serial.Serial(port='/dev/ttyUSB0', baudrate=57600, bytesize=8, timeout=1)
                            lastMsgTime = time.time()
                        break
                        

            except Exception,e:
                print e

    def genericSet(self, name, value, id, longId=None):
        print id
        print longId


        if name == "sinterval":
            try:
                if longId == None:
                    longId = self.idDIct[id]

                val = self.makeIntervalACK(longId, value)
                if val == None:
                    return "Node Update Data Invalid"

                print "here is the new time and id"
                print id, val
                self.gatewayNewTimes[longId] = value
                self.sendtodbLora(longId[0:2] + ":" + longId[2:4], "sinterval", value, 0, "ilora")
                return True
            except Exception,e:
                print e
        elif name.split("-")[0] == "a1" or name.split("-")[0] == "a2" or name.split("-")[0] == "cl1" or name.split("-")[0] == "cl2":
            #try:
            #    value = float(value)
            #except:
            #    return(" Value must be a float or integer")
            return self.processAnalog(name, value, longId)
    
    def processAnalog(self, name, value, id):
        with self.analogLock:
            stringTypeNames = ["units", "vn", "type", "watertype"]
            try:
               

                
                analogName = name.split("-")[0]
                if len(name.split("-")) == 2:
                    chName = name.split("-")[1]
                elif len(name.split("-")) == 3:
                    chName = name.split("-")[1] + "-" + name.split("-")[2]
                if chName not in stringTypeNames:
                    self.analogData[id][analogName][chName] = float(value)
                else:
                    self.analogData[id][analogName][chName] = str(value)

                #update persistant dictionary
                with open('/root/python_firmware/drivers/LoRa_analogData.p', 'wb') as handle:
                    pickle.dump(self.analogData, handle)
                self.sendtodbLora(id, name, value, 0, "ilora")
                
            except Exception, e:
                return str(e)
                return "device unknown or bad data"

            return True

    def sendData(self, obj):
        s = obj["id"]
        #make the short ID
        id = s[0:2] + ":" + s[2:4]
        chData = obj["values"]
        for i in chData:
            self.sendtodbLora(id, i, chData[i], 0, "ilora")


    def ilora_sync(self, name, value):
        self.sendtodb("connected", "true", 0)
        #do anything here you want to synce your data (channel name is sync)
        return True
    
    def parseLoraData(self, data, ser):
        if data[0:2] == "41":
            id = data[2:6]
            if id in self.gatewayNewTimes:
                interval = self.gatewayNewTimes[id]
                del self.gatewayNewTimes[id]
                print ""
                print ""
                print "settings update success!!"
                print ""
                print ""
                self.sendtodbLora(id, "interval", str(interval), 0, "ilora")
                self.sendtodbLora(id, "sinterval", "No Pending Changes", 0, "ilora")
                
            return id
        scale = 16
        id = data[4:8]
        print "here is the id:  ", id
        if id not in self.analogData:
            print "new device found!!!!!!!!!!"
            self.analogData[id] = copy.deepcopy(nodeDefaults)
            #update persistant dictionary
            with open('/root/python_firmware/drivers/LoRa_analogData.p', 'wb') as handle:
                pickle.dump(self.analogData, handle)

        key = {
            1: "a1",
            2: "cl1",
            3: "a2",
            4: "cl2",
            5: "temp",
            6: "batt"
            }
        channels = {}
        #first get the ack i/o
        if data[0:2] == "04":
            sendAck = True
        else:
            sendAck = False
        if sendAck:
            #check and see if there are pending changes
            #this is where I delete the pendig change from the staging interval
            if id in self.gatewayNewTimes:
                interval = self.gatewayNewTimes[id]
                ack = self.makeIntervalACK(id, interval)
                #ack = self.makeIntervalACK(id, "30,5,30,1111")
                print "sending...  ", ack.upper()
                #clear buffer:
                ser.readline()
                ser.write("radio tx " + ack.upper() + "\r\n")
                loopCount = 0
                a = ser.readline()
                while "ok" not in a:
                    loopCount += 1
                    if loopCount > 60:
                        break
                    time.sleep(.05)
                    a = ser.readline()

                ser.write("radio rx 0\r\n")
                loopCount = 0
                a = ser.readline()
                while "ok" not in a:
                    loopCount += 1
                    if loopCount > 60:
                        break
                    time.sleep(.05)
                    a = ser.readline()
            else:
                print "sending small ack"
                ser.write("radio tx " + "41" + id  + "\r\n")
                #clear buffer:
                ser.readline()
                loopCount = 0
                a = ser.readline()
                while "ok" not in a:
                    loopCount += 1
                    if loopCount > 60:
                        break
                    time.sleep(.05)
                    a = ser.readline()

                ser.write("radio rx 0\r\n")
                loopCount = 0
                a = ser.readline()
                while "ok" not in a:
                    loopCount += 1
                    if loopCount > 60:
                        break
                    time.sleep(.05)
                    a = ser.readline()
        bits = bin(int(data[2:4], scale))[2:].zfill(8)
        bits = bits[2:][::-1]
        place = 1
        bitCount = 1
        print bits
        for bit in bits:
            print place
            if bit == "1":
                val = str(struct.unpack('<f', binascii.a2b_hex(data[(8 * bitCount):((8 * bitCount) + 8)]))[0])
                if place == 2 or place == 4:
                    val = round(float(val) * 1000, 4)
                else:
                    val = round(float(val), 4)
                channels[key[place]] = val
                bitCount += 1
            place += 1
        self.processData(id,channels)

        for chan in channels:
            self.sendtodbLora(id, chan + "-v", channels[chan], 0, "ilora")
        print sendAck, id, channels
        
        return id

    def processData(self, id, channels):
        #we send every time, no need to check timestamps
        #lets for now keep a running list of last 10 sends in the last send list
        #1. do trasnform to get real units value
        #2. if there is a tank type selected, calculate gallons
        ignore_data = ["batt","temp"]
        for item in channels:
            if item in ignore_data:
                continue
            if item in self.analogData[id]:
                print channels
                #get its value, its last value, its required change amount, and its last time it sent
                val = float(channels[item])
                units_high = float(self.analogData[id][item]["uval"])
                units_low = float(self.analogData[id][item]["lval"])
                volts_high = float(self.analogData[id][item]["uvolts"])
                volts_low = float(self.analogData[id][item]["lvolts"])

                val = round(((units_high - units_low) / (volts_high - volts_low) * (val - volts_low)) + units_low, 2)
                self.sendtodbLora(id, (item), val, 0, "ilora")
                try:
                    type = float(self.analogData[id][item]["type"])
                    diameter_ft = float(self.analogData[id][item]["diameter-ft"])
                    width_ft = float(self.analogData[id][item]["width-ft"])
                    length_ft = float(self.analogData[id][item]["length-ft"])
                    diameter_in = float(self.analogData[id][item]["diameter-in"])
                    width_in = float(self.analogData[id][item]["width-in"])
                    length_in = float(self.analogData[id][item]["length-in"])
                    gallons = float(self.analogData[id][item]["gallons"])
                except:
                    print "no tank data"
                    continue
                


                try:
                    if type == "rectangular":
                        length =  (float(length_in) / 12) + float(length_ft)
                        width =  (float(width_in) / 12) + float(width_ft)
                        height = float(val)
                        volumeCubicFeet = length * width * height
                        gallons = round(7.48052 * volumeCubicFeet, 2)
                        self.sendtodbLora(id, (item + "-gallons"), gallons, 0, "ilora")
                    elif type == "cylindrical":
                        diameter =  (float(diameter_in) / 12) + float(diameter_ft)
                        height = float(val)
                        volumeCubicFeet = 3.14159265 * (diameter / 2)**2 * height
                        gallons = round(7.48052 * volumeCubicFeet, 2)
                        self.sendtodbLora(id, (item + "-gallons"), gallons, 0, "ilora")
                    elif type == "horizontal":
                        import  math
                        r =  ((float(diameter_in) / 12) + float(diameter_ft)) / 2
                        length =  (float(length_in) / 12) + float(length_ft)
                        height = float(val)
                        volumeCubicFeet = length*(r**2 * math.acos( (r-height)/r )- (r-height)* math.sqrt(2*height*r-height**2) )
                        gallons = round(7.48052 * volumeCubicFeet, 2)
                        self.sendtodbLora(id, (item + "-gallons"), gallons, 0, "stnk")
                except:
                    pass

                last_val = self.analogData[id][item]["last_value"]
                last_time = float(self.analogData[id][item]["last_send_time"])





                self.analogData[id][item]["last_value"] = val
                self.analogData[id][item]["last_send_time"] = time.time()
                




