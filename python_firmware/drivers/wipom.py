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
        print 'device name is:'
        print self.deviceName
        mac2 = mac.replace(":", "")
        self.mac = mac2.upper()
        self.address = 1
        self.debug = True
        self.mcu = mcu
        self.firstRun = True
        self.version = "41" 
        self.mqtt = mqtt
        os.system("chmod 777 /root/reboot")
        

        self.lock = threading.Lock()

        #modbus dictionary for the ComBox
        #multiplier can be multiply or divide or None
        #changeType = number or percent
        #
        connected = False
        while not connected:
            try:
                self.instrument = minimalmodbus.Instrument('/dev/ttySP4', 1) # port name, slave address (in decimal)
                self.instrument.serial.baudrate = 115200
                self.instrument.serial.timeout  = .5 # seconds
                self.instrument.address = 1
                connected = True
                break
            except Exception,e:
                self.sendtodb("error", str(e), 0)
                time.sleep(10)

        #maps



        self.IOmap = {
            "1":"On",
            1:"On",
            0:"Off",
            "0":"Off"
            }

        self.register()

        self.finished = threading.Event()
        threading.Thread.start(self)
        
    #this is a required function for all drivers, its goal is to upload some piece of data
    #about your device so it can be seen on the web
    def register(self):
        self.sendtodb("connected", "True", 0)
        self.modbusWipom = {
            "di1": {"length":16, "address":0, "functioncode":2, "type":"coil", "last_val":"", "multiplier":None, "multiplierVal": 1, "changeType":"number", "change":0, "valueMap":self.IOmap, "range":None},
            "di2": {"length":16, "address":1, "functioncode":2, "type":"coil", "last_val":"", "multiplier":None, "multiplierVal": 1, "changeType":"number", "change":0, "valueMap":self.IOmap, "range":None},
            "di3": {"length":16, "address":2, "functioncode":2, "type":"coil", "last_val":"", "multiplier":None, "multiplierVal": 1, "changeType":"number", "change":0, "valueMap":self.IOmap, "range":None},
            "di4": {"length":16, "address":3, "functioncode":2, "type":"coil", "last_val":"", "multiplier":None, "multiplierVal": 1, "changeType":"number", "change":0, "valueMap":self.IOmap, "range":None},
            "do1": {"length":16, "address":0, "functioncode":1, "type":"coil", "last_val":"", "multiplier":None, "multiplierVal": 1, "changeType":"number", "change":0, "valueMap":self.IOmap, "range":None},
            "do2": {"length":16, "address":1, "functioncode":1, "type":"coil", "last_val":"", "multiplier":None, "multiplierVal": 1, "changeType":"number", "change":0, "valueMap":self.IOmap, "range":None},
            "ai1": {"length":16, "address":0, "functioncode":4, "type":"int", "last_val":"", "multiplier":None, "multiplierVal": 1, "changeType":"number", "change":0, "valueMap":None, "range":None},
            "ai2": {"length":16, "address":1, "functioncode":4, "type":"int", "last_val":"", "multiplier":None, "multiplierVal": 1, "changeType":"number", "change":0, "valueMap":None, "range":None},
            "ai3": {"length":16, "address":2, "functioncode":4, "type":"int", "last_val":"", "multiplier":None, "multiplierVal": 1, "changeType":"number", "change":0, "valueMap":None, "range":None},
            "ai4": {"length":16, "address":3, "functioncode":4, "type":"int", "last_val":"", "multiplier":None, "multiplierVal": 1, "changeType":"number", "change":0, "valueMap":None, "range":None},
            "ai5": {"length":16, "address":4, "functioncode":4, "type":"int", "last_val":"", "multiplier":None, "multiplierVal": 1, "changeType":"number", "change":0, "valueMap":None, "range":None},
            "ai6": {"length":16, "address":5, "functioncode":4, "type":"int", "last_val":"", "multiplier":None, "multiplierVal": 1, "changeType":"number", "change":0, "valueMap":None, "range":None},
            "ai7": {"length":16, "address":6, "functioncode":4, "type":"int", "last_val":"", "multiplier":None, "multiplierVal": 1, "changeType":"number", "change":0, "valueMap":None, "range":None},
            "f1": {"length":16, "address":112, "functioncode":3, "type":"int", "last_val":"", "multiplier":None, "multiplierVal": 1, "changeType":"number", "change":0, "valueMap":None, "range":None},
            "f2": {"length":16, "address":113, "functioncode":3, "type":"int", "last_val":"", "multiplier":None, "multiplierVal": 1, "changeType":"number", "change":0, "valueMap":None, "range":None},
            "p1": {"length":32, "address":121, "functioncode":3, "type":"int", "last_val":"", "multiplier":None, "multiplierVal": 1, "changeType":"number", "change":0, "valueMap":None, "range":None},
            "p2": {"length":32, "address":123, "functioncode":3, "type":"int", "last_val":"", "multiplier":None, "multiplierVal": 1, "changeType":"number", "change":0, "valueMap":None, "range":None},
            "p3": {"length":32, "address":125, "functioncode":3, "type":"int", "last_val":"", "multiplier":None, "multiplierVal": 1, "changeType":"number", "change":0, "valueMap":None, "range":None},
            "p4": {"length":32, "address":127, "functioncode":3, "type":"int", "last_val":"", "multiplier":None, "multiplierVal": 1, "changeType":"number", "change":0, "valueMap":None, "range":None},
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
                        self.processModbus(self.instrument, self.modbusWipom)

                except Exception,e: 
                   
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

            try:
                functioncode = modbusDict[chName]['functioncode']
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

                #first check for coils:
                if type == "coil":
                    val = instrument.read_bit(int(address), functioncode=int(functioncode))

                elif int(length) == 16 and type == "int":
                    #must be normal read
                    val = instrument.read_register(int(address), functioncode=int(functioncode))
                elif int(length) == 32 and type == "long":
                    #must be read long or read float
                    if type == "int" or type == "ints":
                        val = instrument.read_long(int(address), functioncode=int(functioncode))
                        if type == "ints":
                            val = self.int32(int(val))
                elif type == "float" and int(length ==32):
                    val = instrument.read_float(int(address), functioncode=int(functioncode))
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
                    elif type == "coil":
                        if val != last_val:
                            if valueMap != None:
                                self.sendtodb(chName, valueMap[val], 0)
                            else:
                                self.sendtodb(chName, val, 0)
                            modbusDict[chName]['last_val'] = val
                            continue
                    elif type == "float" or type == "int":
                        if abs(float(last_val) - float(val)) > change:
                            if valueMap != None:
                                self.sendtodb(chName, valueMap[val], 0)
                            else:
                                self.sendtodb(chName, val, 0)
                            modbusDict[chName]['last_val'] = val
            except Exception,e:
                print(str(e))
                continue
    
    def mcogen_stop(self, name, value):
        self.lock.acquire()
        try:
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
        try:
            val = self.instrument2.read_registers(4096, 6, functioncode=3)
            time.sleep(1)
            self.instrument2.write_registers(4104, [35702, 29833])
        except:
            self.lock.release()
            return False
        try:
            self.lock.release()
        except:
            pass
        return True

    def mcogen_test(self, name, value):
        self.lock.acquire()
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
    
    def wipom_do1(self, name, value):
        try:
            if value == "On" or value == "on" or value == 1 or value == "1":
                value = 1
            else:
                value = 0
            with self.lock:
                self.instrument.write_bit(0, int(value), functioncode=15)
            
        except Exception,e:
            print(str(e))
        
        return True               
    
    def wipom_do2(self, name, value):
        try:
            if value == "On" or value == "on" or value == 1 or value == "1":
                value = 1
            else:
                value = 0
            with self.lock:
                self.instrument.write_bit(1, int(value), functioncode=15)
        except Exception,e:
            print(str(e))
        return True    
                    
    def wipom_sync(self, name, value):
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
    
    
    def int32(x):
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
   
