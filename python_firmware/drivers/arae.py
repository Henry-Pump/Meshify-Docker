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
        self.chName = "tsar" + '_[' + mac + ':'
        print 'device name is:'
        print self.deviceName
        mac2 = mac.replace(":", "")
        self.mac = mac2.upper()
        self.address = 1
        self.debug = True
        self.mcu = mcu
        self.firstRun = True
        self.version = "10"
        self.mqtt = mqtt
        
        
        self.register()

        


        

        
        
	
        self.finished = threading.Event()
        threading.Thread.start(self)
        
    #this is a required function for all drivers, its goal is to upload some piece of data
    #about your device so it can be seen on the web
    def register(self):
        
        self.areaRaeDict = {
            
            1:{"sendString":"\xf1\x03\x01\x01\x0a", "last_CO":"", "last_VOC":"","last_H2S":"","last_LEL":"","last_O2":"", "last_address":"", "connected": "", "badReadCount": -1},
            2:{"sendString":"\xf1\x03\x02\x01\x09", "last_CO":"", "last_VOC":"","last_H2S":"","last_LEL":"","last_O2":"", "last_address":"", "connected": "", "badReadCount": -1},
            4:{"sendString":"\xf1\x03\x04\x01\x07", "last_CO":"", "last_VOC":"","last_H2S":"","last_LEL":"","last_O2":"", "last_address":"", "connected": "", "badReadCount": -1}
                       
                       
                       
           }

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

        while True:
            try:
                self.ser =serial.Serial(port='/dev/ttyUSB4', baudrate=19200, bytesize=8, parity='N', stopbits=1, timeout=0.5, xonxoff=0, rtscts=True, dsrdtr=True)
                break
            except:
                self.sendtodb("error", "cant open com port on AreaRae", 0)
                time.sleep(5)
            
       
        self.count = 3001
        hb_count = 0
        localCount = 0
        while not self.finished.isSet():
            self.count += 1
            
                
            try:
               
                try:

                    for channel in self.areaRaeDict:
                        dict = self.areaRaeDict[channel]

                        #check and see if we need to call the state disconnected or connected
                        if dict["badReadCount"] == 0:
                            connected = "True"
                            if connected != dict["connected"]:
                                self.sendtodbCH(channel, "connected", connected, 0)
                                dict["connected"] = connected
                        elif dict["badReadCount"] > 15:
                            connected = "False"
                            if connected != dict["connected"]:
                                self.sendtodbCH(channel, "connected", connected, 0)
                                dict["connected"] = connected
                        else:
                            pass

                        
                        
                        sendString = dict["sendString"]
                        last_CO = dict["last_CO"]
                        last_VOC = dict["last_VOC"]
                        last_H2S = dict["last_H2S"]
                        last_LEL = dict["last_LEL"]
                        last_O2 = dict["last_O2"]
                        last_address = dict["last_address"]

                        #update all values every 600 loops
                        localCount += 1
                        if localCount > 120:
                            localCount = 0
                            last_CO = ""
                            last_VOC = ""
                            last_H2S = ""
                            last_LEL = ""
                            last_O2 = ""

                        self.ser.write(sendString)

                        #time.sleep(.5)
                        data = self.ser.read(48)
    
                        lst2 = map(hex,map(ord,data))
                        try:
                            if (len(lst2) -2) != int(lst2[1], 16):
                                print "data wrong length"
                                dict["badReadCount"] = dict["badReadCount"] + 2
                                continue
                            address = [lst2[9].replace('0x', ''), lst2[8].replace('0x', ''), lst2[7].replace('0x', ''), lst2[6].replace('0x', ''), lst2[5].replace('0x', '')]
                            mac = ""
                            for i in address:
                                print len(i)
                                while len(i) < 2:
                                    i = "0" + i
                                mac += (i + ":")
                            mac = mac[:-1]

                            print mac
                            print " "
                            print "CO:  ", (float(int((lst2[16]+lst2[15].replace('0x', '')), 16)) / 10)
                            print "VOC: ", (float(int((lst2[23]+lst2[22].replace('0x', '')), 16)) / 10)
                            print "H2S: ", (float(int((lst2[30]+lst2[29].replace('0x', '')), 16)) / 10)
                            print "LEL: ", (float(int((lst2[37]+lst2[36].replace('0x', '')), 16)) / 10)
                            print "O2:  ", (float(int((lst2[44]+lst2[43].replace('0x', '')), 16)) / 10)


                            CO = (float(int((lst2[16]+lst2[15].replace('0x', '')), 16)) / 10)
                            VOC =  (float(int((lst2[23]+lst2[22].replace('0x', '')), 16)) / 10)
                            H2S = (float(int((lst2[30]+lst2[29].replace('0x', '')), 16)) / 10)
                            LEL = (float(int((lst2[37]+lst2[36].replace('0x', '')), 16)) / 10)
                            O2 = (float(int((lst2[44]+lst2[43].replace('0x', '')), 16)) / 10)

                            #assume if we get here that we have a good connection
                            dict["badReadCount"] = 0



                            if CO < 1.5:
                                CO = 0
                            if VOC < 1.0:
                                VOC = 0
                            if H2S < 1.0:
                                H2S = 0
                            if LEL < 1.0:
                                LEL = 0
                            if O2 < 1.0:
                                O2 = 0

                            

                            if CO != last_CO:
                                self.sendtodbCH(channel, "CO", CO, 0)
                                self.areaRaeDict[channel]["last_CO"] = CO 

                            if VOC != last_VOC:
                                self.sendtodbCH(channel, "VOC", VOC, 0)
                                self.areaRaeDict[channel]["last_VOC"] = VOC
                                 
                            if H2S != last_H2S:
                                self.sendtodbCH(channel, "H2S", H2S, 0)
                                self.areaRaeDict[channel]["last_H2S"] = H2S 

                            if LEL != last_LEL:
                                self.sendtodbCH(channel, "LEL", LEL, 0)
                                self.areaRaeDict[channel]["last_LEL"] = LEL 

                            if O2 != last_O2:
                                self.sendtodbCH(channel, "O2", O2, 0)
                                self.areaRaeDict[channel]["last_O2"] = O2 

                            if last_address != last_address:
                                self.sendtodbCH(channel, "id", mac, 0)
                                self.areaRaeDict[channel]["last_address"] = mac 

                        except Exception,e: 
                            print e
                            dict["badReadCount"] = dict["badReadCount"] + 2
                            print "Response too short"




                    hb_count += 1
                    if hb_count > 600:
                        hb_count = 0
                        self.sendtodb("hb", "On", 0)
                except Exception,e: print(str(e))

                

                
                
                if self.count > 3000:
                    self.count = 0
                    try:
                        #self.gps()
                        #self.signal()
                        self.checkTemp()
                    except:
                        pass
            except Exception,e: print(str(e))
    
    
   
    
            
    
    
    
    
    
    
    
    

    
    
   

    def arae_sync(self, name, value):
        self.register()
        self.count = 3001
        return True

   

    def arae_signal(self, name, value):
        self.signal()
        return True

    def arae_udgps(self, name, value):
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
   
