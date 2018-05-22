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
        self.chName = "at1" + '_[' + mac + ':'
        print 'device name is:'
        print self.deviceName
        mac2 = mac.replace(":", "")
        self.mac = mac2.upper()
        self.address = 1
        self.debug = True
        self.mcu = mcu
        self.firstRun = True
        self.version = "15"
        self.mqtt = mqtt
        self.maxRegister = 65
        
        
        #empty placeholders for the last values
        self.register()


        #make the serial connection:
        try:
            self.instrument = minimalmodbus.Instrument('/dev/ttyUSB0', 1) # port name, slave address (in decimal)
            self.instrument.debug = True
            self.instrument.serial.port          # this is the serial port name
            self.instrument.serial.parity   = serial.PARITY_NONE
            self.instrument.serial.xonxoff = False
            self.instrument.serial.baudrate = 9600   # Baud
            self.instrument.serial.bytesize = 8
            self.instrument.serial.stopbits = 1
            self.instrument.serial.timeout  = 1 # seconds
            self.instrument.address = 2
        except Exception,e:
            self.sendtodb("error", str(e), 0)

        
        
        self.finished = threading.Event()
        threading.Thread.start(self)
        
    #this is a required function for all drivers, its goal is to upload some piece of data
    #about your device so it can be seen on the web
    def register(self):
        self.sendtodb("connected", "True", 0)
        self.last_wlevel = {}
        self.last_tlevel = {}
        self.last_temp = {}
        self.last_overFlow = {}

        for i in range(10, self.maxRegister):
            self.last_wlevel[i] = 0
            self.last_tlevel[i] = 0
            self.last_temp[i] = 0
            self.last_overFlow[i] = ""

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



    


    def gps(self):
        try:
            resp = False
            ser = serial.Serial(port='/dev/ttyS3', baudrate=9600, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, xonxoff=False)
            ser.open
            time.sleep(2)
            
            ser.flushInput() #flush input buffer, discarding all its contents
            ser.flushOutput()#flush output buffer, aborting current output
            time.sleep(1)
            response = ser.readline()
            print response
            latNeg = ""
            longNeg = ""
            if response.split(',')[0] == "$GPRMC":
                lat = response.split(',')[3]
                if response.split(',')[4] == "S":
                    latNeg = "-"
                longitude = response.split(',')[5]
                if response.split(',')[6] == "W":
                    longNeg = "-"
            elif response.split(',')[0] == "$GPGGA":
                lat = response.split(',')[2]
                if response.split(',')[3] == "S":
                    latNeg = "-"
                longitude = response.split(',')[4]
                if response.split(',')[5] == "W":
                    longNeg = "-"
            else:
                return

            googlelat = (latNeg + str(((int(lat.split(".")[0][:2])) + ( float(((lat.split(".")[0][-2:]) + "." + lat.split(".")[1]))  / 60) )))                    
            googlelong = (longNeg +  str(((int(longitude.split(".")[0][:3])) + ( float(((longitude.split(".")[0][-2:]) + "." + longitude.split(".")[1]))  / 60) )))
            googlelat = str(round(float(googlelat), 4))
            googlelong = str(round(float(googlelong), 4))
            
            if googlelat != self.lastLat or googlelong != self.lastLong:
                
                
                print googlelat, googlelong
                value = googlelat + "," + googlelong
                if value != "24.0,121.0" and value!= "0.0,0.0":
                    resp = True
                    self.sendtodb("gps", value, 0)
                else:
                    resp = False
            self.lastLat = googlelat
            self.lastLong = googlelong
            ser.close()
            return resp
        except Exception,e:
            print e
            try:
                ser.close()
            except:
                pass
            pass
        

    def signal(self):
        try:
            ser = serial.Serial(port='/dev/modem_at1', timeout=2, baudrate=9600, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, xonxoff=False)
            ser.open
            time.sleep(2)
            
            ser.flushInput() #flush input buffer, discarding all its contents
            ser.flushOutput()#flush output buffer, aborting current output
            time.sleep(.5)

            ser.write("AT+CSQ" + chr(13))

            print("write data: AT+CSQ")

            time.sleep(0.5)
            response = ser.readlines()
            response = response[1].split(",")[0].replace("+CSQ:", "").strip()
            response = (-113 + (int(response) * 2)) 
            print response
            ser.close()

            return str(response)
            #self.sendtodb("signal", str(response), 0)
        except:
            try:
                ser.close()
            except:
                pass
            pass
        

    def checkTemp(self):
        temp = os.popen('/usr/sbin/mts-io-sysfs show board-temperature')
        temp1 = temp.read()
        temp1 = temp1.strip()
        self.sendtodb("temp", temp1, 0)
        temp.close()

    def run(self):

        

        #on startup send the version number
        self.sendtodb("version", str(self.version), 0)
        self.sendtodb("log", "Tank Level Start Up", 0)
       
        self.count = 3001
        hb_count = 0
        while not self.finished.isSet():
            self.count += 1
            
                
            try:
                for i in range(10, self.maxRegister):

                    print "################################"
                    print "#############sending data ######"
               
                    try:
                        self.instrument.address = i
                        connected = int(self.mqtt._state) 
                        if connected == 1:
                            pause = .1
                        else:
                            pause = 5

                        time.sleep(pause)
                    
                        tlevel = self.instrument.read_float(1, functioncode=3) # Registernumber, number of decimals
                        tlevel = round(tlevel, 1)
                        print tlevel
                        if tlevel != self.last_tlevel[i]:
                            self.sendtodbCH(str(i), "tlevel", str(tlevel), 0)
                        self.last_tlevel[i] = tlevel
                    
                        time.sleep(pause)
                    
                        wlevel = self.instrument.read_float(3, functioncode=3) # Registernumber, number of decimals
                        wlevel = round(wlevel, 1)
                        print wlevel
                        if wlevel != self.last_wlevel[i]:
                            self.sendtodbCH(str(i), "wlevel", str(wlevel), 0)
                        self.last_wlevel[i] = wlevel

                        time.sleep(pause)

                    
                        temp = self.instrument.read_float(5, functioncode=3) # Registernumber, number of decimals
                        temp = int(temp)
                        print temp
                        if abs(temp - self.last_temp[i]) > 1:
                            self.sendtodbCH(str(i), "temp", str(temp), 0)
                            self.last_temp[i] = temp

                        overflow = self.instrument.read_float(7, functioncode=3) # Registernumber, number of decimals
                        overflow = int(overflow)
                        print overflow
                        if overFlow == 1:
                            overFlow = "On"
                        elif overFlow == 0:
                            overFlow = "Off"
                        if overFlow != self.last_overFlow[i]:
                            self.sendtodbCH(str(i), "high", str(overFlow), 0)
                            self.last_overFlow[i] = overFlow




                        if self.count > 3000: 
                            sig = self.signal()
                            self.sendtodbCH(str(i), "signal", str(sig), 0)
                    

                   

                    except Exception,e:
                        print e
                        #self.sendtodb("error", str(e), 0)

                

                
                
                if self.count > 3000:
                    self.count = 0
                    
                    try:
                        for i in range(10, self.maxRegister):
                            self.last_wlevel[i] = 0
                            self.last_tlevel[i] = 0
                            self.last_temp[i] = 0
                    except:
                        pass
            
            except Exception,e:
                self.sendtodb("error", str(e), 0)
    
    
    
    def getModbus(self):
        return self.modbusData

    

    
    
    
    
    
    def readRegister(self, value):
        
        self.sendtodb("readRegister", value, 0)
        register = data.value
        print "here is the reg value"
        print register
        if register.startswith("3"):
            register = register[2:]
            register = int(register)
            register = register - 1
            print "new reg value:"
            print register
            resp = self.read_register(register, 0, functioncode=4)
            print resp
        elif register.startswith("4"):
            register = register[2:]
            register = int(register)
            register = register - 1
            print "new reg value:"
            print register
            resp = self.read_registers(register, 20, functioncode=3)
            print resp
    
    

    
    
    # internal functions & classes


    def atw_sync(self, name, value):
        self.sendtodb("connected", "true", 0)
        self.register()
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
    
    
    def getTime(self):
        return str(int(time.time() + int(self.offset)))
   
