import sys
import string
import socket, fcntl, struct
import client as paho
import os
import time
import ssl
try:
    import json
except:
    import simplejson as json
import thread
import threading
import random
import base64

from meshifyData import meshifyData
#from devices import mainMistaway, m1, apg #, gds #cam,
#from devices import gdsMT as gds
import Queue
import pickle
import urllib2
import urllib
try:
    from sqlQueue import myqueue as SQLQ
except:
    pass
try:
    import SkyWaveDataAPI
    SAT = True
except:
    SAT = False

try:
    import schedule
    sced = True
except:
    sced = False

unitName = "mainMeshify"

broker = "mqtt.meshify.com"

root = os.getcwd() + "/"
#non secure
port = 1884

LORA = True
try:
    import lora_main
except:
    LORA = False



#secure port
#port = 1883

#driver for a virtual device called "main", it can never send data up to the website, but it hold methods that
#can be called easier than others because it has no unquie name assosicated with it
class main():

    def __init__(self, name, number, mac, q, mcu, company, offset, mqtt, nodes, topics):
        self.topics = topics
        self.nodes = nodes
        self.offset = offset
        self.company = company
        self.name = name
        self.number = number 
        self.q = q
        self.mqtt = mqtt
        self.deviceName = name #+ '_[' + mac +  ':' + number[0:2] + ':' + number[2:] + ']!'
        print 'device name is:'
        print self.deviceName
        mac2 = mac.replace(":", "")
        self.mac = mac2.upper()
        self.mcu = mcu
        self.count = 0
        self.dst = ""
        #queue for sets to the mesh network will handeled through a queue in this main driver
        self.meshQ = Queue.Queue()
        version = "5"  # 5 - updated for SAT data and generic sets. 4 - devices changed to drivers for dia
        
        
             

        


        self.sendtodb("version", version, 0)
        thread.start_new_thread(self.registerThread, ())
        
        #pickle.dump( version, open( "coreVersion.p", "wb" ) )

    def sendtodb(self, channel, value, timestamp):

        if int(timestamp) == 0:
            timestamp = self.getTime()
        
        topic = 'meshify/db/%s/%s/%s/%s' % (self.company, self.mac, self.deviceName, channel)
        print topic
        
        msg = """[ { "value":"%s", "timestamp":"%s" } ]""" % (str(value), str(timestamp))
        print msg
        self.q.put([topic, msg, 0])


    def getTime(self):
        return str(int(time.time() + int(self.offset)))


    def main_mcuupdate(self, name, value):
        success = self.mcu.firmUpdate(value)
        
        if success == True:
            val = "update to " + value + " was a success"
        elif success == False:
            print "you need to reboot and pray you didn't brick the MCU"
            val = "update to " + value + " failed"
        else:
            val = "update to " + value + " failed because " + str(success) 
            print "you need to reboot and pray you didn't brick the MCU"
        

        #reseting the MCU also resets the Cellular modem, so we need to redo our mqtt connection once the modem comes back to life
        time.sleep(180)
        try:
            self.mqtt.reconnect()
        except Exception,e:
            print str(e)
            os.system("/root/reboot")
        self.sendtodb(name, val, 0)

    def normalThread(self):
        time.sleep(10)
        os.system("/root/normalStart.sh")

    def debugThread(self):
        time.sleep(10)
        os.system("/root/debugStart.sh")

    def rebootThread(self):
        time.sleep(10)
        os.system("/root/reboot")
        
    def main_normal(self, name, value):
        
        if int(value) == 1:

            thread.start_new_thread(self.normalThread, ())
            return True
        else:
            return False

    def main_debug(self, name, value):
        
        if int(value) == 1:

            thread.start_new_thread(self.debugThread, ())
            return True
        else:
            return False

    def main_reboot(self, name, value):
        if bool(value) == True:
            #reset the modem
            #self.mcu.resetModem()
            #time.sleep(2)

            #resest the MCU
            #try:
            #    os.system("/root/mcu2reset")
            #except:
            #    pass
            thread.start_new_thread(self.rebootThread, ())
            return True
            
            #os.system("/root/reboot")

    def main_SAT(self, name, value):
        print "SAT is SET in MAIN"
        st = "date -s @" + str(int(float(value)))
        os.system(st)

        return True

    def registerThread(self):
        while True:
            time.sleep(3600 * 24)

            try:
                os.system("/usr/bin/ntpdate pool.ntp.org")
                os.system("/usr/sbin/ntpdate pool.ntp.org")
            except:
                pass
            
            try:
                for name, driver in self.nodes.iteritems():
            

                    try:
                        driver.offset = self.offset
                        driver.company = self.company
                        
                
                    except Exception,e:
                        print e
            except:
                pass

    def main_register(self, name, value):
        #try and sync the time
        
        try:
            #setData = """<data><channel_set name="%s" value="%s"/></data>$$$%s""" % ("main.register", "On", 1)
            setData = {}
            setData['name'] = 'main.register'
            setData['value'] = 'On'
            setData['id'] = 1
            print setData
            self.meshQ.put(setData)
        except:
            pass

        try:
            meshData = meshifyData.meshifyData(self.mac)
            self.offset, self.dst, self.company = meshData.getdata()
            print ("meshify/sets/" + str(self.company) + "/" + self.mac + "/#")
            self.mqtt.subscribe(("meshify/sets/" + str(self.company) + "/" + self.mac + "/#"), 0)
            self.mqtt.subscribe(("meshify/files/" + str(self.company) + "/" + self.mac + "/#"), 0)

            self.topics.append("meshify/sets/" + str(self.company) + "/" + self.mac + "/#")
            self.topics.append("meshify/files/" + str(self.company) + "/" + self.mac + "/#")
        except Exception,e:
            print e
        for name, driver in self.nodes.iteritems():
            

            try:
                driver.offset = self.offset
                driver.company = self.company
                driver.register()
                
            except Exception,e:
                print e
                
        return True
                
        #this is where I need to put the function to have all of my devices check in 
            
class meshifyMain():
    

   

    def __init__(self):


        #add google nameserver
        os.system("/bin/echo nameserver 8.8.8.8 > /etc/resolv.conf")
        #make dictionary for xbee sets

        #check and see if the drivers folder is there:
        #if not os.path.exists("drivers"):
        #    #make the drivers dir
        #    os.makedirs("drivers")
        self.MCU_ON = False
        #marker or wether or not the device is a fly
        self.FLY = False
        self.reconnecting = False
        self.mqttQ = Queue.Queue()
        #get MAC address, if this breaks,  you are [no longer] screwed 
        try:
            mac = self.getHwAddr('eth0')
            print "success getting mac"
        except:
            print "error getting mac"
            try:
                from uuid import getnode as get_mac
                mac = get_mac()
                mac = hex(mac).replace('0x', '')
                n = 2
                mac = [mac[i:i+n] for i in range(0, len(mac), n)]
                newMac = ""
                for i in mac:
                    newMac = newMac + i + ":"

                mac = newMac[:-1]
            except:
                mac = "12:34:56:78:91:23"
        mac = str(mac)
        self.OK2Send = True
        self.zigMac = mac
        self.deviceUrlList = []
        self.deviceVersions = {}
        try:
            # todo: change this to sd card if present on some devices
            self.SQLQ = SQLQ.SqliteQueue(root + "sqlQueue/q2")
        except:
            pass

        #varible for if the device is connected to the satellites. 
        self.SAT_COM = False
        

        #if schedule module is there, then set up the global
        try:
            if sced == True:
                self.schedule = schedule.schedule(self.sets, self.mqttQ, self.getTime)
            else: 
                self.schedule = False
        except Exception,e:
            print "####################"
            print e
        
            
        #try and sync the time
        try:
            os.system("/usr/bin/ntpdate pool.ntp.org")
            os.system("/usr/sbin/ntpdate pool.ntp.org")
        except:
            pass


        #dictionary of all the nodes attched
        self.nodes = {}
        
        mac = mac.replace(":", "")
        mac = mac.upper()
        print "here is the mac address"
        print mac

        #get your time offset, DST value and company id from meshify
        try:
            meshData = meshifyData.meshifyData(mac)
            self.offset, self.dst, self.companyId = meshData.getdata()
        except:
            print "didn't work on api to get meshify data"
        
                
        self.mac = mac

        #start the debug thread:
        thread.start_new_thread(self.debugThread, ())


        #set up placeholder for self.mqtt

        self.mqtt = paho.Client(client_id=self.mac, clean_session=True)

        

        #change to false for mqtt.meshify.com
        #self.mqtt.tls_insecure_set(True)
        #self.mqtt.tls_set(root + "ca.crt", certfile=root + "client.crt", keyfile=root + "client.key", cert_reqs=ssl.CERT_NONE)
        self.mqtt.username_pw_set("admin", "columbus")
        
        print "now I'm here"
        #Set up the last will and testiment to tell the system that I'm disconneted
        lc = int(self.getTime()) + 30

        
        
        self.deviceName = unitName + '_[' + self.zigMac +  ':' + "00" + ':' + "00" + ']!'
        self.deviceNameMain = "mainMeshify" + '_[' + self.zigMac +  ':' + "00" + ':' + "00" + ']!'
        topic = 'meshify/db/%s/%s/%s/%s' % (self.companyId, self.mac, self.deviceName, "connected")
        msg = """[ { "value":"%s", "timestamp":"%s" } ]""" % ("False", str(lc))
        self.mqtt.will_set(topic, msg, 2) 
        
        print "will set up on topic: " + topic
        
        #tell mqtt what to do on connect
        self.mqtt.on_connect = self.on_connect

        #tell mqtt which function to call when a message is received
        self.mqtt.on_message = self.on_message
        self.mqtt.on_disconnect = self.on_disconnect

        #make conneciton to the MCU (only on M1 V5 right now):


        try:
            from mcu import mcu_main
            self.MCU_ON = True
        except:
            self.MCU_ON = False

        try:
            if self.MCU_ON == True:
                print "mcu is on"
                try:
                    print "mcu loading"
                    self.mcu = mcu_main.mcu_main()
                    
                    #added these for ifttt actions
                    self.mcu.mac = self.mac
                    self.mcu.on_message = self.on_message
                    self.mcu.FLY = self.FLY


                    #adding this global for turning all data coming out of the device off
                    self.mcu.cutAllDataOff = False

                    print "mcu loaded"
                    #now see if we are a fly
                    flyTries = 0
                    self.mcu.xbeeCom(0)
                    self.mcu.xbee.write("+++")
                    time.sleep(1)
                    self.mcu.xbee.write("ATFR" +chr(13))
                    time.sleep(1)
                    while flyTries < 2:
                        #self.mcu.send_mcu("""{\"SET\": [{\"XBEECOM\": \"0\"}]}\n""")
                        flyTries += 1
                        self.mcu.xbee.read()
                        self.mcu.xbee.write("+++")
                        time.sleep(2)
                        self.mcu.xbee.write("ATDD" +chr(13))
                        time.sleep(3)
                        response = self.mcu.xbee.read()
                        if "777" in response or LORA:
                            print "I'm a fly"
                            #self.mcu.spiOn(0)
                            self.FLY = True
                            self.mcu.FLY = self.FLY
                            if LORA:
                                #self.mcu.xbee = lora_main.lora()
                                #self.mcu.xbee.fileTransfer = False
                                pass
                            #set the xbee to talk to the coordinator 
                            #this needs to be working for network switching
                            #self.mcu.xbee.atCommandSet("DH", "0")
                            #self.mcu.xbee.atCommandSet("DL", "FFFF")
                            thread.start_new_thread(self.xbeeGetThread, ())
                            break
                        else:
                            self.FLY = False
                except Exception, e:
                    print e
                    self.mcu.FLY = self.FLY
                    self.FLY = False
            else:
                print "MCU NOT ON"
                self.mcu = None


        except Exception, e:
            print e


        #while True:
        #    time.sleep(3)
        #    print self.mcu.getDict()

        #turn off connected LED's 
        if self.MCU_ON:
            self.mcu.FLY = self.FLY
            self.mcu.ledControl(2,0,0)
            self.mcu.ledControl(3,0,0)

    


        self.topics = []

        #we need an api to get some of the unique data for the topic structure
        self.topics.append("meshify/sets/1/" + self.mac + "/#")
        self.topics.append("meshify/files/1/" + self.mac + "/#")
        self.topics.append("meshify/sets/" + str(self.companyId) + "/" + self.mac + "/#")
        self.topics.append("meshify/files/" + str(self.companyId) + "/" + self.mac + "/#")
        


        
        
        

        

        #wait a few seconds to connect
        time.sleep(5)
        
        #####################################################
        # this is the loading of the devices, if it fails, we still need main to work
        #order of operations:
        # 1. From API
        # 2. From Text file
        # 3. From previous loads pickle file
        # 4. Nothing, it will only run main (not mainMeshify, just main wich can do reboot and register)
        
        
        #the json data should come back from an API, for now it will come from in the root/python_firmware deviceList.txt

        try:
            try:
                data = meshData.checkConfig()
                if len(data) < 1:
                    raise ValueError('too short')
            except:
                json_data = open('deviceList.txt')
                data = json.load(json_data)
            #build a list of urls for your device driver buckets 
            for i in data:
                print i
                #check and see if we are running the dia, if so then kill the mcu thread running the xbee so the dia can have full access to the xbee
                if i == "dia" or i == "spider":
                    self.mcu.xbee.runXbee = False
                self.deviceUrlList.append(data[i])
                print i
                print data[i]
                
            pickle.dump( self.deviceUrlList, open( "deviceUrls.p", "wb" ) )
        except Exception,e:
            print "####################"
            print e
            #if we can't get it from the web, look for the pickled version
            try:
                self.deviceUrlList = pickle.load( open( "deviceUrls.p", "rb" ) )
            except:
                print "couldn't load devices from pickle"

        


        


        #try and load your versions dictionary, if this can't load, then load all drivers for the first time
        try:
            self.deviceVersions = pickle.load( open( root + "deviceVersions.p", "rb" ) )
        except:
            print "couldn't load devices Versions from pickle"

        self.deviceList = {}

       
        if self.FLY == False:
            for i in self.deviceUrlList:
                try:
                    print i
                    data = json.load(urllib.urlopen(i + "config.txt"))  # json.load(urllib2.urlopen("http://" + i + "config.txt"))
                    #data = urllib2.urlopen(("http://" + i + "config.txt"))
                    #data = data.read()
                    print data
                    #data = json.load(data)
                
                    #download the files
                    print "trying to download the files"
                    try:
                        if int(data["releaseVersion"]) > int(self.deviceVersions[(data["deviceName"] + "_" + data["driverId"])]):
                            print "new version found in repo", data["releaseVersion"]
                            for x in data["files"]:
                                print (i + data["files"][x])
                                urllib.urlretrieve((i + data["files"][x]), ("./drivers/" + (data["files"][x])))
                        else:
                            print "we have the latest version for: " + (data["deviceName"] + "_" + data["driverId"]) + " of " + str(self.deviceVersions[(data["deviceName"] + "_" + data["driverId"])])
                    except:
                        print "probably didn't have any files to start with, loading all files"
                        for x in data["files"]:
                            print (i + data["files"][x])
                            urllib.urlretrieve((i + data["files"][x]), ("./drivers/" + (data["files"][x])))

                    dList = [ data["driverFileName"].replace(".py", ""), data["deviceName"], data["driverId"], data["releaseVersion"]]
                    self.deviceList[(data["deviceName"] + "_" + data["driverId"])] = dList
                    print self.deviceList
                except Exception,e:
                    print e 
                    continue


        #if our device list is still empty, try and grab the saved one
        if len(self.deviceList) < 1:
            #get the old device list
            try:
                dl = pickle.load( open( "deviceList.p", "rb" ) )
                self.deviceList = dl
                print self.deviceList
            except Exception,e:
                print e
                self.deviceList = {}
                print "couldn't load deviceList from pickle"
        else:
            pickle.dump( self.deviceList, open( "deviceList.p", "wb" ) )
        
            


        

        

        try:
            self.main = main('main', '', self.zigMac, self.mqttQ, self.mcu, self.companyId, self.offset, self.mqtt, self.nodes, self.topics)
        except Exception,e:
            print e


        self.nodes["main"] = self.main

        

        #filename,  node name, 4 digit identifier, version number (must be an integer)


        #gds deviceList
        #deviceList = [ ["mainMistaway", "mainMistaway", "0000", "1"], ["gdsMT", "gdsc", "0005", "1"] ]

        #gate Device List
        #deviceList = [ ["mainMistaway", "mainMistaway", "0000", "1"], ["gate", "gate", "0006", "1"] ]

        for device in self.deviceList:
            print "trying to load: " + device
            
            try:
                device = self.deviceList[device]

                #subscribe to the device first, if it breaks, this makes it possible to fix all of this type at once
                self.topics.append("meshify/files/" + str(device[1]) + "/#")
                self.topics.append("meshify/sets/" + str(device[1]) + "/#")
                topic = str(("meshify/sets/" + str(device[1]) + "/#"))
                print "######", topic
                self.mqtt.subscribe(topic, 0)
                topic = str(("meshify/files/" + str(device[1]) + "/#"))
                print "######", topic
                self.mqtt.subscribe(topic, 0)

                
                #import the file from the devices folder   
                imported_module = __import__("drivers." + str(device[0]))
                #import the code from the device driver
                fileImport = getattr(imported_module, str(device[0]))
                #import the driver class from the file
                funct = getattr(fileImport, "start")
                #start this instance and add it to the devices dictionary
                self.nodes[(str(device[1]) + "_" + str(device[2]))] = funct(name=str(device[1]), number=str(device[2]), mac=self.zigMac, Q=self.mqttQ, mcu=self.mcu, companyId=self.companyId, offset=self.offset, mqtt=self.mqtt, Nodes=self.nodes)



                #add name and version to a dictionary for pickling
                self.deviceVersions[(str(device[1]) + "_" + str(device[2]))] = self.nodes[(str(device[1]) + "_" + str(device[2]))].version
                pickle.dump( self.deviceVersions, open(root + "deviceVersions.p", "wb" ) )




                
                
            except Exception,e:
                print e
                lc = self.getTime()
                value = "Failed Loading: " + str(device[2]) + " on startup with error: " + str(e)
                msg = """[ { "value":"%s", "timestamp":"%s", "msgId":"%s" } ]""" % (value, str(lc), "1")
                topic = "meshify/errors/" 
                self.mqttQ.put([topic, str(msg), 2])
                print e
      


        if self.FLY == False:
            print "made it to here, not a fly"
            #start logging data!!!
            self.reconnecting = True
            thread.start_new_thread(self.sqlPoolThread, ())

            #connect to broker
            #thread.start_new_thread(self.connect_thread, ())
            while True:
                try:
                    self.connect_to_broker()
                    self.reconnecting = False
                    try:
                        os.system("/usr/bin/ntpdate pool.ntp.org")
                        os.system("/usr/sbin/ntpdate pool.ntp.org")
                        os.system("ntpdate pool.ntp.org")
                    except:
                        pass
                    break
                except:
                    print "didn't work this time"
                    time.sleep(30)


        #tell the MQTT client to run forever!!
        print "made it here"
        while True:
            print "##### here is the connection status #### ", str(self.mqtt._state)
            try:
                if not self.FLY:
                    print self.mqtt.loop()
                if self.MCU_ON:
                    if self.mcu.cutAllDataOff:
                        print "All Data is Being cut off, no outbound alloud"
                        time.sleep(5)
                        continue

                if not self.mqttQ.empty(): #or self.SQLQ.getLen() > 0: 
                    if str(self.mqtt._state) == "1" or self.FLY == True:

                        try:
                            print self.SQLQ.getLen() 
                            if self.SQLQ.getLen() > 0:
                                loopCount = 0
                                while self.SQLQ.getLen() > 0:
                                    loopCount += 1
                                    if loopCount > 20:
                                        loopCount = 0
                                        if not self.FLY:
                                            print self.mqtt.loop()
                                    val = self.SQLQ.popleft()
                                    if not self.FLY:
                                        resp = self.mqtt.publish(val[0], val[1], val[2])
                                        
                                    else:
                                        if val[0].split("/")[1] == "db":
                                            xeebVal = json.dumps(json.loads(val[1])[0]["value"])
                                            if xeebVal.startswith('"') and xeebVal.endswith('"'):
                                                xeebVal = xeebVal[1:-1]
                                            upld = val[0].split("/")[3] + "/" + val[0].split("/")[4] + "/" + val[0].split("/")[5] + "/" + xeebVal 
                                            self.xbeeSend(upld)
                                            time.sleep(.5)
                                        else:
                                            respId = (''.join(random.choice('0123456789ABCDEF') for i in range(4)))
                                            self.xbeeSend("%%" + val[0] + "%%" + json.dumps(json.loads(val[1])[0]["value"]) + "%%" )
                                        
                        except Exception, e:
                            print e
                            print "no SQL Queue on this device"
                                
                        try:
                            val = self.mqttQ.get(block=False, timeout=1)
                            #print "Outputting: ", val
                            if not self.FLY:
                                resp = self.mqtt.publish(val[0], val[1], val[2])
                            elif self.mcu.xbee.fileTransfer == True:
                                #if we are sending a file, put this data point back in the Q
                                self.mqttQ.put(val)
                                time.sleep(3)
                                continue
                            else:
                                if val[0].split("/")[1] == "db":
                                    xeebVal = json.dumps(json.loads(val[1])[0]["value"])
                                    if xeebVal.startswith('"') and xeebVal.endswith('"'):
                                        xeebVal = xeebVal[1:-1]
                                    upld = val[0].split("/")[3] + "/" + val[0].split("/")[4] + "/" + val[0].split("/")[5] + "/" + xeebVal
                                    self.xbeeSend( upld )
                                else:
                                    self.xbeeSend("%%" + val[0] + "%%" + json.dumps(json.loads(val[1])[0]["value"]) + "%%" )
                                time.sleep(2)
                            #print "####### here is the response"
                            #make a dictionary of response codes xbee
                            #print resp
                        except:
                            print "Q had an error"
                            time.sleep(1)
                        loopCount = 0
                        while self.mqttQ.qsize() > 20:
                            loopCount += 1
                            if loopCount > 20:
                                loopCount = 0
                                if not self.FLY:
                                    print self.mqtt.loop()
                            try:
                                val = self.mqttQ.get(block=False, timeout=1)
                                #print "Outputting: ", val

                                if not self.FLY:
                                    resp = self.mqtt.publish(val[0], val[1], val[2])
                                elif self.mcu.xbee.fileTransfer == True:
                                    #if we are sending a file, put this data point back in the Q
                                    self.mqttQ.put(val)
                                    time.sleep(3)
                                    continue
                                else:
                                    if val[0].split("/")[1] == "db":
                                        xeebVal = json.dumps(json.loads(val[1])[0]["value"])
                                        if xeebVal.startswith('"') and xeebVal.endswith('"'):
                                            xeebVal = xeebVal[1:-1]
                                        upld = val[0].split("/")[3] + "/" + val[0].split("/")[4] + "/" + val[0].split("/")[5] + "/" + xeebVal
                                        self.xbeeSend(upld)

                                    else:
                                        self.xbeeSend("%%" + val[0] + "%%" + json.dumps(json.loads(val[1])[0]["value"]) + "%%" )
                                    time.sleep(2)
                                
                            except:
                                print "Q had an error"
                                time.sleep(1)
                    
                        
                
            except Exception,e:
                print e
                time.sleep(10)
                if self.reconnecting == False:
                    self.recon()
            time.sleep(.5)
            
            

    def connect_thread(self):
        while True:
            try:
                print "####### connecting to the broker ########"
                self.connect_to_broker()
                
                
            except Exception,e:
                print(str(e))
                print "didn't work to connect, restarting...."
                os.system('/root/reboot')
                
    def connect_to_broker(self):

        if self.companyId == "1":
            meshData = meshifyData.meshifyData(self.mac)
            self.offset, self.dst, self.companyId = meshData.getdata()
        
        
        self.mqtt.connect(broker, port, keepalive=120)
        self.topic_sub()

        #tell the MQTT client to run forever!!
        #self.mqtt.loop_forever()
       
            
    def on_disconnect(self, mosq, userdata, rc):
        print "################ DISCONECCTED #################"

        #turn off connected LED
        if self.MCU_ON:
            self.mcu.ledControl(2,0,0)

        self.recon()
        

    def connect_check(self):
        #this funtion checks to see how many times its tried to reconnect in the 3 minutes that it goes to sleep
        #if it wakes up and you are on the same attempt, then its froze and needs to reboot
        local_count = self.count
        time.sleep(180)
        if local_count == self.count:
            #Dont reboot if connected to SAT
            if self.SAT_COM == True:
                pass
            else:
                os.system('/root/reboot')



    def sqlPoolThread(self):

        #while spooling the data I am going to attempt a handshake with the SkyWave satellites 
        #handshake data will include my mac address
        #the web will return my current UTC time, which by the time I get it, it will be off by a few seconds, but whos counting ;)
        #if it connects, it will set a variable called SAT_COM to True, by way of the main device
        print "starting up sat connection"

        #start a Queue for the sending up of data to the SATS
        satQ = Queue.Queue()
        if SAT == True and self.FLY == False:
            thread.start_new_thread(SkyWaveDataAPI.skywave, (self.sets, self.mac, self.stateData, satQ, self.mcu))

        #wait 1 minute to see if we connect to the SATs
        time.sleep(60)
        try:
            while self.reconnecting == True:
                val = self.mqttQ.get()
                try:
                    if self.SQLQ.getLen() > 5000:
                        #delete oldest value
                        trash = self.SQLQ.popleft()
                    
                except:
                    pass
                if self.SAT_COM == True:
                    print "sending up data to sats"
                    satQ.put(val)
                else:
                    print "storing up data for later 3g connection"
                    try:
                        self.SQLQ.append(val)
                    except:
                        pass
        except:
            pass

    def recon(self):
        self.reconnecting = True
        thread.start_new_thread(self.sqlPoolThread, ())
        count = 0
        while True:
            
            if count > 2000:
                if self.SAT_COM == True:
                    count = 0
                else:
                    break
                
            count += 1
            print count
            try:
                self.count = count
                thread.start_new_thread(self.connect_check, ())
                self.mqtt.reconnect()
                self.count = 0
                self.reconnecting = False
                break
            except:
                print "couldn't reconnect, retrying in 30 seconds"
                os.system("/bin/echo nameserver 8.8.8.8 > /etc/resolv.conf")
                os.system("/sbin/ifup 3g")
                time.sleep(30)
                
        
        if count > 2000 and not self.FLY:
            #don't reboot if connected to SAT
            print "rebooting now"
            os.system('/root/reboot')
            
    
    def on_connect(self, mosq, userdata, rc):

        #turn connected LED
        if self.MCU_ON:
            self.mcu.ledControl(2,1,0)
            self.mcu.ledControl(3,0,0)


        
        #stop using sat data 
        self.SAT_COM = False

        # let the watchdog know we are not on SAT anymore
        os.system('/bin/echo False > /root/SAT')

        #wait a few seconds for the connection to be made solid
        time.sleep(4)

        #set the channel connected to true
        lc = self.getTime()
        topic = 'meshify/db/%s/%s/%s/%s' % (self.companyId, self.mac, self.deviceName, "connected")
        msg = """[ { "value":"%s", "timestamp":"%s" } ]""" % ("True", str(lc))
        self.mqttQ.put([topic, msg, 2])

        #set the network to 3g
        lc = self.getTime()
        topic = 'meshify/db/%s/%s/%s/%s' % (self.companyId, self.mac, self.deviceName, "net")
        msg = """[ { "value":"%s", "timestamp":"%s" } ]""" % ("3g", str(lc))
        self.mqttQ.put([topic, msg, 2])
            
        print(" ############### Connection returned " + str(rc) + " ###############")
        self.topic_sub()
        

    def topic_sub(self):
        for topic in self.topics:
            print topic
            self.mqtt.subscribe(topic, 0)

    def sets(self, msg, sch=False):
        entireMsg = msg
        #[{"user":"demo@meshify.com","mac":"000CE373293D","company":"188","payload":{"name":"wipom_[00:0c:e3:73:29:3d:00:21]!.do2","value":"1","expires":"1389369695"},"msgId":4478}]
        print "I got the set"
        print msg
        try:
            data = json.loads(msg)
            data = data[0]
            msgId = str(data['msgId'])
            data = data['payload']
            name = data['name']
            value = data['value']
            expires = data['expires']
            print name, value, expires
            
            #name = 'oulet_[00:13:a2:00:40:a0:48:cb]!.switch'
            # grab the 4 digit unique device code from the end of the MAC address

            
            n = name.split('.')
            channel = n[1]
            n = n[0]

            try:
                #if the first part of the zigbee mac address is legit, meaning it comes from digi
                #then I need to treat this like a mesh node and send it to the dia
                #This is only for the SPIDER's Dia Nodes
                #the best check is to see if the addresses are derived from the same address
                if name.split('.')[0].split("_")[1].replace("[", "").replace(":", "").replace("]!", "")[:-10].upper() == "0013A2":
                    print "found an xbee"
                    #setData = """<data><channel_set name="%s" value="%s"/></data>$$$%s""" % (name, value, msgId)
                    setData = {}
                    setData['name'] = name
                    setData['value'] = value
                    setData['id'] = msgId
                    print setData
                    self.main.meshQ.put(setData)
                    return
            except:
                print "couldn't determine if there was an xbee"

            
            if n == "main":
                if channel == "SAT":
                    print "got ping from sat cloud app, this mean we have a connection"
                    try:
                        if float(value) > 1422910000:
                            print "SAT CONNECTED!!!"
                            self.SAT_COM = True
                            #turn connected LED to amber
                            if self.MCU_ON:
                                self.mcu.ledControl(3,1,0)
                                self.mcu.ledControl(2,0,0)
                            #send connected = True
                            lc = self.getTime()
                            topic = 'meshify/db/%s/%s/%s/%s' % (self.companyId, self.mac, self.deviceName, "connected")
                            msg = """[ { "value":"%s", "timestamp":"%s" } ]""" % ("True", str(lc))
                            self.mqttQ.put([topic, msg, 2])

                            #set the network to sat
                            lc = self.getTime()
                            topic = 'meshify/db/%s/%s/%s/%s' % (self.companyId, self.mac, self.deviceName, "net")
                            msg = """[ { "value":"%s", "timestamp":"%s" } ]""" % ("sat", str(lc))
                            self.mqttQ.put([topic, msg, 2])

                            # let the watchdog know if we are on SAT
                            os.system('/bin/echo True > /root/SAT')
                    except:
                        print "didn't send the right date"
                nodeName = "main"
                nodeNumber = ""
            
            else:
                m = n
                m = m.split('_')
                nodeName = m[0]
                n = n.replace(']!', '')
                n = n[-5:]
                nodeNumber = n.replace(':', '')
                nodeNumber = "_" + nodeNumber
        except:
            print "not valid JSON"
            return
        


        #check and see if you are setting the scheduler
        if channel.startswith("sch-"):
            print "data now being sent to the scheduler"
            try:
                if self.schedule != False:
                    self.schedule.message(channel, json.loads(entireMsg))
                    return
            except:
                print "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
                print "BAD JSON"
                return



        #this grabs the class for the driver for the node: #this should be called className
        funcName = nodeName + nodeNumber
        #this grabs the method for that channel inside of the driver for that node:
        funcChan = nodeName + '_' + channel
        print funcName
        #try:
        #    # if nodes[funcName] != undefined
        #        #channelCallback = getattr(nodes[funcName], funcChan)
        #        #success = channelCallback(channel, value)
        #    func = getattr(self, funcName)
        #except:
        #    print 'no Set callback found for channel: ' + funcName
        #else:
        try:
            #classFunc = getattr(func, funcChan)  #func(value)
            #success = classFunc(channel, value)

            #first try a specific callback set, the fundtion will look like: deviceName_0000
            try:
                print "trying to find callback for:"
                print funcChan
                channelCallback = getattr(self.nodes[funcName], funcChan)
                success = channelCallback(channel, value)
            except:
                print "looking for genericSet"
                #now try a generic one, that looks like self.genericSet(self, channel, value, UnitNumber) Unit number is the second to last 2 digits of the tech name
                channelCallback = getattr(self.nodes[funcName], "genericSet")
                try:
                    success = channelCallback(channel, value, nodeNumber[1:3], nodeNumber[1:])
                except:
                    success = channelCallback(channel, value, nodeNumber[1:3])

            if success == True:
                if int(msgId) == 0:
                    return 0
                lc = self.getTime()
                if sch == False:
                    value = str(self.mac) + " Success Setting: " + channel + " To: " + value
                    msg = """[ { "value":"%s", "timestamp":"%s", "msgId":"%s" } ]""" % (value, str(lc), msgId)
                    """ """
                    topic = "meshify/responses/" + msgId
                    self.mqttQ.put([topic, str(msg), 2])
                else:
                    return 0
                
            else:
                if sch == False:
                    lc = self.getTime()
                    if success == False:
                        reason = "(Internal Gateway/Device Error)"
                    else:
                        reason = success
                    value = str(self.mac) + " Failed Setting: " + channel + " To: " + value + " " + reason
                    msg = """[ { "value":"%s", "timestamp":"%s", "msgId":"%s" } ]""" % (value, str(lc), msgId)
                    topic = "meshify/responses/" + msgId
                    self.mqttQ.put([topic, str(msg), 2])
                else:
                    return 1
        except:
            if int(msgId) == 0:
                return 2
            if sch == False:
                lc = self.getTime()
                value = str(self.mac) + " Failed Setting: " + channel + " To: " + value + " (No Callback Found)"
                msg = """[ { "value":"%s", "timestamp":"%s", "msgId":"%s" } ]""" % (value, str(lc), msgId)
                topic = "meshify/responses/" + msgId
                self.mqttQ.put([topic, str(msg), 2])
                print 'no Set callback found for channel: ' + funcName
            else:
                return 2
                
    
    #function to be called when a message is received
    def handle_message(self, topic, payload, qos):
        try:
            
            
            print("Message received on topic "+topic+" with QoS "+str(qos))
            topics = topic.split("/")
            if topics[1] == "files" and topics[4] == "write":
                self.OK2Send = False
                path = topics[5]
                path = path.replace("$", "/")
                print path
                with open(path, 'wb') as fd:
                    fd.write(payload)
                    fd.close()
                    print "file written"
                #update the channel mainMistaway_files, a dummy channel for keeping track of file transactions
                lc = self.getTime()
                topic = 'meshify/db/%s/%s/%s/%s' % (self.companyId, self.mac, self.deviceNameMain, "files")
                msg = """[ { "value":"%s", "timestamp":"%s" } ]""" % ((str(self.mac) + " File Written: " + path), str(lc))
                self.mqttQ.put([topic, msg, 2])
            elif topics[1] == "files" and topics[4] == "get":

                self.OK2Send = False
                path = topics[5]
                mqttpath = path
                path = path.replace("$", "/")
                print path
                f = open(path, 'rb')
                byteArray = f.read()
                #byteArray = bytes(byteArray)
                topic = 'meshify/get/%s/%s/%s' % (self.companyId, self.mac, mqttpath)
                msg = byteArray
                self.mqtt.publish(topic, msg, 0)
                f.close()
                print "message sent on topic: ", topic
                
                #update the channel mainMistaway_files, a dummy channel for keeping track of file transactions
                lc = self.getTime()
                topic = 'meshify/db/%s/%s/%s/%s' % (self.companyId, self.mac, self.deviceNameMain, "files")
                msg = """[ { "value":"%s", "timestamp":"%s" } ]""" % ((str(self.mac) + " File Sent: " + path), str(lc))
                self.mqttQ.put([topic, msg, 2])
            elif topics[1] == "files" and topics[4] == "delete" and payload == "delete":
                path = topics[5]
                path = path.replace("$", "/")
                val = "Success Deleting "
                try:
                    os.remove(path)
                except OSError, e:  ## if failed, report it back to the user ##
                    val = "Error Deleting "
                    print ("Error: %s - %s." % (e.filename,e.strerror))
                    
                #update the channel mainMistaway_files, a dummy channel for keeping track of file transactions
                lc = self.getTime()
                topic = 'meshify/db/%s/%s/%s/%s' % (self.companyId, self.mac, self.deviceNameMain, "files")
                msg = """[ { "value":"%s", "timestamp":"%s" } ]""" % ((val + path), str(lc))
                self.mqttQ.put([topic, msg, 2]) 
            elif topics[1] == "sets":
                self.sets(payload)
            self.OK2Send = True
        except Exception,e:
            print e
            self.OK2Send = True
            print "error understanding the mqtt message"
        
                
    def on_message(self, mosq, obj, msg):

        try:
            print msg
        
            #if the message has either a device name or the mac address of this unit then send to handle_message if not send to dia
            #if the name isn't hex, then its an ascii group set
            try:
                num = int(msg.topic.split("/")[2], 16)
                is_hex = True
            except:
                is_hex = False

            try:
                #if the device is in the xbeeQ lookup dictionary, then pass it there
                devName = json.loads(msg.payload)[0]["payload"]["name"].split(".")[0]
                if devName in self.mcu.xbees:
                    #this is an xbee node running the dia
                    xbeeSet = self.mcu.xbees[devName]
                    xbeeSet.put([msg.topic, msg.payload])
                    return
            except Exception, e:
                print e
                print "error parsing set for xbee"
            #case 1, the message is meant for me or I'm a fly
            #case 2, the company ID is a number, not a word, try the set to the xbee again i guess??
            #case 3, the compnay id was actually a group, send it to both the 
            if msg.topic.split("/")[3] == self.mac or self.FLY == True:
                thread.start_new_thread(self.handle_message, (msg.topic, msg.payload, msg.qos))
            elif is_hex:
                xbeeSet = self.mcu.xbees[msg.topic.split("/")[3]]
                xbeeSet.put([msg.topic, msg.payload])
            else:
                #this is a group, so set both
                thread.start_new_thread(self.handle_message, (msg.topic, msg.payload, msg.qos))
                xbeeSet = self.mcu.xbees[msg.topic.split("/")[3]]
                xbeeSet.put([msg.topic, msg.payload])
        except:
            pass

        

    # this retrieves the MAC address from the ethernet card    
    def getHwAddr(self, ifname):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        info = fcntl.ioctl(s.fileno(), 0x8927,  struct.pack('256s', ifname[:15]))
        return ''.join(['%02x:' % ord(char) for char in info[18:24]])[:-1]



    def stateData(self):
        return self.SAT_COM, self.reconnecting

    def getTime(self):
        return str(int(time.time() + int(self.offset)))
    # Here is the spot for all of your channel set callbacks
    # Callbacks are to be writen with the following nameing scheme:
    # deviceName_DeviceId_ChannelName
    # the function will take in the new value it is getting set to
    # for any action to take place on that channel set you must define a callback
    # with the name defined by the nameing scheme above.

    def debugThread(self):

        #this thread is reading the system output of the core as its runs and publishes it to 
        #the topic: meshify/debug/macaddress
        
        try:
            print 'Number of arguments:', len(sys.argv), 'arguments.'
            if  str(sys.argv[1]).lower().strip() == "debug=true" or  str(sys.argv[1]).lower().strip() == "debug = true" or str(sys.argv[1]).lower().strip() == "true":
                try:
                    if len(str(sys.argv[2]).lower().strip()) > 2:
                        fileLocation = str(sys.argv[2]).lower().strip()
                    else:
                        fileLocation = "/tmp/main.log"
                except:
                    fileLocation = "/tmp/main.log"

                file = open(fileLocation, 'r+')
                while 1:
                    where = file.tell()
                    line = file.readline()
                    if not line:
                        file.seek(where)
                        file.truncate(0)
                        time.sleep(1)
                        file.seek(0) 
                    else:
                        topic = "meshify/debug/" + self.mac
                        msg = filter(lambda x: x in string.printable,str(line))
                        self.mqttQ.put([topic, msg, 0])
        except Exception, e:
            print "debug error"
            print e


    def xbeeSend(self, data):
        
        respId = (''.join(random.choice('0123456789ABCDEF') for i in range(4)))
        data = data + respId + "$"
        count = 0
        
        while True and self.mcu.xbee.fileTransfer == False:
            if count > 5:
                print "failed getting response after 3 tries"
                if self.xbeeConnected == True:
                    self.xbeeConnected = False
                    #broadcast to coordinator 
                    #self.mcu.xbee.atCommandSet("DH", "0")
                    #self.mcu.xbee.atCommandSet("DL", "FFFF")
                    #turn off connected LED
                    if self.MCU_ON:
                        self.mcu.ledControl(2,0,0)
                        self.mcu.ledControl(1,0,0)
                    # let the watchdog know we are not connected to the SPIDER
                    os.system('/bin/echo False > /root/XBEE')
                return False
            count += 1
            try:
                self.mcu.xbee.write(base64.b64encode(data.encode('utf-8')))
            except Exception,e:
                print "error writing xbee to gateway"
                print e
            inner_count = 0
            while True and self.mcu.xbee.fileTransfer == False:
                inner_count += 1
                time.sleep(.5)
                if respId in self.xbeeResponseList:
                    print "id found!!!"
                    if self.xbeeConnected == False:
                        self.xbeeConnected = True
                        #turn connected LED
                        if self.MCU_ON:
                            self.mcu.ledControl(2,1,0)
                            self.mcu.ledControl(1,1,0)
                        # let the watchdog know we are connected to the SPIDER
                        os.system('/bin/echo True > /root/XBEE')
                    return True
                elif inner_count > 12:
                    print "no response found"
                    break

    def xbeeGetThread(self):
        #build a list of last 20 responses ie: if id in listofIds then OK
        #when the ID's start populating, turn connected on!! LED
        self.xbeeResponseList = []
        self.xbeeConnected = False
        data = ""
        while True:
            if self.mcu.xbee.fileTransfer == True:
                time.sleep(5)
                continue
            else:
                try:
                    newData = self.mcu.xbee.read()
                    if newData != "":
                        data += newData
                        print data
                        if "$$" in data:
                            list_of_sets = data.split("$$")
                            if len( list_of_sets[len(list_of_sets) - 1]) < 1:
                                data = ""
                                del list_of_sets[-1]
                            else: 
                                data = list_of_sets[len(list_of_sets) - 1]
                                del list_of_sets[-1]
                            for item in list_of_sets:
                                if len(item) == 4:
                                    print "new response id", item
                                    self.xbeeResponseList.append(item)
                                    if len(self.xbeeResponseList) > 20:
                                        self.xbeeResponseList.pop(0)
                                    continue
                                print "we have a complete message"
                                topic = item.split("%%")[1]
                                payload = item.split("%%")[2]
                                self.handle_message(topic, payload, 1)
                                time.sleep(2)
                    else:
                        time.sleep(.5)
                        continue

                except Exception,e:
                    print "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
                    print "xbee read error"
                    print e
                    time.sleep(1)
    
def startMain():
    try:
        test = meshifyMain()
    except:
        pass
startMain()
