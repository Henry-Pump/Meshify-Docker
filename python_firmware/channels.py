class Channels:
    #handles the serial connection from linux to the MCU to the xbee

    def __init__(self, mqttQ):
        self.q = mqttQ
        self.company
        self.mac
        self.chName
        self.getTime()
        self.chName2
        self.deviceName

        self.channelDict = {}

    def channelCrunch(self, channel, value, sendChange):
        pass
        #check the channel Dictinary and see if the channel has bee seen before
        #if it hasn't then return True, so it will get sent (first time data gets set it always should be pushed to the cloud)
        #if it has been here before then we need to check what kind of data is it (float or string)
        #then find out the change value
        #if the change value is None, then just send it
        #if its a float/int with a changevalue != None, then compare it, if it fails the comparison, save the value as the last value, but don't send it and don't update the last sent value
        #if its a string with a any compare value != None, then compare it to the old string, if its different then send it

    def set(self, name, value, timestamp, change=None, subCh=None, deviceName=None, JSON=False):
        pass
        if JSON == True:
            self.sendtodbJSON(name, value, timestamp, change)
        elif deviceName != None and subCh != None:
            self.sendtodbDevice(subCh, name, value, timestamp, deviceName, change)
        elif deviceName == None and subCh != None:
            self.sendtodbCH(subCh, name, value, timestamp, change)
        else:
            self.sendtodb(name, value, timestamp, change) 


    def sendtodbDevice(self, ch, channel, value, timestamp, deviceName, change):


        if int(ch) < 10:
            ch = "0" + str(int(ch))

        dname = deviceName + self.chName2 + str(ch) + ":99]!"

        

        if int(timestamp) == 0:
            timestamp = self.getTime()

        fullName = dname + "." + channel

        if self.channelCrunch(channel, value, sendChange):
        
            topic = 'meshify/db/%s/%s/%s/%s' % (self.company, self.mac, dname, channel)
            print topic
            msg = """[ { "value":"%s", "timestamp":"%s" } ]""" % (str(value), str(timestamp))
            print msg
            self.q.put([topic, msg, 0])
        
    def sendtodbCH(self, ch, channel, value, timestamp, change):


        if int(ch) < 10:
            ch = "0" + str(ch)

        dname = self.chName + str(ch) + ":99]!"

        

        if int(timestamp) == 0:
            timestamp = self.getTime()

        fullName = dname + "." + channel

        if self.channelCrunch(channel, value, sendChange):
        
            topic = 'meshify/db/%s/%s/%s/%s' % (self.company, self.mac, dname, channel)
            print topic
            msg = """[ { "value":"%s", "timestamp":"%s" } ]""" % (str(value), str(timestamp))
            print msg
            self.q.put([topic, msg, 0])
    
    def sendtodb(self, channel, value, timestamp, change):

        if int(timestamp) == 0:
            timestamp = self.getTime()
            if timestamp < 1400499858:
                return
        
        topic = 'meshify/db/%s/%s/%s/%s' % (self.company, self.mac, self.deviceName, channel)
        print topic
        msg = """[ { "value":"%s", "timestamp":"%s" } ]""" % (str(value), str(timestamp))
        print msg
        self.q.put([topic, msg, 0])
    
    def sendtodbJSON(self, channel, value, timestamp, change):

        if int(timestamp) == 0:
            timestamp = self.getTime()
            if timestamp < 1400499858:
                return
        
        topic = 'meshify/db/%s/%s/%s/%s' % (self.company, self.mac, self.deviceName, channel)
        print topic
        msg = """[ { "value":%s, "timestamp":"%s" } ]""" % (str(value), str(timestamp))
        print msg
        self.q.put([topic, msg, 0])
