import types
import traceback
import binascii
import threading
import time
import thread
import os
import struct
import sys
import textwrap
import Queue
import json


class deviceBase():

    def __init__(self, name=None, number=None, mac=None, Q=None, mcu=None, companyId=None, offset=None, mqtt=None, Nodes=None):
        self.offset = offset
        self.company = companyId
        self.name = name
        self.number = number 
        self.q = Q
        self.deviceName = name + '_[' + mac +  ':' + number[0:2] + ':' + number[2:] + ']!'
        self.chName = "M1" + '_[' + mac + ':'
        self.chName2 = '_[' + mac + ':'
        print 'device name is:'
        print self.deviceName
        mac2 = mac.replace(":", "")
        self.mac = mac2.upper()
        self.address = 1
        self.debug = True
        self.mcu = mcu
        self.firstRun = True
        self.mqtt = mqtt
        self.nodes = Nodes
        #local dictionary of derived nodes ex: localNodes[tank_0199] = self
        self.localNodes = {}
        os.system("chmod 777 /root/reboot")
        os.system("echo nameserver 8.8.8.8 > /etc/resolv.conf")
        #Queue for imcoming sets
        self.loraQ = Queue.Queue()

        self.knownIDs = []
        thread.start_new_thread(self.getSetsThread, ())
        
    def getSetsThread(self):

        while True:
            try:
                item = self.loraQ.get(block=True, timeout=600)
                try:
                    print "here is the item from the sets q"
                    print item
                    if len(item) == 2:
                        techname = str(json.loads(item[1])[0]['payload']['name'].split(".")[0])
                        channel = str(json.loads(item[1])[0]['payload']['name'].split(".")[1])
                        name = techname.split("_")[0]
                        id = techname.split("_")[1][1:-2].replace(":","").upper()
                        value = json.loads(item[1])[0]['payload']['value']
                        msgId = json.loads(item[1])[0]['msgId']

                        print channel, value, id, name, msgId
                        success = self.specificSets(channel, value, id, name)
                                                  
                        if success == True:
                            print "SUCCESS ON SET"
                            if int(msgId) == 0:
                                return
                            lc = self.getTime()

                            value = str(self.mac) + " Success Setting: " + channel + " To: " + value
                            msg = """[ { "value":"%s", "timestamp":"%s", "msgId":"%s" } ]""" % (value, str(lc), msgId)
                            print value
                            print msg
                            topic = "meshify/responses/" + str(msgId)
                            print topic
                            self.q.put([topic, str(msg), 2])

                
                        else:

                            lc = self.getTime()
                            if success == False:
                                reason = "(Internal Gateway/Device Error)"
                            else:
                                reason = success
                            value = str(self.mac) + " Failed Setting: " + channel + " To: " + value + " " + reason
                            msg = """[ { "value":"%s", "timestamp":"%s", "msgId":"%s" } ]""" % (value, str(lc), msgId)
                            topic = "meshify/responses/" + msgId
                            self.q.put([topic, str(msg), 2])
                       
                except:
                    if int(msgId) == 0:
                        return 
                    lc = self.getTime()
                    value = str(self.mac) + " Failed Setting: " + channel + " To: " + value + " (No Callback Found)"
                    msg = """[ { "value":"%s", "timestamp":"%s", "msgId":"%s" } ]""" % (value, str(lc), msgId)
                    topic = "meshify/responses/" + msgId
                    self.q.put([topic, str(msg), 2])
                    print 'no Set callback found for channel: ' + funcName

            except:
                print "sets queue timeout, restarting..."
            

    def sendtodbDevLora(self, id, channel, value, timestamp, deviceName):

       

        mac = self.mac
        
        if deviceName == "mainMeshify":
            zigmac = "_[01:00:00:00:00:" + id[0:2] + ":" + id[2:4] + ":" + id[4:6] + "]!"
        else:
            zigmac = "_[00:00:00:00:00:" + id[0:2] + ":" + id[2:4] + ":" + id[4:6] + "]!"
        dname = deviceName + zigmac

        #define dname, make id into techname and mac
        if id not in self.knownIDs:
            self.knownIDs.append(id)
            self.mcu.xbees[dname] = self.loraQ

        #meshify/db/330/C493000354FB/ilora/c493000354fb2A6E/a1-v
        #[ { "value":"0.5635", "timestamp":"1486039316" } ]

        if int(timestamp) == 0:
            timestamp = self.getTime()
        
        topic = 'meshify/db/%s/%s/%s/%s' % (self.company, mac, dname, channel)
        print topic
        msg = """[ { "value":"%s", "timestamp":"%s" } ]""" % (str(value), str(timestamp))
        print msg
        self.q.put([topic, msg, 0])

    def sendtodbLocLora(self, id, channel, value, timestamp, deviceName):

       

        mac = id
        while len(mac) < 12:
            mac = "0" + mac
        if deviceName == "mainMeshify":
            zigmac = "_[01:00:00:00:00:" + id[0:2] + ":" + id[2:4] + ":" + id[4:6] + "]!"
        else:
            zigmac = "_[00:00:00:00:00:" + id[0:2] + ":" + id[2:4] + ":" + id[4:6] + "]!"
        dname = deviceName + zigmac

         #define dname, make id into techname and mac
        if id not in self.knownIDs:
            self.knownIDs.append(id)
            topic = str(("meshify/sets/" + str(self.company) + "/" + mac + "/#"))
            self.mqtt.subscribe(topic, 0)
            topic = str(("meshify/sets/" + "1" + "/" + mac + "/#"))
            self.mqtt.subscribe(topic, 0)
            self.mcu.xbees[dname] = self.loraQ

        #meshify/db/330/C493000354FB/ilora/c493000354fb2A6E/a1-v
        #[ { "value":"0.5635", "timestamp":"1486039316" } ]

        if int(timestamp) == 0:
            timestamp = self.getTime()
        
        topic = 'meshify/db/%s/%s/%s/%s' % (self.company, mac, dname, channel)
        print topic
        msg = """[ { "value":"%s", "timestamp":"%s" } ]""" % (str(value), str(timestamp))
        print msg
        self.q.put([topic, msg, 0])

    def sendtodbLocLoraCom(self, id, channel, value, timestamp, deviceName):

       

        mac = "1" + id
        while len(mac) < 12:
            mac = "0" + mac

        if deviceName == "mainMeshify":
            zigmac = "_[01:00:00:00:00:" + id[0:2] + ":" + id[2:4] + ":" + id[4:6] + "]!"
        else:
            zigmac = "_[00:00:00:00:01:" + id[0:2] + ":" + id[2:4] + ":" + id[4:6] + "]!"
        dname = deviceName + zigmac

         #define dname, make id into techname and mac
        if id not in self.knownIDs:
            self.knownIDs.append(id)
            topic = str(("meshify/sets/" + str(self.company) + "/" + mac + "/#"))
            self.mqtt.subscribe(topic, 0)
            topic = str(("meshify/sets/" + "1" + "/" + mac + "/#"))
            self.mqtt.subscribe(topic, 0)
            self.mcu.xbees[dname] = self.loraQ

        #meshify/db/330/C493000354FB/ilora/c493000354fb2A6E/a1-v
        #[ { "value":"0.5635", "timestamp":"1486039316" } ]

        if int(timestamp) == 0:
            timestamp = self.getTime()
        
        topic = 'meshify/db/%s/%s/%s/%s' % (self.company, mac, dname, channel)
        print topic
        msg = """[ { "value":"%s", "timestamp":"%s" } ]""" % (str(value), str(timestamp))
        print msg
        self.q.put([topic, msg, 0])

    def sendtodbLoc(self, ch, channel, value, timestamp, deviceName, mac):


        #this will add your derived nodes the master nodes list, allowing them to receive sets!!
        localNodesName = deviceName + "_" + str(ch) + "99"

        if not self.localNodes.has_key(localNodesName):
            self.localNodes[localNodesName] = True
            self.nodes[localNodesName] = self

        #make the techname 
        lst = textwrap.wrap(str(mac), width=2)
        tech = ""
        for i in range(len(lst)):
            tech += lst[i].lower() + ":"
        

        chName2 = '_[' + tech 

        if int(ch) < 10:
            ch = "0" + str(int(ch))

        if len(ch) > 2:
            ch = ch[:-2]

        dname = deviceName + chName2 + str(ch) + ":98]!"

        if int(timestamp) == 0:
            timestamp = self.getTime()
        
        topic = 'meshify/db/%s/%s/%s/%s' % (self.company, mac, dname, channel)
        print topic
        msg = """[ { "value":"%s", "timestamp":"%s" } ]""" % (str(value), str(timestamp))
        print msg
        self.q.put([topic, msg, 0])

    def sendtodbDevJSON(self, ch, channel, value, timestamp, deviceName):

        if int(ch) < 10:
            ch = "0" + str(int(ch))
        dname = deviceName + self.chName2 + str(ch) + ":99]!"
        if int(timestamp) == 0:
            timestamp = self.getTime()
        
        topic = 'meshify/db/%s/%s/%s/%s' % (self.company, self.mac, dname, channel)
        print topic
        msg = """[ { "value":%s, "timestamp":"%s" } ]""" % (str(value), str(timestamp))
        print msg
        self.q.put([topic, msg, 0])

    def sendtodbLora(self, ch, channel, value, timestamp, deviceName):

        if ":" not in ch:
            ch = ch[0:2] + ":" + ch[2:4]

        #this will add your derived nodes the master nodes list, allowing them to receive sets!!
        localNodesName = deviceName + "_" + str(ch).replace(':', "")

        if not self.localNodes.has_key(localNodesName):
            self.localNodes[localNodesName] = True
            self.nodes[localNodesName] = self

        

        dname = deviceName + self.chName2 + str(ch) + "]!"

        

        if int(timestamp) == 0:
            timestamp = self.getTime()
        
        topic = 'meshify/db/%s/%s/%s/%s' % (self.company, self.mac, dname, channel)
        print topic
        msg = """[ { "value":"%s", "timestamp":"%s" } ]""" % (str(value), str(timestamp))
        print msg
        self.q.put([topic, msg, 0])
        
    def sendtodbDev(self, ch, channel, value, timestamp, deviceName):


        #this will add your derived nodes the master nodes list, allowing them to receive sets!!
        localNodesName = deviceName + "_" + str(ch) + "99"

        if not self.localNodes.has_key(localNodesName):
            self.localNodes[localNodesName] = True
            self.nodes[localNodesName] = self

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
        else:
            timestamp =  str(int(timestamp) + int(self.offset))
        
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
        else:
            timestamp =  str(int(timestamp) + int(self.offset))
        
        topic = 'meshify/db/%s/%s/%s/%s' % (self.company, self.mac, self.deviceName, channel)
        print topic
        msg = """[ { "value":%s, "timestamp":"%s" } ]""" % (str(value), str(timestamp))
        print msg
        self.q.put([topic, msg, 0])
    def getTime(self):
        return str(int(time.time() + int(self.offset)))




