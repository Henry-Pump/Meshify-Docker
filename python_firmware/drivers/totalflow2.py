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
    
    def __init__(self, name=None, number=None, mac=None, Q=None, mcu=None, companyId=None, offset=None, mqtt=None):
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
        self.version = "1"
        
        
        #empty placeholders for the bitarrays
        self.ChannelOnList = ["1", "1", "1", "1", "1", "1", "1", "1", "1", "1", "1", "1", "1", "1", "1", "1", "1", "1", "1", "1", "1", "1", "1", "1", "1", "1", "1", "1", "1", "1", "1", "1"]
        self.last_alarm1 = ["", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""]
        self.last_alarm2 = ["", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""]
        self.last_alarm3 = ["", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""]
        self.last_Fault = ["", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""]
        self.last_LowBat = ["", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""]
        self.last_ChannelOn = ["", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""]
        self.last_ChannelCommError = ["", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""]
        self.lvlDict = {1:"0", 2:"0", 3:"0", 4:"0", 5:"0", 6:"0", 7:"0", 8:"0", 9:"0", 10:"0", 11:"0", 12:"0", 13:"0", 14:"0", 15:"0", 16:"0", 17:"0", 18:"0", 19:"0", 20:"0", 21:"0", 22:"0", 23:"0", 24:"0", 25:"0", 26:"0", 27:"0", 28:"0", 29:"0", 30:"0", 31:"0", 32:"0"}
        self.nameDict = {1:"0", 2:"0", 3:"0", 4:"0", 5:"0", 6:"0", 7:"0", 8:"0", 9:"0", 10:"0", 11:"0", 12:"0", 13:"0", 14:"0", 15:"0", 16:"0", 17:"0", 18:"0", 19:"0", 20:"0", 21:"0", 22:"0", 23:"0", 24:"0", 25:"0", 26:"0", 27:"0", 28:"0", 29:"0", 30:"0", 31:"0", 32:"0"}
        self.lastLong = ""
        self.lastLat = ""
        self.gdsc_alarm1 = None
        self.gdsc_alarm2 = None
        self.gdsc_alarm3 = None

        self.last_almnodes = ""


        #make the serial connection:
        self.instrument = minimalmodbus.Instrument('/dev/ttyS2', 1) # port name, slave address (in decimal)
        self.instrument.debug = True
        self.instrument.serial.port          # this is the serial port name
        self.instrument.serial.parity   = serial.PARITY_NONE
        self.instrument.serial.xonxoff = False
        self.instrument.serial.baudrate = 19200   # Baud
        self.instrument.serial.bytesize = 8
        self.instrument.serial.stopbits = 1
        self.instrument.serial.timeout  = 2 # seconds
        self.instrument.address = 1

        
        
	
        self.finished = threading.Event()
        threading.Thread.start(self)
        
    #this is a required function for all drivers, its goal is to upload some piece of data
    #about your device so it can be seen on the web
    def register(self):
        self.sendtodb("connected", "true", 0)
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
            time.sleep(300)
            self.count += 1
            try:
               
                print "################################"
                print "#############sending data ######"
               
                try:
                    temperature = self.instrument.read_registers(7000, 5, functioncode=3) # Registernumber, number of decimals
                    print temperature
                    self.sendtodb("stpres", str(temperature[0]), 0)
                    self.sendtodb("difpres", str(temperature[1]), 0)
                    self.sendtodb("temperature", str(temperature[2]), 0)
                    self.sendtodb("flrt", str(temperature[3]), 0)
                    self.sendtodb("yvol", str(temperature[4]), 0)
                    
                except Exception,e: print(str(e))
                    

                

                
                
                if self.count > 3000:
                    self.count = 0
                    try:
                        self.gps()
                        self.signal()
                        self.checkTemp()
                        
                    except:
                        pass
            except Exception,e: print(str(e))
    
    
    


    def gdscAlarms(self):
        try:
            msg = ""
            alarm1 = 0
            alarm2 = 0
            alarm3 = 0
            for i in range(32):
                
                if self.ChannelOnList[i] != "1":
                    continue
                
                if self.last_alarm1[i] == "1":
                    alarm1 += 1

                if self.last_alarm2[i] == "1":
                    alarm2 += 1
      
                if self.last_alarm3[i] == "1":
                    alarm3 += 1

                
                count = 0
                local1 = ""
                local2 = ""
                local3 = ""
                if self.last_alarm1[i] == "1":
                    local1 = "1:"
                    count += 1
                if self.last_alarm2[i] == "1":
                    local2 = "2:"
                    count += 1                
                if self.last_alarm3[i] == "1":
                    local3 = "3"
                    count += 1
                if count > 0:
                    msg1 = str((self.nameDict[i + 1] + ": " + self.lvlDict[(i + 1)] + ","))
                    msg += msg1

            if msg == "":
                msg = "No Alarms"

            if self.last_almnodes != msg:
                self.sendtodb("almnodes", msg, 0)

            time.sleep(1)

            print alarm1, self.gdsc_alarm1, alarm2, self.gdsc_alarm2, alarm3, self.gdsc_alarm3 
            if alarm1 != self.gdsc_alarm1:
                self.sendtodb("alarm1", str(alarm1), 0)
            if alarm2 != self.gdsc_alarm2:
                self.sendtodb("alarm2", str(alarm2), 0)
            if alarm3 != self.gdsc_alarm3:
                self.sendtodb("alarm3", str(alarm3), 0)

            

            self.gdsc_alarm1 = alarm1
            self.gdsc_alarm2 = alarm2
            self.gdsc_alarm3 = alarm3
            self.last_almnodes = msg
        except Exception,e: print(str(e))
        

    def getNames(self, reg):
        
        
        for i in range(32):
            if self.ChannelOnList[i] != "1":
                continue
            try:
                
                subreg = (reg + (i * 8))
                print "############## here is the reg number"
                print subreg
                part1 = self.instrument.read_string(subreg, numberOfRegisters=2, functioncode=3)
                print part1
                #part1 = hex(int(part1)).split('x')[1].decode("hex")

                
                subreg += 2
                part2 = self.instrument.read_string(subreg, numberOfRegisters=2, functioncode=3)
                print part2
                #part2 = hex(int(part2)).split('x')[1].decode("hex")

                
                subreg += 2
                part3 = self.instrument.read_string(subreg,  numberOfRegisters=2, functioncode=3)
                print part3
                #part3 = hex(int(part3)).split('x')[1].decode("hex")

                
                subreg += 2
                part4 = self.instrument.read_string(subreg, numberOfRegisters=2,  functioncode=3)
                print part4
                #part4 = hex(int(part4)).split('x')[1].decode("hex")
                
                subreg += 2
                
                value = str(part1) + str(part2) + str(part3) + str(part4)

                if value != self.nameDict[(i + 1)]:
                    self.sendtodbCH(str(i + 1), "name", value, 0)
                   
                self.nameDict[i + 1] = value
            except:
                print "errer getting name"
                    
                
            
    
    
    def getlevel(self, reg): #reg = 33064
        
        
        for i in range(32):
            if self.ChannelOnList[i] != "1":
                continue
            try:
                newReg = (int(reg) + (i * 2))
                print newReg
                resp = self.instrument.read_float(newReg, functioncode=4)
                value = str(round(float(resp), 1))
                #value = str(resp)
                print "old value ", self.lvlDict[(i + 1)]
                print "new value ", value
                if value != self.lvlDict[(i + 1)]:
                    self.sendtodbCH(str((i + 1)), "lvl", value, 0)
                #update value for next time
                self.lvlDict[(i + 1)] = value
            except:
                print "errer getting level"
                   
                
    def getBitArray(self, reg, name, lastValue):
        lst = self.instrument.read_long(int(reg), functioncode=4)
        print "here is the raw modbus value: ", lst
        lst = int(lst)
        lst = list('{0:0b}'.format(lst))
        
        while len(lst) < 32:
            lst = ['0'] + lst
        
        print len(lst)
        
        lst = lst[::-1]
        print lastValue
        print lst
        channelcount = 1

        listcount = 0
        #last value is False on startup, so we send up all the data
        #if it is not false then we compare with the old data to see if its changed
        if lastValue == False:
            for i in range(32):
                print i
                if self.ChannelOnList[i] != "1":
                    continue
                if lst[i] == "0":
                    value = "Off"
                    self.sendtodbCH(str(i + 1), name, value, 0)
                elif lst[i] == "1":
                    value = "On"
                    self.sendtodbCH(str(i + 1), name, value, 0)
                    
                
        else:
            listcount = 0
            for i in range(32):
                print i
                if self.ChannelOnList[i] != "1":
                    continue
                try:
                    if lst[i] != lastValue[i]:
                        print "found new value"
                        print "channel count ", (i + 1)
                        print "listcount ", i
                        print "last value ", lastValue[i]
                        print "current value ", lst[i]
                        if lst[i] == "0":
                            value = "Off"
                            self.sendtodbCH(str(i + 1), name, value, 0)
                        elif lst[i] == "1":
                            value = "On"
                            self.sendtodbCH(str(i + 1), name, value, 0)
                        
                        continue
                            
                        
                except:
                    
                    continue
                
        return lst

    def channelEnabled(self):
        
        #here I want to return the total number of units that are turned on
        lst = self.instrument.read_long(34025, functioncode=4)

        lst = int(lst)
        lst = list('{0:0b}'.format(lst))
        
        while len(lst) < 32:
            lst = ['0'] + lst
        
        print len(lst)
        
        lst = lst[::-1]
        print "here are the ones that are on"
        print lst
        self.ChannelOnList = lst
        return

    def setRegister(self, name, value):
        NEW_DATA = int(value)
        NAME = name
        print NAME
        register = ModDict[NAME]
        print register
        if register.startswith("4"):
            try:
                register = register[2:]
                register = int(register)
                register = register - 1
                print "new reg value:"
                print register
                self.write_register(register, NEW_DATA, 0) # Registernumber, value, number of decimals for storage
                time.sleep(2)
            except:
                pass
            try:
                resp = self.read_register(register, numberOfDecimals=0, functioncode=3)
                print resp
                data.value = str(resp)
                self.sendtodb(name, value, 0)
            except:
                pass
    
    def readLevel(self):
        resp = self.read_registers(299, 5, functioncode=4)
        for x in range(0, 5):
            if x == 1:
                continue
            print ModList3[x]
            print resp[x]
            self.sendtodb(ModList3[x], str(resp[x]), 0)
            
    
    def readAll(self, data):
        try:
            #self.property_set("readALL", Sample(time.time(), "Ok", ""))
            resp = self.read_registers(399, 21, functioncode=3)
            for x in range(0, 21):
                if x == 18 or x == 19:
                    continue
                self.sendtodb(ModList1[x], str(resp[x]), 0)
            resp = self.read_registers(435, 10, functioncode=3)
            for x in range(0, 10):
                self.sendtodb(ModList2[x], str(resp[x]), 0)
            resp = self.read_registers(299, 5, functioncode=4)
            for x in range(0, 5):
                if x == 1:
                    continue
                self.sendtodb(ModList3[x], str(resp[x]), 0)
        except Exception,e: print(str(e))
    
    
    
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

    

    def tfp_signal(self, name, value):
        self.signal()
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
   
