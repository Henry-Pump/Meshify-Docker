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
import update_mcu
import gsmgps
from xml.dom.minidom import parseString
from math import radians, cos, sin, asin, sqrt
import Queue
import pickle
import base64


map1 = {
    "opc_pm1":"pm1",
    "opc_pm2_5":"pm2_5",
    "opc_pm10":"pm10",
    "pm1":"pm1",
    "pm2_5":"pm2_5",
    "pm10":"pm10",
    "sample_period":"period",
    "flowrate":"flow",
    "BIN0":"BIN0",
    "BIN1":"BIN1",
    "BIN2":"BIN2",
    "BIN3":"BIN3",
    "BIN4":"BIN4",
    "BIN5":"BIN5",
    "BIN6":"BIN6",
    "BIN7":"BIN7",
    "BIN8":"BIN8",
    "BIN9":"BIN9",
    "BIN10":"BIN10",
    "BIN11":"BIN11",
    "BIN12":"BIN12",
    "BIN13":"BIN13",
    "BIN14":"BIN14",
    "BIN15":"BIN15",
    "CL":"cloop",
    "I1":"din1",
    "I2":"din2",
    "I3":"din3",
    "I4":"din4",
    "A1":"analog1",
    "A2":"analog2",
    "A3":"analog3",
    "A4":"analog4",
    "OC1": "dout1",
    "OC2": "dout2",
    "OC3": "dout3",
    "OC4": "dout4",
    "R1":"relay1",
    "VIN":"vin",
    "BAT":"bat",
    "TMP":"temp",
    "PULSE":"pulse",
    "VER" : "ver"
    }

IOelements = {
    "I1":"din1",
    "I2":"din2",
    "I3":"din3",
    "I4":"din4",
    "OC1": "dout1",
    "OC2": "dout2",
    "OC3": "dout3",
    "OC4": "dout4",
    "R1":"relay1"
    }


IOdata = {
        "1":"On",
        1: "On",
        "on": "On",
        "On": "On",
        "0": "Off",
        0: "Off",
        "off": "Off",
        "Off": "Off"
        }

#fake mqtt message for ifttt actions 
class mqttMsg(object):
    
    def __init__(self, topic, payload):
        self.topic = topic
        self.payload = payload
        self.qos = 1

class xbeeSerial:
    #handles the serial connection from linux to the MCU to the xbee

    def __init__(self):
        self.runXbee = False
        self.data = ""
        self.lock = threading.Lock()
        thread.start_new_thread(self.readThread, ())
        self.writeLock = threading.Lock()
        self.first_run = True

        #flag to direct data during file transfer
        self.fileTransfer = False

    def open(self):
        pass
    def close(self):
        pass

    def isOpen(self):
        return True
    
    def writeAT(self, buf):
        print "writing XBEE AT: ", buf
        f_out = os.open('/dev/ttyXBEE_RX', os.O_WRONLY )
        os.write(f_out, buf)
        os.close(f_out)

    def write(self, buf):
        print "writing XBEE: ", buf
        with self.writeLock:
            f_out = os.open('/dev/ttyXBEE_RX', os.O_WRONLY )
            os.write(f_out, buf)
            os.close(f_out)

    def read(self, max=1000):
        with self.lock:
            data = self.data
            self.data = ""
        return data
    def flushInput(self):
        self.data = ""
    def flushOutput(self):
        self.data = ""

    def atCommandGet(self, command):
        with self.writeLock:
            #clear out the read buffer:
            self.read()
            self.writeAT("+++")
            time.sleep(2)
            at = "AT" + command + chr(13)
            self.writeAT(at)
            time.sleep(2)
            return self.read()
            
    def makeDragon(self):
        self.atCommandSet("DD", "B0776")
        time.sleep(4)
        self.atCommandSet("DD", "B0776")
        time.sleep(2)
        os.system("reboot -f")

    def makeFly(self):
        self.atCommandSet("DD", "B0777")
        time.sleep(4)
        self.atCommandSet("DD", "B0777")
        time.sleep(2)
        os.system("reboot -f")
    def atCommandSet(self, command, value):
        with self.writeLock:
            #clear out the read buffer:
            self.read()
            self.writeAT("+++")
            time.sleep(2)
            at = "AT" + command + "=" + value + chr(13)
            self.writeAT(at)
            time.sleep(2)
            self.writeAT("ATWR" + chr(13))
           
    def readThread(self):
        
        while self.runXbee:
            time.sleep(.05)
            
            try:
                
                f_in = os.open('/dev/ttyXBEE_TX', os.O_RDONLY)
                line = os.read(f_in, 10000)
                print "reading XBEE: ", line
                os.close(f_in)
                if self.fileTransfer == False:
                    try:
                        d = base64.b64decode(line)
                        line = d
                    except:
                        pass
                with self.lock:
                    self.data += line

                
                #this clears the buffer on the first time you open the connection 
                #if self.first_run == True:
                #    self.data = ""
                #    self.first_run = False
            except Exception,e:
                try:
                    self.lock.release()
                except:
                    pass
                print(str(e))
                return ""


class rs232Serial:
    #handles the serial connection from linux to the MCU to the xbee

    def __init__(self):
        self.data = ""
        self.lock = threading.Lock()
        thread.start_new_thread(self.readThread, ())
        self.first_run = True
        

    def open(self):
        pass
    def close(self):
        pass

    def isOpen(self):
        return True
    
    def write(self, buf):
        print "writing 232: ", buf
        f_out = os.open('/dev/ttyRS232_RX', os.O_WRONLY )
        os.write(f_out, buf)
        os.close(f_out)

    def read(self, max=1000):
        with self.lock:
            data = self.data
            self.data = ""
        return data
    def flushInput(self):
        self.data = ""
    def flushOutput(self):
        self.data = ""
    def readThread(self):
        
        while True:
            
            try:
                
                f_in = os.open('/dev/ttyRS232_TX', os.O_RDONLY)
                line = os.read(f_in, 10000)
                print "reading 232: ", line
                os.close(f_in)
                with self.lock:
                    self.data += line

                
                #this clears the buffer on the first time you open the connection 
                #if self.first_run == True:
                #    self.data = ""
                #    self.first_run = False
            except Exception,e:
                try:
                    self.lock.release()
                except:
                    pass
                print(str(e))
                return ""


class rs485Serial:
    #handles the serial connection from linux to the MCU to the xbee

    def __init__(self):
        self.data = ""
        self.lock = threading.Lock()
        thread.start_new_thread(self.readThread, ())
        self.first_run = True
        
    def open(self):
        pass
    def close(self):
        pass

    def isOpen(self):
        return True
    



    def write(self, buf):
        print "writing 485: ", buf
        f_out = os.open('/dev/ttyRS485_RX', os.O_WRONLY )
        os.write(f_out, buf)
        os.close(f_out)

    def read(self, max=1000, pause=0.1):
        time.sleep(pause)
        with self.lock:
            data = self.data
            self.data = ""

        return data
        

    def readThread(self):
        
        while True:
            
            try:
                
                f_in = os.open('/dev/ttyRS485_TX', os.O_RDONLY)
                line = os.read(f_in, 10000)
                print "reading 485: ", line
                os.close(f_in)
                with self.lock:
                    self.data += line
                
                
                #this clears the buffer on the first time you open the connection 
                #if self.first_run == True:
                #    self.data = ""
                #    self.first_run = False
            except Exception,e:
                try:
                    self.lock.release()
                except:
                    pass
                print(str(e))
                return ""
            


class mcu_main(threading.Thread):
    """
    In this class I need to:
    
    1. make a serial connection to the MCU
    2. set up a method for sending data to the com port self.write(data)
    3. set up a thread for checking for data coming in from the com port
        assumptions here are that the mcu will buffer the incoming messages.
        
        
    """
    
    
    
    def __init__(self):
        #global for if the flies on the network will be at this location or their own.
        self.flySameLocation = True
        self.xbees = {}
        threading.Thread.__init__(self)
        self.daemon = True
        self.last_OK = False
        self.lock = threading.Lock()
        self.connected = False
        self.last_485 = None
        self.finished = threading.Event()
        threading.Thread.start(self)
        self.dataDict = {}
        self.rs485 = rs485Serial()
        self.rs232 = rs232Serial()
        self.xbee = xbeeSerial()
        self.count = 0
        self.ledStat = None
        self.signal = None
        self.gps = "0.0,-0.0"
        try:
            self.gsmgps = gsmgps.gsmgps()
        except:
            pass

        self.iftQ = Queue.Queue()
        self.iftLock = threading.Lock()
        try:
            with open('/root/python_firmware/mcu/iftttMap.p', 'rb') as handle:
                self.iftttMap = pickle.load(handle)
                print "found pickled iftttMap dictionary"
                print self.iftttMap
        except:
            print "couldn't load iftttMap from pickle"
            self.iftttMap = {"M1_[c4:93:00:06:71:38:00:30]!":[{"channel":"cloop", "value":"<16", "then":{"name":"M1_[c4:93:00:06:71:38:00:30]!", "channel":"dout3", "value":"On"}},
                                                              {"channel":"cloop", "value":"<16", "then":{"name":"M1_[c4:93:00:06:71:38:00:30]!", "channel":"dout2", "value":"Off"}},
                                                              {"channel":"cloop", "value":"<16", "then":{"name":"M1_[c4:93:00:06:71:38:00:30]!", "channel":"dout1", "value":"Off"}},

                                                              {"channel":"cloop", "value":">16&<18", "then":{"name":"M1_[c4:93:00:06:71:38:00:30]!", "channel":"dout3", "value":"Off"}},
                                                              {"channel":"cloop", "value":">16&<18", "then":{"name":"M1_[c4:93:00:06:71:38:00:30]!", "channel":"dout2", "value":"On"}},
                                                              {"channel":"cloop", "value":">16&<18", "then":{"name":"M1_[c4:93:00:06:71:38:00:30]!", "channel":"dout1", "value":"Off"}},

                                                              {"channel":"cloop", "value":">18", "then":{"name":"M1_[c4:93:00:06:71:38:00:30]!", "channel":"dout3", "value":"Off"}},
                                                              {"channel":"cloop", "value":">18", "then":{"name":"M1_[c4:93:00:06:71:38:00:30]!", "channel":"dout2", "value":"Off"}},
                                                              {"channel":"cloop", "value":">18", "then":{"name":"M1_[c4:93:00:06:71:38:00:30]!", "channel":"dout1", "value":"On"}},

                                                              ]}
       
        with open('/root/python_firmware/mcu/iftttMap.p', 'wb') as handle:
            pickle.dump(self.iftttMap, handle)
            
        thread.start_new_thread(self.iftttThread, ())


    def set485Baud(self, baud):
        baud = str(baud)
        cmd = """<SET COM="RS485BAUD">%s</SET>\n""" % baud
        success = self.send_mcu(cmd ,retry=5)
        #self.spiOn(0)
        return success

    def set232Baud(self, baud):
        baud = str(baud)
        cmd = """<SET COM="RS232BAUD">%s</SET>\n""" % baud
        success = self.send_mcu(cmd ,retry=5)
        #self.spiOn(0)
        return success

    def resetModem(self):
        success = self.send_mcu("""<SET COM="GSMRST">1</SET>\n""" ,retry=5)
        




    def firmUpdate(self, filename):

        with self.lock:
            self.connected = False
            self.ser.close()
            success = update_mcu.update_mcu(filename)
            print success
            if success == True:
                print "we got it working"

            
        return success
        

    

    def stop(self):
        self.finished.set()
        self.join()

    def getDict(self):
        data = self.dataDict
        return data


    





    def digitalOut1(self, state):
        state = self.ioValueTest(state)
        state = str(state)
        success = self.send_mcu("""<SET COM="OC1">""" + state + """</SET>\n""" ,retry=5)
        return success

    def digitalOut2(self, state):
        state = self.ioValueTest(state)
        state = str(state)
        success = self.send_mcu("""<SET COM="OC2">""" + state + """</SET>\n""" ,retry=5)
        return success
    
    def digitalOut3(self, state):
        state = self.ioValueTest(state)
        state = str(state)
        success = self.send_mcu("""<SET COM="OC3">""" + state + """</SET>\n""" ,retry=5)
        return success    

    def digitalOut4(self, state):
        state = self.ioValueTest(state)
        state = str(state)
        success = self.send_mcu("""<SET COM="OC4">""" + state + """</SET>\n""" ,retry=5)
        return success
    
    def digitalOut5(self, state):
        state = self.ioValueTest(state)
        state = str(state)
        success = self.send_mcu("""<SET COM="OC5">""" + state + """</SET>\n""" ,retry=5)
        return success
        

    def relay2(self, state):
        #state = self.ioValueTest(state)
        #state = str(state)
        #success = self.send_mcu("""<SET COM="R2">""" + state + """</SET>\n""" ,retry=5)
        return True
        

    def relay1(self, state):
        state = self.ioValueTest(state)
        state = str(state)
        if state == "0":
            buf =  """{\"SET\": [{\"R1\": \"0\"}]}\n"""
        elif state == "1":
            buf =  """{\"SET\": [{\"R1\": \"1\"}]}\n"""
        success = self.send_mcu(buf ,retry=5)
        return success
        
    def ledControl(self, ledNumber, onoff, blinking):

        str1 = """<SET COM="LED%s">%s</SET>\n""" % (str(ledNumber), str(onoff))
        str2 = """<SET COM="LEDBL%s">%s</SET>\n""" % (str(ledNumber), str(blinking))
        #str1 = """{\"SET\": [{\"LED%s\": \"%s\"}]}\n""" % (str(ledNumber), str(onoff))
                 
        #str2 = """ {\"SET\": [{\"LEDBL%s\": \"%s\"}]}\n""" % (str(ledNumber), str(blinking))
        success = self.send_mcu(str2, retry=5)
        time.sleep(.5)
        success = self.send_mcu(str1, retry=5)

        if success:
            return True
        else:
            return False

    def spiOn(self, state):
        if state == 1 or state == "1" or state == "on" or state == "on":
            success = self.send_mcu("""<SET COM="OPC">1</SET>\n""" ,retry=5)
            #self.send_mcu("""<SET COM=\"OPC_FAN_LASER_ON\"></SET>\n""")
            #self.send_mcu("""{\"SET\": [{\"OPC\": \"1\"}, {\"R1\": \"0\"}, {\"R1\": \"1\"}]}\n""")
        if state == 0 or state == "0" or state == "off" or state == "Off":
            self.send_mcu("""<SET COM=\"OPC_FAN_LASER_OFF\"></SET>\n""")
            self.send_mcu("""{\"SET\": [{\"OPC\": \"0\"}]}\n""")


    def xbeeCom(self, state):
        if state == 1 or state == "1" or state == "on" or state == "on":
            success = self.send_mcu("""<SET COM="XBEECOM">1</SET>\n""" ,retry=5)
        if state == 0 or state == "0" or state == "off" or state == "Off":
            success = self.send_mcu("""<SET COM="XBEECOM">0</SET>\n""" ,retry=5)

    def resetXbee(self):
        success = self.send_mcu("""<SET COM="XBEERST">1</SET>\n""" ,retry=5)
        return success

    def rs232reset(self):
        success = self.send_mcu("""<SET COM="RS232RESET">1</SET>\n""")
        return success
    def sleep(self, time):
        time = str(time)
        success = self.send_mcu("""<SET COM="SLEEP">""" + time + """</SET>\n""")
        return success
        
    def COM_thread(self):

        while True:
            time.sleep(1.5)
            try:
                self.send_mcu_no_response("<GET>STATE</GET>\n")
            except:
                pass
            
    def run(self):

        #thread.start_new_thread(self.RS485_thread, ())
        thread.start_new_thread(self.COM_thread, ())
        thread.start_new_thread(self.updateGPSandSignalThread, ())
        thread.start_new_thread(self.mcuWatchdogThread, ())
        
        
        while True:
            time.sleep(.5)
            try:
                
                f_in = os.open('/dev/ttyCOM_TX', os.O_RDONLY)

                line = os.read(f_in, 1000)
                os.close(f_in)
                
                #print line
               
                
                
                
                #line = line[0]
                item = str(line)
                if "OK" in item or "ok" in item:
                    self.last_OK = True
                try:
                    x = parseString(item)
                    try:
                        self.count = int(x.getElementsByTagName("STATE")[0].getAttribute("req_cnt"))
                    except:
                        pass
                    #print "here is the count  ", self.count
                    for i in x.childNodes:
                        for a in i.childNodes:
                            name = a.localName  
                            if name != None:
                                val = x.getElementsByTagName(name)[0].firstChild.nodeValue
                                if name in IOelements:
                                    self.dataDict[map1[name]] = self.IOmap(val)
                                else:
                                    try:
                                        self.dataDict[map1[name]] = val
                                    except:
                                        continue
                except Exception, e:
                    pass#print e
                
                

            except Exception,e:
                #print(str(e))
                time.sleep(.5)
     
    def IOmap(self, value):
        if IOdata.has_key(value):
            newVal = IOdata[value]
        else:
            newVal = value
        return newVal

    def ioValueTest(self, value):
        if value == 0 or value == "0" or value == "off" or value == "Off":
            newVal = 0
        elif value == 1 or value == "1" or value == "on" or value == "On":
            newVal = 1
        return newVal

    def send_mcu_no_response(self,data):
        buf = data
        with self.lock:
            f_out = os.open('/dev/ttyCOM_RX', os.O_WRONLY )
            os.write(f_out, buf)
            os.close(f_out)

    def send_mcu(self, data, retry=0):
        buf = data
        
        last_OK = False
        while retry > -1:
            retry =  (int(retry) -1)
            
            with self.lock:
                time.sleep(1)
                self.last_OK = False
                f_out = os.open('/dev/ttyCOM_RX', os.O_WRONLY )
                os.write(f_out, buf)
                os.close(f_out)
                count = 0
                while last_OK == False:
                   
                    time.sleep(.5)
                    last_OK = self.last_OK
                    if last_OK == True:
                        retry = -2
                        break
                    count += 1
                    if count > 5:
                        break
                        
       
        return last_OK

    def updateGPSandSignalThread(self):
        while True:
            time.sleep(2)
            try:
                
                signal, gps = self.getGPSGSM()
                gps = gps.split(",")

                lat = round(float(gps[0]), 8)
                long = round(float(gps[1]), 8)
                gps = str(lat) + "," + str(long) 
                if gps!= self.gps:
                    self.gps = gps

                #led status 4=solid, 3=blinking fast 2=blinking slow, 1=off
                if signal != self.signal:
                    self.signal = signal
                    if int(signal) > 46:
                        status = 4
                    elif int(signal) > 28:
                        status = 3
                    elif int(signal) > 1:
                        status = 2
                    else:
                        status = 1
                    if status != self.ledStat:
                        self.ledStat = status
                        if status == 4:
                            self.ledControl(1,1,0)
                        elif status == 3:
                            self.ledControl(1,1,8)
                        elif status == 2:
                            self.ledControl(1,1,120)
                        elif status == 1:
                            self.ledControl(1,0,0)
            except Exception, e:
                #print e
                time.sleep(5)


    def distanceBetween(self, lon1, lat1, lon2, lat2):
        lon1 = float(lon1)
        lat1 = float(lat1)
        lon2 = float(lon2)
        lat2 = float(lat2)
        """
        Calculate the great circle distance between two points 
        on the earth (specified in decimal degrees)
        """
        # convert decimal degrees to radians 
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

        # haversine formula 
        dlon = lon2 - lon1 
        dlat = lat2 - lat1 
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a)) 
        r = 3956 # Radius of earth in kilometers. Use 3956 for miles
        return c * r
    def get_modem_id(self):
        try:
            mdn = self.gsmgps.get_MDN()
        except Exception,e:
            print "error getting modem id"
            print e
            return None
        return mdn

    def get_sim_id(self):
        try:
            sim = self.gsmgps.get_SIMID()
        except Exception,e:
            print "error getting sim id"
            print e
            return None
        return sim

    def getGPSGSM(self):
        tries = 0
        while tries < 10:
            try:
                tries += 1
                a = self.gsmgps.main()
                signal = a[0]
                gps = str(a[1][0]) + "," + str(a[1][1])
                return signal, gps
            except:
                pass 

        return None, None

    def setIftttmap(self, obj):

        with self.iftLock:
            self.iftttMap = obj
            with open('/root/python_firmware/mcu/iftttMap.p', 'wb') as handle:
                pickle.dump(self.iftttMap, handle)

    def iftttThread(self):
        while True:
            time.sleep(1)
            try:
                data = self.iftQ.get()
                name = data[0]
                channel = data[1]
                value = data[2]
                with self.iftLock:
                    if name in self.iftttMap:
                        for i in self.iftttMap[name]:
                            trigger = False
                            if i['channel'] == channel:
                                if i["value"].startswith("<"):
                                    if "&" in i["value"]:
                                        if i["value"].split("&")[1].startswith("<"):
                                            if float(value) < float(i["value"].split("&")[0].replace("<", "")) and float(value) < float(i["value"].split("&")[1].replace("<", "")):
                                                trigger = True
                                        elif i["value"].split("&")[1].startswith(">"):
                                            if float(value) < float(i["value"].split("&")[0].replace("<", "")) and float(value) > float(i["value"].split("&")[1].replace(">", "")):
                                                trigger = True
                                        elif i["value"].split("&")[1].startswith("="):
                                            if float(value) < float(i["value"].split("&")[0].replace("<", "")) and float(value) == i["value"].split("&")[1].replace("=", ""):
                                                trigger = True
                                    else:
                                        if float(value) < float(i["value"].replace("<", "")):
                                            print "Less than rule triggered"
                                            print "we have a pending ifttt action"
                                            trigger = True
                                        


                                elif i["value"].startswith(">"):
                                    if "&" in i["value"]:
                                        if i["value"].split("&")[1].startswith("<"):
                                            if float(value) > float(i["value"].split("&")[0].replace(">", "")) and float(value) < float(i["value"].split("&")[1].replace("<", "")):
                                                trigger = True
                                        elif i["value"].split("&")[1].startswith(">"):
                                            if float(value) > float(i["value"].split("&")[0].replace(">", "")) and float(value) > float(i["value"].split("&")[1].replace(">", "")):
                                                trigger = True
                                        elif i["value"].split("&")[1].startswith("="):
                                            if float(value) > float(i["value"].split("&")[0].replace(">", "")) and float(value) == i["value"].split("&")[1].replace("=", ""):
                                                trigger = True
                                    else:
                                        if float(value) > float(i["value"].replace(">", "")):
                                            print "Greater than rule triggered"
                                            print "we have a pending ifttt action"
                                            trigger = True




                                        


                                elif i["value"].startswith("=") or i['value'] == value:
                                    if i["value"].replace("=", "") == value:
                                        trigger = True


                                if trigger:
                                    print "we have a pending ifttt action"
                                    set_value = i['then']['value']
                                    set_name = i['then']['name']
                                    set_channel = i['then']['channel']
                                    topic = "meshify/sets/1/" + self.mac
                                    message = '[{"user":"ifttt action","mac":"%s","company":"1","payload":{"name":"%s.%s","value":"%s","expires":"1389369695"},"msgId":0}]' % (self.mac, set_name, set_channel, set_value)
                                    self.on_message("n", "j", mqttMsg(topic, message))
                                    time.sleep(1)
                                

            except Exception,e:
                print e

    def mcuWatchdogThread(self):
        time.sleep(3600)
        while True:
            old_count = self.count
            time.sleep(120)
            if self.count <= old_count:
                print "reseting, data is not changing"
                #mcu no longer getting updates.
                os.system("reboot -f")
                time.sleep(120)
            else:
                pass
                #print "healthy mcu"

    
         
            
    


    