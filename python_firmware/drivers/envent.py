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
import minimalmodbusTF as minimalmodbus


onOff = {
    0: "Off",
    1: "On"
    }



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
        self.chName = "gdsd" + '_[' + mac + ':'
        print 'device name is:'
        print self.deviceName
        mac2 = mac.replace(":", "")
        self.mac = mac2.upper()
        self.address = 1
        self.debug = True
        self.mcu = mcu
        self.firstRun = True
        self.version = "2"
        
        
        #empty placeholders for the bitarrays
        self.lastLong = ""
        self.lastLat = ""
        
        self.register()
        
        self.last_almnodes = ""
        connected = False
        while not connected:
            try:
                #make the serial connection:
                self.instrument = minimalmodbus.Instrument('/dev/ttyUSB4', 1) # port name, slave address (in decimal)
                self.instrument.debug = True
                self.instrument.serial.port          # this is the serial port name
                #self.instrument.serial.parity   = serial.PARITY_NONE
                #self.instrument.serial.xonxoff = False
                self.instrument.serial.baudrate = 9600   # Baud
                self.instrument.serial.bytesize = 8
                self.instrument.serial.stopbits = 1
                self.instrument.serial.timeout  = 2 # seconds
                self.instrument.address = 8
                connected = True
            except Exception,e:
                try:
                    print "#######################"
                    print e
                    print "trying USB 0"
                    #make the serial connection:
                    self.instrument = minimalmodbus.Instrument('/dev/ttyUSB0', 1) # port name, slave address (in decimal)
                    self.instrument.debug = True
                    self.instrument.serial.port          # this is the serial port name
                    #self.instrument.serial.parity   = serial.PARITY_NONE
                    #self.instrument.serial.xonxoff = False
                    self.instrument.serial.baudrate = 9600   # Baud
                    self.instrument.serial.bytesize = 8
                    self.instrument.serial.stopbits = 1
                    self.instrument.serial.timeout  = 2 # seconds
                    self.instrument.address = 8
                    connected = True
                except:
                    time.sleep(10)


        
        

        self.finished = threading.Event()
        threading.Thread.start(self)
        
    #this is a required function for all drivers, its goal is to upload some piece of data
    #about your device so it can be seen on the web
    def register(self):
        self.sendtodb("connected", "True", 0)
        self.last_values = {
        'mvzs1': "",
        'sas1': "",
        'mvsas1': "",
        'eas1': "",
        'mvses1': "",
        'ocs1': "",
        'ics2': "",
        'mvzs2': "",
        'sas2': "",
        'mvsas2': "",
        'eas2': "",
        'mvses2': "",
        'r1': "",
        'r2': "",
        'r4': "",
        'lt': "",

        }
        self.count = 3002

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
                    self.sendtodb("gps", value, 0)
            self.lastLat = googlelat
            self.lastLong = googlelong
            ser.close()
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
            self.sendtodb("signal", str(response), 0)
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
       
        self.count = 3001
        while not self.finished.isSet():
            
            try:
               
                print "################################"
                print "#############sending data ######"
               
                try:
                    data = self.instrument.read_registers(7001, 12, functioncode=3) # Registernumber, number of decimals
                    print data

                    currentValues = {}

                    currentValues['mvzs1'] = str(  round(float(data[0]))  )
                    currentValues['sas1'] = str(  round(float(data[1]))  )
                    currentValues['mvsas1'] = str(  round(float(data[2]))  )
                    currentValues['eas1'] = str(  round(float(data[3]), 1)  )
                    currentValues['mvses1'] = str(  round(float(data[4]))  )
                    currentValues['ocs1'] = str(  round(float(data[5]), 1)  )
                    currentValues['ics2'] = str(  round(float(data[6]), 1)  )
                    currentValues['mvzs2'] = str(  round(float(data[7]))  )
                    currentValues['sas2'] = str(  round(float(data[8]), 1)  )
                    currentValues['mvsas2'] = str(  round(float(data[9]))  )
                    currentValues['eas2'] = str(  round(float(data[10]))  )
                    currentValues['mvses2'] = str(  round(float(data[11]))  )

                    r1 = onOff[int(self.instrument.read_bit(1005, functioncode=1))]
                    r2 = onOff[int(self.instrument.read_bit(1006, functioncode=1))] 
                    r4 = onOff[int(self.instrument.read_bit(1008, functioncode=1))] 
                    lowtape = onOff[int(self.instrument.read_bit(1012, functioncode=1))]

                    currentValues['r1'] = r1
                    currentValues['r2'] = r2
                    currentValues['r4'] = r4
                    currentValues['lt'] = lowtape


                    for i in currentValues:
                        if currentValues[i] != self.last_values[i]:
                            self.sendtodb(i, str(currentValues[i]), 0)

                    self.last_values = currentValues


                    
                    
                except Exception,e: 
                    #self.sendtodb("error", str(e), 0)
                    print(str(e))
                    

                

                
                
                if self.count > 3000:
                    self.count = 0
                    try:
                        self.gps()
                        self.signal()
                        self.checkTemp()
                        
                    except:
                        pass
            except Exception,e: print(str(e))
    
    
    


    


                    
                
            
    
    
    
                   
                
    

    
    

    
    
    # internal functions & classes

    

    def envent_signal(self, name, value):
        self.signal()
        return True
        
    def envent_sync(self, name, value):
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
    
    
    def getTime(self):
        return str(int(time.time() + int(self.offset)))
   
