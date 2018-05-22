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
import minimalmodbusM1
import pickle
import json
import vpn




_NUMBER_OF_BYTES_PER_REGISTER = 2





class start(threading.Thread):
    """\
        This class extends one of our base classes and is intended as an
        example of a concrete, example implementation, but it is not itself
        meant to be included as part of our developer API. Please consult the
        base class documentation for the API and the source code for this file
        for an example implementation.
        
        """
    
    # here are the setting defaults
    DEF_HEXDEC = True
    DEF_EOLN = None
    DEF_CHARTOUT = 2.0
    
    # a sanity value to prevent an infinite rcv_buffer creation
    DEF_MAX_READ = 1000
    
    def __init__(self, name=None, number=None, mac=None, Q=None, mcu=None, companyId=None, offset=None, mqtt=None, Nodes=None):
        threading.Thread.__init__(self)
        self.daemon = True
        self.offset = offset
        self.company = companyId
        self.name = name
        self.number = number 
        self.q = Q
        self.deviceName = name + '_[' + mac +  ':' + number[0:2] + ':' + number[2:] + ']!'
        self.chName = "mcogen" + '_[' + mac + ':'
        self.chName2 = '_[' + mac + ':'
        print 'device name is:'
        print self.deviceName
        mac2 = mac.replace(":", "")
        self.mac = mac2.upper()
        self.address = 1
        self.debug = True
        self.mcu = mcu
        self.firstRun = True
        self.version = "3" 
        self.mqtt = mqtt
        os.system("chmod 777 /root/reboot")
        self.vpn = vpn.vpn()
        
        self.modbusInterfaces = {}
        self.lock = threading.Lock()

        #modbus dictionary for the ComBox
        #multiplier can be multiply or divide or None
        #changeType = number or percent
        #
        



        self.IOmap = {
            "1":"On",
            1:"On",
            0:"Off",
            "0":"Off"
            }
        try:
            with open('/root/python_firmware/drivers/modbusMap.p', 'rb') as handle:
                self.modbusMap = pickle.load(handle)
                
            print "found pickled dictionary"
            print self.modbusMap
        except:
            print "couldn't load modbusMap from pickle"
           
            self.modbusMap = { }
        self.register()

        self.finished = threading.Event()
        threading.Thread.start(self)
        
    #this is a required function for all drivers, its goal is to upload some piece of data
    #about your device so it can be seen on the web
    def register(self):
        self.sync = True
        self.sendtodb("connected", "True", 0)
        #{'c':'none','b':'9600','p':'none','s':'1','f':'Off'}
        

        with self.lock:
            self.syncModbus()
            for comport in self.modbusMap:
                for address in self.modbusMap[comport]["addresses"]:
                    for channelName in self.modbusMap[comport]["addresses"][address]:
                        self.modbusMap[comport]["addresses"][address][channelName]["la"] = ""
                
        


        self.forwardingMap = {
                            "1": {
                                                "port":"",
                                                "externalPort":"",
                                                "externalIP":""
                                            },
                            "2": {
                                                "port":"",
                                                "externalPort":"",
                                                "externalIP":""
                                            },
                            "3": {
                                                "port":"",
                                                "externalPort":"",
                                                "externalIP":""
                                            },
                            "4": {
                                                "port":"",
                                                "externalPort":"",
                                                "externalIP":""
                                            }
                
                            }
        
        self.last_alarms = ""
        self.last_state = ""
        self.last_tct1 = ""
        self.last_tsp1 = ""
        self.last_tmd1 = ""
        self.last_tst1 = ""

        self.vpnCheckUp()
        #self.count = 3001

    def stop (self):
        self.finished.set()
        self.join()
    

    def vpnCheckUp(self):
        try:
            for i in range(1,5):
                for channel in self.vpn.forwardingMap[str(i)]:
                    if self.vpn.forwardingMap[str(i)][channel] != self.forwardingMap[str(i)][channel]:
                        print "new value found in the vpn"
                        if channel == "port":
                            newchannel = ("port" + str(i))
                        elif channel == "externalPort":
                            newchannel = ("eport" + str(i))
                        elif channel == "externalIP":
                            newchannel = ("ip"  + str(i))
                       
                        self.sendtodb(str(newchannel), str(self.vpn.forwardingMap[str(i)][channel]), 0)
                        self.forwardingMap[str(i)][channel] = self.vpn.forwardingMap[str(i)][channel]
            self.sendtodb("vpnip", str(self.vpn.get_ip_address("tun0")), 0)
        except Exception,e:
            print "(&(*&(*&(*&(&(&&(&&(*&(&(*&(&(*"
            print e

        
    def sendtodbDev(self, ch, channel, value, timestamp, deviceName):


        if int(ch) < 10:
            ch = "0" + str(int(ch))

        dname = deviceName + self.chName2 + str(ch) + ":99]!"

        

        if int(timestamp) == 0:
            timestamp = self.getTime()
        
        topic = 'meshify/db/%s/%s/%s/%s' % (self.company, self.mac, dname, channel)
        print topic
        msg = """[ { "value":"%s", "timestamp":"%s" } ]""" % (str(value), str(timestamp))
        print msg
        self.q.put([topic, msg, 0])
        
    def sendtodbCH(self, ch, channel, value, timestamp):


        if int(ch) < 10:
            ch = "0" + str(ch)

        dname = self.chName + str(ch) + ":99]!"

        

        if int(timestamp) == 0:
            timestamp = self.getTime()
        
        topic = 'meshify/db/%s/%s/%s/%s' % (self.company, self.mac, dname, channel)
        print topic
        msg = """[ { "value":"%s", "timestamp":"%s" } ]""" % (str(value), str(timestamp))
        print msg
        self.q.put([topic, msg, 0])
    
    def sendtodb(self, channel, value, timestamp):

        if int(timestamp) == 0:
            timestamp = self.getTime()
            if timestamp < 1400499858:
                return
        
        topic = 'meshify/db/%s/%s/%s/%s' % (self.company, self.mac, self.deviceName, channel)
        print topic
        msg = """[ { "value":"%s", "timestamp":"%s" } ]""" % (str(value), str(timestamp))
        print msg
        self.q.put([topic, msg, 0])
    
    def sendtodbJSON(self, channel, value, timestamp):

        if int(timestamp) == 0:
            timestamp = self.getTime()
            if timestamp < 1400499858:
                return
        
        topic = 'meshify/db/%s/%s/%s/%s' % (self.company, self.mac, self.deviceName, channel)
        print topic
        msg = """[ { "value":%s, "timestamp":"%s" } ]""" % (str(value), str(timestamp))
        print msg
        self.q.put([topic, msg, 0])
        
    def start(self):
        
        
        
        # you could add other ddo settings here
        thread.start_new_thread(self.loop, ())
        
    
    
    # def stop(): uses XBeeSerial.stop()
    
    
    ## Locally defined functions:



    def run(self):

        #on startup send the version number
        self.sendtodb("version", str(self.version), 0)
        self.sendtodb("log", "system start up", 0)


        self.last = {}
        try:
            self.currentDict = self.mcu.getDict()
            print "here is the dictionary ", self.currentDict
            self.last.update(self.currentDict)
            for item in self.currentDict:
                self.sendtodb(item, self.currentDict[item], 0)
        except:
            print "couldnt' get the dictionary from the mcu"

        while self.modbusInterfaces == {}:
            with self.lock:
                for com in self.modbusMap:
                    port = self.modbusMap[com]["c"]
                    if port not in self.modbusInterfaces:
                        if port == "M1-232":
                            baud = self.modbusMap[com]["b"]
                            if baud == "":
                                baud = 9600
                            else:
                                baud = int(baud)
                            #set up rs232 for link to DeapSea
                            connected = False
                            #make sure the baud rate gets set
                            while connected == False:
                                connected = self.mcu.set232Baud(baud)
                                time.sleep(1)
                            serial2 = self.mcu.rs232

                            self.instrument2 = minimalmodbusM1.Instrument(1, serial2)
                            self.instrument2.address = 1
                            self.modbusInterfaces[port] = self.instrument2
                            print "added M1 232 interface"
                        elif port == "M1-485":
                            baud = self.modbusMap[com]["b"]
                            if baud == "":
                                baud = 9600
                            else:
                                baud = int(baud)
                            #set up rs232 for link to DeapSea
                            connected = False
                            #make sure the baud rate gets set
                            while connected == False:
                                connected = self.mcu.set485Baud(baud)
                                time.sleep(1)
                            serial4 = self.mcu.rs485
                            
                            self.instrument1 = minimalmodbusM1.Instrument(1, serial4)
                            self.instrument1.address = 1
                            self.modbusInterfaces[port] = self.instrument1
                            print "added M1 485 interface"
                        elif port == "M1-MESH":
                            baud = self.modbusMap[com]["b"]
                            if baud == "":
                                baud = 9600
                            else:
                                baud = int(baud)
                            #set up rs232 for link to DeapSea
                            connected = False
                            #make sure the baud rate gets set
                            
                            serialX = self.mcu.xbee

                            self.instrument1 = minimalmodbusM1.Instrument(1, serialX)
                            self.instrument1.address = 1
                            self.modbusInterfaces[port] = self.instrument1
                            print "added M1 XBEE interface"
                        else:
                            connected = False
                            tries = 0
                            while not connected:
                                tries += 1
                                port = self.modbusMap[com]["c"]
                                baud = self.modbusMap[com]["b"]
                                if port == None or port == "none" or port == "None":
                                    connected = True
                                    continue
                                if baud == "":
                                    baud = 9600
                                else:
                                    baud = int(baud)
                                try:
                                    instrument = minimalmodbus.Instrument(port, 1) # port name, slave address (in decimal)
                                    instrument.serial.baudrate = baud
                                    instrument.serial.timeout  = 1 # seconds
                                    instrument.address = 1
                                    connected = True
                                    self.modbusInterfaces[port] = instrument
                                    print "added custom interface: " + port
                                    break
                                except Exception,e:
                                    if tries > 10:
                                        connected = True
                                        break
                                    self.sendtodb("error", str(e), 0)
                                    time.sleep(20)

            with self.lock:
                self.currentDict = self.mcu.getDict()
                for item in self.currentDict:
                    print "comparing ", self.currentDict[item], " to ", self.last[item]
                    if self.currentDict[item] != self.last[item]:
                        print "new value for: " + item
                        self.sendtodb(item, self.currentDict[item], 0)
                self.last.update(self.currentDict)
            time.sleep(30)


        

        time.sleep(10)
       
        self.count = 3001
        hb_count = 0
        while not self.finished.isSet():
            self.count += 1
            
                
            try:
               
                print "################################"
                print "#############sending data ######"
               
                try:
                    with self.lock:
                        self.processModbus()
                except Exception,e: 
                    print(str(e))
                    self.sendtodb("error", str(e), 0)


                with self.lock:
                    self.currentDict = self.mcu.getDict()
                    for item in self.currentDict:
                        if self.sync == True:
                            print "comparing ", self.currentDict[item], " to ", self.last[item]
                            if self.currentDict[item] != self.last[item]:
                                print "new value for: " + item
                                self.sendtodb(item, self.currentDict[item], 0)
                        else:
                            #update all values:
                            self.sendtodb(item, self.currentDict[item], 0)
                    if self.sync == True:
                        self.sync = False
                    self.last.update(self.currentDict)
                #time.sleep(10)
         
            except Exception,e: print(str(e))
    
    
   
    
            
    
    
    
    
    
    
    
    

    
    
    # internal functions & classes

    def processModbus(self):
       # "mdl": {"length":16, "address":769, "type":"int", "last_val":"", "multiplier":None, "multiplierVal": "1"},

        print "checking modbus"
        print self.modbusMap
        for com in self.modbusMap:


            for address in self.modbusMap[com]["addresses"]:
                #get the modbus instrument
                instrument = self.modbusInterfaces[self.modbusMap[com]["c"]]
                instrument.address = int(address)
                ch = address
                if int(ch) < 10:
                    ch = "0" + str(ch)

                for chName in self.modbusMap[com]["addresses"][address]:
                    
                    #"{'chn':'2-1-v','dn':'M1','da':'1','le':'16','a':'301','f':'3','t':'int','la':null,'m':'none','mv':'1','ct':'number','c':'1','vm':null,'r':'1-200','s':'On'}"
                    try:
                        status = self.modbusMap[com]["addresses"][address][chName]['s']

                        #if the status is no on, continue
                        if status != "On":
                            continue

                        deviceName = str(self.modbusMap[com]["addresses"][address][chName]['dn'])
                        functioncode = str(self.modbusMap[com]["addresses"][address][chName]['f'])
                        length = int(str(self.modbusMap[com]["addresses"][address][chName]['le']))
                        regAddress = int(str(self.modbusMap[com]["addresses"][address][chName]['a']))
                        type = str(self.modbusMap[com]["addresses"][address][chName]['t'])
                        last_val = self.modbusMap[com]["addresses"][address][chName]['la']
                        multiplier = str(self.modbusMap[com]["addresses"][address][chName]['m'])
                        multiplierVal = int(self.modbusMap[com]["addresses"][address][chName]['mv'])
                        changeType = str(self.modbusMap[com]["addresses"][address][chName]['ct'])
                        try:
                            change = int(str(self.modbusMap[com]["addresses"][address][chName]['c']))
                        except:
                            change = 0
                        valueMap = self.modbusMap[com]["addresses"][address][chName]['vm']
                        range = str(self.modbusMap[com]["addresses"][address][chName]['r'])
                        if multiplier == "none":
                            multiplier = None
                        if last_val == None or last_val == "none":
                            last_val = ""

                        try:
                            if range is not None:
                                high = range.split("-")[1]
                                low = range.split("-")[0]
                        except:
                            range = None

                        print multiplier, last_val, (str(last_val) == "")

                        #first check for coils:
                        if type == "coil":
                            val = instrument.read_bit(int(regAddress), functioncode=int(functioncode))

                        elif int(length) == 16 and type == "int":
                            #must be normal read
                            print "getting int"
                            val = instrument.read_register(int(regAddress), functioncode=int(functioncode))
                            print val
                        elif int(length) == 32 and type == "long":
                            #must be read long or read float
                            if type == "int" or type == "ints":
                                val = instrument.read_long(int(regAddress), functioncode=int(functioncode))
                                if type == "ints":
                                    val = self.int32(int(val))
                        elif type == "float" and int(length) == 32:
                            val = instrument.read_float(int(regAddress), functioncode=int(functioncode))
                        elif type == "floatbs" and int(length) == 32:
                            t = instrument.read_registers(int(regAddress), 2, functioncode=int(functioncode))
                            val = self.byteSwap32(t) 
                        else:
                            continue
                        #check if there is a multiplier
                        if multiplier != None:
                            if multiplier == "divide":
                                val = round(float((float(val) / float(multiplierVal))), 2)
                            elif multiplier == "multiply":
                                val = round(float((float(val) * float(multiplierVal))), 2)

                        #check and see if we have a range, if its outside the range then just ignore the data and continue
                        if range != None:
                            #validate the value is in the range
                            try:
                                if float(val) > float(high) or float(val) < float(low):
                                    continue
                            except:
                                print "validation error, skipping value"
                                continue


                        #check if the data has changed
                        if changeType == "number":
                            #compare last value with a change amount to see if we have enough change to send it
                            #first see if you have an empty string as the last value, if so its the first time and we don't need to compare, but just send the value
                            if str(last_val) == "":
                                if val != last_val:
                                    if valueMap != None:
                                        if deviceName != "M1":
                                            self.sendtodbDev(ch, chName, valueMap[str(val)], 0, deviceName)
                                        else:
                                            self.sendtodb(chName, valueMap[str(val)], 0)
                                    else:
                                        if deviceName != "M1":
                                            self.sendtodbDev(ch, chName, val, 0, deviceName)
                                        else:
                                            self.sendtodb(chName, val, 0)
                                    self.modbusMap[com]["addresses"][address][chName]['la'] = val
                                    continue
                            elif type == "str":
                                if val != last_val:
                                    if valueMap != None:
                                        if deviceName != "M1":
                                            self.sendtodbDev(ch, chName, valueMap[str(val)], 0, deviceName)
                                        else:
                                            self.sendtodb(chName, valueMap[str(val)], 0)
                                    else:
                                        if deviceName != "M1":
                                            self.sendtodbDev(ch, chName, val, 0, deviceName)
                                        else:
                                            self.sendtodb(chName, val, 0)
                                    self.modbusMap[com]["addresses"][address][chName]['la'] = val
                                    continue
                            elif type == "coil":
                                if val != last_val:
                                    if valueMap != None:
                                        if deviceName != "M1":
                                            self.sendtodbDev(ch, chName, valueMap[str(val)], 0, deviceName)
                                        else:
                                            self.sendtodb(chName, valueMap[str(val)], 0)
                                    else:
                                        if deviceName != "M1":
                                            self.sendtodbDev(ch, chName, val, 0, deviceName)
                                        else:
                                            self.sendtodb(chName, val, 0)
                                    self.modbusMap[com]["addresses"][address][chName]['la'] = val
                                    continue
                            elif type == "float" or type == "int":
                                if abs(float(last_val) - float(val)) > change:
                                    if valueMap != None:
                                        if deviceName != "M1":
                                            self.sendtodbDev(ch, chName, valueMap[str(val)], 0, deviceName)
                                        else:
                                            self.sendtodb(chName, valueMap[str(val)], 0)
                                    else:
                                        if deviceName != "M1":
                                            self.sendtodbDev(ch, chName, val, 0, deviceName)
                                        else:
                                            self.sendtodb(chName, val, 0)
                                    self.modbusMap[com]["addresses"][address][chName]['la'] = val
                    except Exception,e:
                        print "had an error on the modbus loop"
                        print(str(e))

                        continue
    
    
    
   
                    
    def M1_sync(self, name, value):
        self.register()
        self.count = 3001
        return True
    
    
    def syncModbus(self):
        #{'c':'none','b':'9600','p':'none','s':'1','f':'Off'}
        for comport in self.modbusMap:
            data = """{"c":"%s", "b":"%s", "p":"%s", "s":"%s", "f":"%s"}""" % (self.modbusMap[comport]["c"],self.modbusMap[comport]["b"],self.modbusMap[comport]["p"],self.modbusMap[comport]["s"],self.modbusMap[comport]["f"] )
            if comport == 1 or comport == "1":
                name = "2s"
            elif comport == 2 or comport == "2":
                name = "4s"
            self.sendtodbJSON(name, data, 0)
            for address in self.modbusMap[comport]["addresses"]:
                for channelName in self.modbusMap[comport]["addresses"][address]:
                    name = self.modbusMap[comport]["addresses"][address][channelName]["m1ch"]
                    self.sendtodbJSON(name, json.dumps(self.modbusMap[comport]["addresses"][address][channelName]), 0)


    
    def handleModbusEntry(self, name, value):

        if name.split("-")[0] == "2":
            com = "1"
        elif name.split("-")[0] == "4":
            com = "2"
        else:
            return False


            

        newVal = value.replace("'", '"')
        newJson = json.loads(newVal)

        #check here to see if this is a deletion 
        if "s" in newJson and not "a" in newJson and newJson["s"] == "Off":
            print "we have a delete request for the channel: " + name
            try:
                for comport in self.modbusMap:
                    for address in self.modbusMap[comport]["addresses"]:
                        for channelName in self.modbusMap[comport]["addresses"][address]:
                            if self.modbusMap[comport]["addresses"][address][channelName]["m1ch"] == name:
                                del self.modbusMap[comport]["addresses"][address][channelName]
                                self.sendtodb(name, "", 0)


                pass

            except:
                pass


        channelName = newJson["chn"]
        devAddress = newJson["da"]
        newJson["m1ch"] = name

        newEntry = {channelName : newJson}

        #first check and see if the address already exists 
        if devAddress in self.modbusMap[com]["addresses"]:
            #if it is here, then just add a new item to the dictionary
            self.modbusMap[com]["addresses"][devAddress][channelName] = newJson
            pass
        else:
            #make a new address entry for this com port
            self.modbusMap[com]["addresses"][devAddress] = newEntry

        self.sendtodbJSON(name, json.dumps(newJson), 0)
    
    def handleComSetup(self, name, value):
        print "I'm at location 10"
        if name == "2s" or name == "4s":

            if name == "2s":
                com = "1"
            elif name == "4s":
                com = "2"
            else:
                return False
            #this is the com settings for 232
            #looks like this:{'c':'M1-232','b':'9600','p':'none','s':'1','f':'Off'}
            #c = com port, b = baud, p = parity, s = stop bit, f = flow control

            print value

            #{'c':'none','b':'9600','p':'none','s':'1','f':'Off'}
            newVal = value.replace("'", '"')
            newJson = json.loads(newVal)
            print newJson

            

            port = newJson["c"]
            baud = newJson["b"]
            parity = newJson["p"]
            stopbit = newJson["s"]
            flow = newJson["f"]
            print "I'm at location 12"
            #update the interface:
            connected = False
            tries = 0



             #first check and see if the com port has been set up before
            if com in self.modbusMap:
            
                print "this com port is already here"
                #if the comport is already here, just change its settings and be on your way!
                self.modbusMap[com]["c"] = port
                self.modbusMap[com]["b"] = baud
                self.modbusMap[com]["p"] = parity
                self.modbusMap[com]["s"] = stopbit
                self.modbusMap[com]["f"] = flow
            else:
                #if its new we need to add it, but we need to make sure this is done before we try and add devices to it.
                self.modbusMap[com] = {
                    "c": port,
                    "b": baud,
                    "p":parity,
                    "s":stopbit,
                    "f":flow,
                    "addresses": {}
                    }



            if com == "1":

                while connected == False:
                    tries += 1
                    connected = self.mcu.set232Baud(int(baud))
                    time.sleep(1)
                    if tries > 10:
                        connected = True
                        break
            elif com == "2":
                while connected == False:
                    tries += 1
                    connected = self.mcu.set485Baud(int(baud))
                    time.sleep(1)
                    if tries > 10:
                        connected = True
                        break
            else:
                inst = self.modbusInterfaces[port]
                inst.serial.baudrate = baud
           
                     
            print "new com port setup"
            print "I'm at location 14"
            print self.modbusMap
            self.sendtodbJSON(name, json.dumps(newJson), 0)
            """self.modbusMap = { "M1-485": {
                                            "port": "/dev/ttySP4",
                                            "baud": "",
                                            "parity":"",
                                            "stopbits":"",
                                            "flowcontrol":"",
                                            "addresses": { 
                                                            "1": {"p4": {"reg":"299","length":32, "address":1, "functioncode":3, "type":"int", "last_val":"", "multiplier":None, "multiplierVal": 1, "changeType":"number", "change":0, "valueMap":None, "range":None}}
                                                          }
                                             }
                                  }
             
                                 """
    
    def genericSet(self, name, value, id):
        print "I'm at location 1"
        try:
            if name == "2s" or name == "4s":
                with self.lock:
                    print "I'm at location 2"
                    self.handleComSetup(name, value)

                    #update persistant dictionary
                    with open('/root/python_firmware/drivers/modbusMap.p', 'wb') as handle:
                        pickle.dump(self.modbusMap, handle)
                    return True

            try:

                print "I'm at location 3"
                if name.split("-")[2] == 'v':
                    #this is a channel set, for future use
                    pass
            except:
                pass

            #2-1","value":"{'chn':'2-1-v','dn':'M1','le':'16','a':'301','f':'3','t':'int','la':null,'m':'none','mv':'1','ct':'number','c':'1','vm':null,'r':'1-200','s':'On'}"
            if name.split("-")[0] == "2" or name.split("-")[0] == "4":
                with self.lock:
                    self.handleModbusEntry(name, value)
                    #update persistant dictionary
                    with open('/root/python_firmware/drivers/modbusMap.p', 'wb') as handle:
                        pickle.dump(self.modbusMap, handle)
                    return True

        except Exception,e:
            print(str(e))
            return False




    def M1_vpnpf(self, name, value):
        #value = "1,8080,192.168.1.2,80"

        v = value.split(",")

        if v[1] == "del":
            self.vpn.delForward(1)
            return True
        else:
            number = v[0]
            port = v[1]
            ip = v[2]
            exPort = v[3]
            self.vpn.addForward(number, port, exPort, ip)
            self.vpnCheckUp()
            return True



    def M1_vpn(self, name, value):
        try:
            #on,lewis@lewis.com,password,subnet,ip
            values = value.split(",")
            if values[0] == "On" or values[0] == "on" or values[0] == 1 or values[0] == "1":
                self.vpn.turnOn("", values[1], values[2], self.mac, values[3], values[4])
            elif values[0] == "Off" or values[0] == "off" or values[0] == 0 or values[0] == "0":
                self.vpn.turnOff()

            time.sleep(30)
            self.vpnCheckUp()
            self.sendtodb("vpn", value, 0)
        except Exception,e:
            print(str(e))
            self.sendtodb("error", str(e), 0)
        return True


    def M1_dout1(self, name, value):
        
        success = self.mcu.digitalOut1(str(value))
        self.sendtodb(name, str(value), 0)

        #return True/False
        return success
    
        
    def M1_dout2(self, name, value):
        success = self.mcu.digitalOut2(str(value))
        self.sendtodb(name, str(value), 0)

        #return True/False
        return success

    def M1_dout3(self, name, value):
        success = self.mcu.digitalOut3(str(value))
        self.sendtodb(name, str(value), 0)

        #return True/False
        return success
    
    def M1_dout4(self, name, value):
        success = self.mcu.digitalOut4(str(value))
        self.sendtodb(name, str(value), 0)

        #return True/False
        return success
        
    def M1_dout5(self, name, value):
        success = self.mcu.digitalOut5(str(value))
        self.sendtodb(name, str(value), 0)

        #return True/False
        return success

   
        
    def M1_relay2(self, name, value):
        success = self.mcu.relay2(value)
        self.sendtodb(name, str(value), 0)

        #return True/False
        return success


    
    def M1_relay1(self, name, value):
        success = self.mcu.relay1(value)
        self.sendtodb(name, str(value), 0)


        #return True/False
        return success

    def M1_reboot(self, name, value):
        os.system("reboot")

    def get_eoln(self):
        eoln = SettingsBase.get_setting(self, "eoln")
        if eoln is None:
            return None
        
        if eoln != self.__eoln_save:
            # cache result to avoid repeat processing of escapes
            self.__eoln_save = eoln
            self._eoln = strip_escapes(eoln)
        return self._eoln
    
    
    def int32(self, x):
        if x>0xFFFFFFFF:
            raise OverflowError
        if x>0x7FFFFFFF:
            x=int(0x100000000-x)
            if x<2147483648:
                return -x
            else:
                return -2147483648
        return x
    
    def byteSwap32(self, array):
        #array is a list of 2 dec numbers
        newVal = ""
        for i in array:
            i = hex(i).replace('0x', '')
            while len(i) < 4:
                i = "0" + i
            print i
            newVal = i + newVal 
        print newVal
        return struct.unpack('!f', newVal.decode('hex'))[0]
    def getTime(self):
        return str(int(time.time() + int(self.offset)))
   
