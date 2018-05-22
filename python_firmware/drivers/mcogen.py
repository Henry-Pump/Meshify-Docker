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
try:
    import json
except:
    import simplejson as json


_NUMBER_OF_BYTES_PER_REGISTER = 2


errorMap = {
    0: "Disabled Input",
    1: "Not active alarm",
    2: "Warning alarm",
    3: "Shutdown alarm",
    4: "Electrical trip alarm",
    8: "Inactive Indication (no string)",
    9: "Inactive Indication (displayed string)",
    10: "Active indication",
    15: "Unimplemented alarm"
}

errorList = [
{"Emergency stop": ""},
{"Low oil pressure": ""},
{"High coolant temperature": ""},
{"Low coolant temperature": ""},
{"Under speed": ""},
{"Over speed": ""},
{"Generator Under frequency": ""},
{"Generator Over frequency": ""},
{"Generator low voltage": ""},
{"Generator high voltage": ""},
{"Battery low voltage": ""},
{"Battery high voltage": ""},
{"Charge alternator failure": ""},
{"Fail to start": ""},
{"Fail to stop": ""},
{"Generator fail to close": ""},
{"Mains fail to close": ""},
{"Oil pressure sender fault": ""},
{"Loss of magnetic pick up": ""},
{"Magnetic pick up open circuit": ""},
{"Generator high current": ""},
{"Calibration lost": ""},
{"Low fuel level": ""},
{"CAN ECU Warning": ""},
{"CAN ECU Shutdown": ""},
{"CAN ECU Data fail": ""},
{"Low oil level switch": ""},
{"High temperature switch": ""},
{"Low fuel level switch": ""},
{"Expansion unit watchdog alarm": ""},
{"kW overload alarm": ""},
{"Negative phase sequence current alarm": ""}, 
{"Earth fault trip alarm": ""},
{"Generator phase rotation alarm": ""},
{"Auto Voltage Sense Fail": ""},
{"Maintenance alarm": ""},
{"Loading frequency alarm": ""},
{"Loading voltage alarm": ""},
{"Fuel usage running": ""},
{"Fuel usage stopped": ""},
{"Protections disabled": ""},
{"Protections blocked": ""},
{"Generator breaker failed to open": ""},
{"Mains breaker failed to open": ""},
{"Bus breaker failed to close": ""},
{"Bus breaker failed to open": ""},
{"Generator reverse power alarm": ""},
{"Short circuit alarm": ""},
{"Air flap closed alarm": ""},
{"Failure to sync": ""},
{"Bus live": ""},
{"Bus not live": ""},
{"Bus phase rotation": ""},
{"Priority selection error": ""},
{"MSC data error": ""},
{"MSC ID error": ""},
{"Bus low voltage": ""},
{"Bus high voltage": ""},
{"Bus low frequency": ""},
{"Bus high frequency": ""},
{"MSC failure": ""},
{"MSC too few sets": ""},
{"MSC alarms inhibited": ""},
{"MSC old version units on the bus": ""},
{"Mains reverse power alarmmains export alarm": ""},
{"Minimum sets not reached": ""},
{"Insufficient capacity": ""},
{"Out of sync": ""},
{"Alternative aux mains fail": ""},
{"Loss of excitation": ""},
{"Mains ROCOF": ""},
{"Mains vector shift": ""},
{"Mains decoupling low frequency": ""},
{"Mains decoupling high frequency": ""},
{"Mains decoupling low voltage": ""},
{"Mains decoupling high voltage": ""},
{"Mains decoupling combined alarm": ""},
{"Charge air temperature": ""},
{"Mains phase rotation alarm identifier": ""},
{"AVR Max Trim Limit alarm": ""},
{"High coolant temperature electrical trip alarm": ""},
{"Temperature sender open circuit alarm": ""},
{"Out of sync Bus": ""},
{"Out of sync Mains": ""},
{"Bus 1 live": ""},
{"Bus 1 phase rotation": ""},
{"Bus 2 live": ""},
{"Bus 2 phase rotation": ""},
{"Out of sync Mains (Aux Mains Fail)": ""},
{"ECU Protect": ""},
{"ECU Malfunction": ""},
{"ECU Information": ""},
{"ECU Shutdown": ""},
{"ECU Warning": ""},
{"ECU Electrical Trip": ""},
{"ECU Aftertreatment": ""},
{"Water In Fuel": ""},
{"ECU Heater": ""},
{"ECU Cooler": ""},
{"DC Total Watts Overload": ""},
{"High Plant Battery Temperature": ""},
{"Low Plant Battery Temperature": ""},
{"Low Plant Battery Voltage": ""},
{"High Plant Battery Voltage": ""},
{"Plant Battery Depth of Discharge": ""},
{"DC Battery Over Current": ""},
{"DC Load Over Current": ""},
{"High Total DC Current": ""},
{"High fuel level": ""},
{"Low kW Load (Wet Stacking)": ""},
{"null": ""},
{"mull": ""}

]



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
        print 'device name is:'
        print self.deviceName
        mac2 = mac.replace(":", "")
        self.mac = mac2.upper()
        self.address = 1
        self.debug = True
        self.mcu = mcu
        self.firstRun = True
        self.version = "43" 
        self.mqtt = mqtt
        #os.system("chmod 777 /root/reboot")
        

        self.lock = threading.Lock()

        #modbus dictionary for the ComBox
        #multiplier can be multiply or divide or None
        #changeType = number or percent
        #
        

        #try and grab the last gas meter read from flash
        



        

        

        #maps



        self.modeMap = {
            0:"Stop Mode",
            1:"Auto Mode",
            2:"Manual Mode",
            3:"Test on Load Mode",
            4:"Auto with manual restore mode/Prohibit Return",
            5:"User Config",
            6:"Test off Load Mode",
            65535:"Unimplemented"
            }

        self.register()

        self.finished = threading.Event()
        threading.Thread.start(self)
        
    #this is a required function for all drivers, its goal is to upload some piece of data
    #about your device so it can be seen on the web
    def register(self):
        self.sendtodb("connected", "True", 0)
        self.modbusDeepSea = {
            "op": {"length":16, "address":1024, "type":"int", "last_val":"", "multiplier":"multiply", "multiplierVal": "0.145037738", "changeType":"number", "change":4, "valueMap":None, "range":None},
            "rpm": {"length":16, "address":1030, "type":"int", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":100, "valueMap":None, "range":None},
            "ewt": {"length":16, "address":1025, "type":"int", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":6, "valueMap":None, "range":"0-100"},
            "av": {"length":16, "address":1028, "type":"int", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":2, "valueMap":None, "range":None},
            "sv": {"length":16, "address":1029, "type":"int", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":2, "valueMap":None, "range":None},
            "mode": {"length":16, "address":772, "type":"int", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":0, "valueMap":self.modeMap, "range":None},
            "sn": {"length":32, "address":770, "type":"int", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":0, "valueMap":None, "range":None},
            "mdl": {"length":16, "address":769, "type":"int", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":0, "valueMap":None, "range":None},
            "hrs": {"length":32, "address":1798, "type":"int", "last_val":"", "multiplier":"divide", "multiplierVal": "3600", "changeType":"number", "change":0.2, "valueMap":None, "range":None},
            "c1t": {"length":16, "address":1281, "type":"int", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":10, "valueMap":None, "range":None},
            "c2t": {"length":16, "address":1282, "type":"int", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":10, "valueMap":None, "range":None},
            "starts": {"length":32, "address":1808, "type":"int", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":0, "valueMap":None, "range":None}
            }

        self.modbusComBox = {
            "gri": {"length":32, "address":276, "type":"int", "last_val":"", "multiplier":"divide", "multiplierVal": "1000", "changeType":"number", "change":0.2, "valueMap":None, "range":None},
            "gro": {"length":32, "address":302, "type":"int", "last_val":"", "multiplier":"divide", "multiplierVal": "1000", "changeType":"number", "change":0.2, "valueMap":None, "range":None},
            "lo": {"length":32, "address":324, "type":"int", "last_val":"", "multiplier":"divide", "multiplierVal": "1000", "changeType":"number", "change":0.2, "valueMap":None, "range":None},
            "efb": {"length":32, "address":228, "type":"int", "last_val":"", "multiplier":"divide", "multiplierVal": "1000", "changeType":"number", "change":0.1, "valueMap":None, "range":None},
            "etb": {"length":32, "address":252, "type":"int", "last_val":"", "multiplier":"divide", "multiplierVal": "1000", "changeType":"number", "change":0.1, "valueMap":None, "range":None},
            "gei": {"length":32, "address":348, "type":"int", "last_val":"", "multiplier":"divide", "multiplierVal": "1000", "changeType":"number", "change":0.2, "valueMap":None, "range":None},
            "grsv": {"length":32, "address":376, "type":"int", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1, "valueMap":None, "range":None},
            "se": {"length":32, "address":354, "type":"int", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":0, "valueMap":None, "range":None},
            "grs": {"length":32, "address":435, "type":"int", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":0, "valueMap":None, "range":None},
            "ges": {"length":32, "address":440, "type":"int", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":0, "valueMap":None, "range":None},
            "grid": {"length":32, "address":102, "type":"ints", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":10, "valueMap":None, "range":None},
            "bat": {"length":32, "address":84, "type":"ints", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":10, "valueMap":None, "range":None},
            "load": {"length":32, "address":154, "type":"int", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":10, "valueMap":None, "range":None}
            }
        self.last_alarms = ""
        self.last_state = ""
        self.last_tct1 = ""
        self.last_tsp1 = ""
        self.last_tmd1 = ""
        self.last_tst1 = ""


        #self.count = 3001

    def stop (self):
        self.finished.set()
        self.join()
    
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
    
    def start(self):
        
        
        
        # you could add other ddo settings here
        thread.start_new_thread(self.loop, ())
        
    
    
    # def stop(): uses XBeeSerial.stop()
    
    
    ## Locally defined functions:



    def run(self):

        

        #on startup send the version number
        self.sendtodb("version", str(self.version), 0)
        self.sendtodb("log", "system start up", 0)

        connected = False

        while not connected:
            try:
                import minimalmodbusM1

        
                #set up rs485 for link to ComBox
                ans = False
                #make sure the baud rate gets set
                while ans == False:
                    ans = self.mcu.set485Baud(19200)
                    time.sleep(1)
                serial = self.mcu.rs485

                self.instrument1 = minimalmodbusM1.Instrument(10, serial)
                self.instrument1.address = 10

                #set up rs232 for link to DeapSea
                ans = False
                #make sure the baud rate gets set
                while ans == False:
                    ans = self.mcu.set232Baud(19200)
                    time.sleep(1)
                serial2 = self.mcu.rs232

                self.instrument2 = minimalmodbusM1.Instrument(10, serial2)
                self.instrument2.address = 10
                connected = True
                break

            except:
                print "failed to connect to M1 serial devices"
                time.sleep(20)
       
        self.count = 3001
        hb_count = 0

        try:
            with open('gas.pickle', 'rb') as gas:
               self.gas_offset = int(pickle.load(gas))
        except:
            self.gas_offset = 0
        
        
        self.last_pulses = self.gas_offset

        while not self.finished.isSet():
            self.count += 1
            
                
            try:
               
                print "################################"
                print "#############sending data ######"
               
                try:

                    connected = int(self.mqtt._state) 
                    if connected == 1:
                        pause = .1
                    else:
                        pause = 5


                    time.sleep(pause)

                    self.lock.acquire()
                    try:
                        self.processModbus(self.instrument1, self.modbusComBox)
                    except:
                        pass
                    try:
                        self.processModbus(self.instrument2, self.modbusDeepSea)
                    except:
                        pass

                    #this will make it easy to grab the register and end up with 4 charters that I can turn into integers 
                    #then map them to their values
                    try:
                        errors = self.instrument2.read_registers(int(39425), 28, functioncode=3)
                    except:
                        errors = []

                    self.lock.release()

                    errorLst = ""

                    count = 0

                    #each error reading will have 4 error codes in it
                    
                    for i in errors:
                        er = i
                        er = int(er)
                        er = hex(er)
                        er = str(er)
                        er = er[2:]


                        while len(er) < 4:
                            er = "0" + er
                        #now we have a 4 characater string
                        for char in er:
                            
                            #our error number is the int of the hex digit
                            erNum = int(char, 16)
                            #match up with the errorList for this number
                            errordict = errorList[count]
                            
                            #add 1 to our count
                            count += 1

                            for n in errordict:
                                name = n
                                last_value = errordict[n]
                                
                            #set the last value in the dictionary, this might be used later
                            errordict[n] = erNum

                            
                            #if its greater than 1, then itpys in some type of error state
                            if erNum > 1 and erNum != 15:
                                errorLst += name + ": " + errorMap[erNum] + ", "
                                

                    if errorLst == "":
                        errorLst = "No Alarms"

                    if errorLst != self.last_alarms:
                        self.sendtodb("alarms", errorLst, 0)
                        self.last_alarms = errorLst


                    #check the RPMs to determine the running state
                    rpms = self.modbusDeepSea['rpm']['last_val']
                    if rpms != "":
                        if int(rpms) > 0:
                            status = "Engine Running"
                        else:
                            status = "Engine Off"

                        if status != self.last_state:
                            self.sendtodb("stat", str(status), 0)
                            self.last_state = status

                    #grap some thermostat data
                    try:
                        for name, driver in self.nodes.iteritems():
                            try:
                                #dia is the name of the driver that manages all of the xbee devices
                                if name.startswith('dia'):
                                    ddm = driver.core.get_service("device_driver_manager")
                                    nodes = ddm.get_instance_list()
                                    for i in nodes:
                                        #thermostat is the name of all of the thermostats
                                        if i.startswith('therm'):
                                            node = ddm.get_driver_object(i)
                                            tct1 = node.property_get("current_temp").value
                                            tsp1 = node.property_get("spt").value
                                            tmd1 = node.property_get("mode").value
                                            tst1 = node.property_get("SS").value

                                            if tct1 != self.last_tct1:
                                                self.sendtodb("tct1", str(tct1), 0)
                                                self.last_tct1 = tct1

                                            if tsp1 != self.last_tsp1:
                                                self.sendtodb("tct1", str(tsp1), 0)
                                                self.last_tsp1 = tsp1

                                            if tmd1 != self.last_tmd1:
                                                self.sendtodb("tct1", str(tmd1), 0)
                                                self.last_tmd1 = tmd1

                                            if tst1 != self.last_tst1:
                                                self.sendtodb("tct1", str(tst1), 0)
                                                self.last_tst1 = tst1
                                        
                            except Exception,e:
                                print e

                    except Exception,e:
                        print e








                    

                    pulses = self.mcu.dataDict["pulse"]
                    pulses = int(pulses) + int(self.gas_offset)

                    if pulses != self.last_pulses:

                        self.sendtodb("ngs", str(pulses), 0)
                        self.last_pulses = pulses

                        #save the value to flash for storage
                        with open('gas.pickle', 'wb') as gas:
                            pickle.dump(str(pulses), gas)

                    #time.sleep(60)

                    #output = self.instrument.read_long(302, functioncode=3)
                    #self.sendtodb("energy_output", output, 0)
                    #time.sleep(30)
                    


                    

                    hb_count += 1
                    if hb_count > 600:
                        hb_count = 0
                        self.sendtodb("hb", "1", 0)
                except Exception,e: 
                    try:
                        self.lock.release()
                    except:
                        pass
                    print(str(e))
                    self.sendtodb("error", str(e), 0)

                

                
                
                if self.count > 3000:
                    self.count = 0
                    try:
                        pass
                    except:
                        pass
            except Exception,e: print(str(e))
    
    
   
    
            
    
    
    
    
    
    
    
    

    
    
    # internal functions & classes

    def processModbus(self, instrument, modbusDict):
       # "mdl": {"length":16, "address":769, "type":"int", "last_val":"", "multiplier":None, "multiplierVal": "1"},
        for chName in modbusDict:

            

            length = modbusDict[chName]['length']
            address = modbusDict[chName]['address']
            type = modbusDict[chName]['type']
            last_val = modbusDict[chName]['last_val']
            multiplier = modbusDict[chName]['multiplier']
            multiplierVal = modbusDict[chName]['multiplierVal']
            changeType = modbusDict[chName]['changeType']
            change = modbusDict[chName]['change']
            valueMap = modbusDict[chName]['valueMap']
            range = modbusDict[chName]['range']
            try:
                if range is not None:
                    high = range.split("-")[1]
                    low = range.split("-")[0]
            except:
                range = None

            if int(length) == 16:
                #must be normal read
                val = instrument.read_register(int(address), functioncode=3)
            elif int(length) == 32:
                #must be read long or read float
                if type == "int" or type == "ints":
                    val = instrument.read_long(int(address), functioncode=3)
                    if type == "ints":
                        val = self.int32(int(val))
                elif type == "float":
                    val = instrument.read_float(int(address), functioncode=3)
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
                            self.sendtodb(chName, valueMap[val], 0)
                        else:
                            self.sendtodb(chName, val, 0)
                        modbusDict[chName]['last_val'] = val
                        continue
                elif type == "str":
                    if val != last_val:
                        if valueMap != None:
                            self.sendtodb(chName, valueMap[val], 0)
                        else:
                            self.sendtodb(chName, val, 0)
                        modbusDict[chName]['last_val'] = val
                        continue
                elif abs(float(last_val) - float(val)) > change:
                    if valueMap != None:
                        self.sendtodb(chName, valueMap[val], 0)
                    else:
                        self.sendtodb(chName, val, 0)
                    modbusDict[chName]['last_val'] = val
    
    
    def mcogen_stop(self, name, value):
        self.lock.acquire()
        try:
            time.sleep(1)
            val = self.instrument2.read_registers(4096, 6, functioncode=3)
            time.sleep(1)
            self.instrument2.write_registers(4104, [35700, 29835])
        except:
            self.lock.release()
            return False
        try:
            self.lock.release()
        except:
            pass
        return True
                    
    def mcogen_auto(self, name, value):
        self.lock.acquire()
        try:
            time.sleep(1)
            val = self.instrument2.read_registers(4096, 6, functioncode=3)
            time.sleep(1)
            self.instrument2.write_registers(4104, [35701, 29834])
        except:
            self.lock.release()
            return False
        try:
            self.lock.release()
        except:
            pass
        return True
                    
    def mcogen_manual(self, name, value):
        self.lock.acquire()
        time.sleep(1)
        try:
            val = self.instrument2.read_registers(1028, 2, functioncode=3)
            time.sleep(1)
            self.instrument2.write_registers(4104, [35702, 29833])
        except Exception,e:
            self.sendtodb("error", str(e), 0)
            self.lock.release()
            return False
        try:
            self.lock.release()
        except:
            pass
        return True

    def mcogen_test(self, name, value):
        self.lock.acquire()
        time.sleep(1)
        try:
            val = self.instrument2.read_registers(4096, 6, functioncode=3)
            time.sleep(1)
            self.instrument2.write_registers(4104, [35703, 29832])
        except:
            self.lock.release()
            return False
        try:
            self.lock.release()
        except:
            pass
        return True

    def mcogen_start(self, name, value):

        self.lock.acquire()
        time.sleep(1)
        try:
            val = self.instrument2.read_registers(4096, 6, functioncode=3)
            time.sleep(1)
            self.instrument2.write_registers(4104, [35705, 29830])
        except:
            self.lock.release()
            return False
        try:
            self.lock.release()
        except:
            pass
        return True
    
    def mcogen_meterset(self, name, value):
        #we need to make it so the current offset + pulses = new value
        #using algebra know that this will work
        self.gas_offset = int(value) - int(self.mcu.dataDict["pulse"])
        return True
        
        pass               
                    
    def mcogen_sync(self, name, value):
        self.register()
        self.count = 3001
        return True
            
        
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
    
    def getTime(self):
        return str(int(time.time() + int(self.offset)))
   
