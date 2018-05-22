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
        self.chName = "tsac" + '_[' + mac + ':'
        print 'device name is:'
        print self.deviceName
        mac2 = mac.replace(":", "")
        self.mac = mac2.upper()
        self.address = 1
        self.debug = True
        self.mcu = mcu
        self.firstRun = True
        self.version = "4"
        self.mqtt = mqtt
        
        
        self.register()

        


        #make the serial connection:
        self.instrument = minimalmodbus.Instrument('/dev/ttyUSB4', 1) # port name, slave address (in decimal)
        self.instrument.debug = True
        self.instrument.serial.port          # this is the serial port name
        self.instrument.serial.parity   = serial.PARITY_NONE
        self.instrument.serial.xonxoff = False
        self.instrument.serial.baudrate = 9600   # Baud
        self.instrument.serial.bytesize = 8
        self.instrument.serial.stopbits = 1
        self.instrument.serial.timeout  = 2 # seconds
        self.instrument.address = 1

        
        
	
        self.finished = threading.Event()
        threading.Thread.start(self)
        
    #this is a required function for all drivers, its goal is to upload some piece of data
    #about your device so it can be seen on the web
    def register(self):
        self.sendtodb("connected", "True", 0)
        self.bitar1lst = ["em_stop_output", "comp_run_stat", "air_dis_valve_stat", "wireless1_com_er"]
        self.bitar1 = {"em_stop_output": "", "comp_run_stat": "", "air_dis_valve_stat": "", "wireless1_com_er": ""}
        
        self.bitarlst = ["CO", "CO2", "O2", "VOC", "dew_point", "temp_trans", "pres_trans", "flow_trans", "temp_wrls_nd1", "pres_wrls_nd1"]
        self.bit_inhibits_status = {"CO":"", "CO2":"", "O2":"", "VOC":"", "dew_point":"", "temp_trans":"", "pres_trans":"", "flow_trans":"", "temp_wrls_nd1":"", "pres_wrls_nd1":""}
        self.bit_alarm_1 = {"CO":"", "CO2":"", "O2":"", "VOC":"", "dew_point":"", "temp_trans":"", "pres_trans":"", "flow_trans":"", "temp_wrls_nd1":"", "pres_wrls_nd1":""}
        self.bit_alarm_2 = {"CO":"", "CO2":"", "O2":"", "VOC":"", "dew_point":"", "temp_trans":"", "pres_trans":"", "flow_trans":"", "temp_wrls_nd1":"", "pres_wrls_nd1":""}
        self.bit_fault = {"CO":"", "CO2":"", "O2":"", "VOC":"", "dew_point":"", "temp_trans":"", "pres_trans":"", "flow_trans":"", "temp_wrls_nd1":"", "pres_wrls_nd1":""}
        self.bit_calibrate = {"CO":"", "CO2":"", "O2":"", "VOC":"", "dew_point":"", "temp_trans":"", "pres_trans":"", "flow_trans":"", "temp_wrls_nd1":"", "pres_wrls_nd1":""}
        self.bit_values = {"CO":"", "CO2":"", "O2":"", "VOC":"", "dew_point":"", "temp_trans":"", "pres_trans":"", "flow_trans":"", "temp_wrls_nd1":"", "pres_wrls_nd1":""}
        
        self.lastLong = ""
        self.lastLat = ""
        self.last_CO_alarms = ""
        self.last_CO2_alarms = ""
        self.last_O2_alarms = ""
        self.last_VOC_alarms = ""

        self.count = 3001

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
        self.sendtodb("log", "system start up", 0)
       
        self.count = 3001
        hb_count = 0
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

                    #get bitArray for compressor status
                    self.firstArray()
                    time.sleep(pause)
                    self.inhibitArray()
                    time.sleep(pause)
                    self.alarm1Array()
                    time.sleep(pause)
                    self.alarm2Array()
                    time.sleep(pause)
                    self.faultArray()
                    time.sleep(pause)
                    self.calArray()

                    time.sleep(pause)

                    #read these registers for the float values
                    regList = [7, 9, 11, 13, 15, 17, 19, 21, 23, 25]
                    for i in range(10):
                        val = ""
                        val = self.instrument.read_float(regList[i], functioncode=3)
                        val = round(val, 1)
                        if val != self.bit_values[self.bitarlst[i]]:
                            self.sendtodb((self.bitarlst[i] + "_val"), val, 0)
                            self.bit_values[self.bitarlst[i]] = val

        

                    last_O2 = self.alarmsStr("O2", self.last_O2_alarms)
                    self.last_O2_alarms = last_O2

                    last_CO = self.alarmsStr("CO", self.last_CO_alarms)
                    self.last_CO_alarms = last_CO

                    last_CO2 = self.alarmsStr("CO2", self.last_CO2_alarms)
                    self.last_CO2_alarms = last_CO2

                    last_VOC = self.alarmsStr("VOC", self.last_VOC_alarms)
                    self.last_VOC_alarms = last_VOC

                    

                    hb_count += 1
                    if hb_count > 600:
                        hb_count = 0
                        self.sendtodb("hb", "1", 0)
                except Exception,e: print(str(e))

                

                
                
                if self.count > 3000:
                    self.count = 0
                    try:
                        self.gps()
                        #self.signal()
                        self.checkTemp()
                    except:
                        pass
            except Exception,e: print(str(e))
    
    
   
    
            
    
    
    
    
    
    
    
    

    
    
    # internal functions & classes
    def alarmsStr(self, gas, lastValue):
        msg = ""
        alarm1 = self.bit_alarm_1[gas]
        alarm2 = self.bit_alarm_2[gas]
        fault = self.bit_fault[gas]
        inhib = self.bit_inhibits_status[gas]
        if int(alarm1) == 1:
            msg += "Alarm 1, "
        if int(alarm2) == 1:
            msg += "Alarm 2, "
        if int(fault) == 1:
            msg += "Fault, "
        if int(inhib) == 1:
            msg += "Inhibited, "

        if msg == "":
            msg = "No Alarms"

        if msg != lastValue:
            if lastValue == "No Alarms" or lastValue == "":
                if msg != "No Alarms":
                    #changed from no alarms to alarms, alarm state is On
                    chName = (gas + "_alm_st")
                    self.sendtodb(chName, "On", 0)

            if lastValue != "No Alarms" or lastValue == "":
                if msg == "No Alarms":
                    #changed from alarms to no alarms, alarm state is Off
                    chName = (gas + "_alm_st")
                    self.sendtodb(chName, "Off", 0)

        name = "alarms_" + gas
        if msg != lastValue:
            self.sendtodb(name, msg, 0)

        return msg
       



    def calArray(self):
        array = self.getBitArray(6)
        for i in range(4):
            if array[i] != self.bit_calibrate[self.bitarlst[i]]:
                
                if array[i] == '0':
                    val = "Normal"
                elif array[i] == '1':
                    val = "Calibration Mode"
                else:
                    continue
               
                self.sendtodb((self.bitarlst[i] + "_cal"), val, 0)
                self.bit_calibrate[self.bitarlst[i]] = array[i]

    def faultArray(self):
        array = self.getBitArray(5)
        for i in range(10):
            if array[i] != self.bit_fault[self.bitarlst[i]]:
                
                if array[i] == '0':
                    val = "Off"
                elif array[i] == '1':
                    val = "On"
                else:
                    continue
               
                self.sendtodb((self.bitarlst[i] + "_flt"), val, 0)
                self.bit_fault[self.bitarlst[i]] = array[i]

    def alarm2Array(self):
        array = self.getBitArray(4)
        for i in range(10):
            if array[i] != self.bit_alarm_2[self.bitarlst[i]]:
                
                if array[i] == '0':
                    val = "Off"
                elif array[i] == '1':
                    val = "On"
                else:
                    continue
               
                self.sendtodb((self.bitarlst[i] + "_a2"), val, 0)
                self.bit_alarm_2[self.bitarlst[i]] = array[i]

    def alarm1Array(self):
        array = self.getBitArray(3)
        for i in range(10):
            if array[i] != self.bit_alarm_1[self.bitarlst[i]]:
                
                if array[i] == '0':
                    val = "Off"
                elif array[i] == '1':
                    val = "On"
                else:
                    continue
               
                self.sendtodb((self.bitarlst[i] + "_a1"), val, 0)
                self.bit_alarm_1[self.bitarlst[i]] = array[i]


    def inhibitArray(self):
        array = self.getBitArray(2)
        for i in range(10):
            if array[i] != self.bit_inhibits_status[self.bitarlst[i]]:
                
                if array[i] == '0':
                    val = "OK"
                elif array[i] == '1':
                    val = "Inhibited"
                else:
                    continue
               
                self.sendtodb((self.bitarlst[i] + "_inhib"), val, 0)
                self.bit_inhibits_status[self.bitarlst[i]] = array[i]


    def firstArray(self):
        array = self.getBitArray(1)
        for i in range(4):
            if array[i] != self.bitar1[self.bitar1lst[i]]:
                if i == 0:
                    if array[i] == '0':
                        val = "Off"
                    elif array[i] == '1':
                        val = "On"
                    else:
                        continue
                if i == 1:
                    if array[i] == '0':
                        val = "Off"
                    elif array[i] == '1':
                        val = "Running"
                    else:
                        continue
                if i == 2:
                    if array[i] == '0':
                        val = "Closed"
                    elif array[i] == '1':
                        val = "Open"
                    else:
                        continue
                if i == 3:
                    if array[i] == '0':
                        val = "OK"
                    elif array[i] == '1':
                        val = "Com Error"
                    else:
                        continue
                self.sendtodb(self.bitar1lst[i], val, 0)
                self.bitar1[self.bitar1lst[i]] = array[i]


    def getBitArray(self, address):
        lst = self.instrument.read_register(int(address), functioncode=3)
        lst = int(lst)
        lst = hex(lst)
        lst = lst[2:]

        while len(lst) < 4:
            lst = "0" + lst

        bit1 = lst[0:2]

        bit2 = lst[2:]

        bit1 = int(bit1, 16)

        bit2 = int(bit2, 16)

        lst1 = list('{0:0b}'.format(bit1))
        lst2 = list('{0:0b}'.format(bit2))

        while len(lst1) < 8:
            lst1 = ['0'] + lst1 

        while len(lst2) < 8:
            lst2 =  ['0'] + lst2 

        lst = lst2 + lst1

        lst = lst[::-1]

        print lst
        return lst

    def tsac_sync(self, name, value):
        self.register()
        self.count = 3001
        return True

   

    def tsac_signal(self, name, value):
        self.signal()
        return True

    def tsac_udgps(self, name, value):
        self.lastLong = ""
        self.lastLat = ""
        resp = self.gps()
        if resp == False:
            self.sendtodb("log", "gps lock failed", 0)
        else:
            self.sendtodb("log", "gps lock success", 0)
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
   
