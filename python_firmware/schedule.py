import array
import time
import thread
import threading
try:
    import json
except:
    import simplejson as json
import pickle
import datetime
from datetime import tzinfo, timedelta
ZERO = timedelta(0)


class schedule():

    def __init__(self, setCallback, Q, getTime, ):
        self.sets = setCallback
        self.q = Q
        self.getTime = getTime



        print "%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%"
        print "starting scheduler"
        #load any schedules from pickle file
        #if we can't get it from the web, look for the pickled version
        try:
            with open('/root/python_firmware/drivers/schJSON.p', 'rb') as handle:
                self.schedDict = pickle.load(handle)
                
            print "found pickled dictionary"
            print self.schedDict
        except:
            print "couldn't load devices from pickle"
            self.schedDict = {}

        thread.start_new_thread(self.run, ())


    #[{"user":"demo@meshify.com","mac":"000CE373293D","company":"188","payload":{"name":"wipom_[00:0c:e3:73:29:3d:00:21]!.do2","value":"1","expires":"1389369695"},"msgId":4478}]
    #take that object and replace the .d02 (channel name) with the channel name in the scheduler, and the value with the value, then put back into sets

    #add -> update the list of scheduled events, return in time order

    #del -> remove the one with the hash that was sent. [hash, hash, hash]

    def run(self):
        #sleep for a minute to make sure the core is ready
        time.sleep(30)

        try:
            t = self.getTime()
        except:
            #try and sleep another minute
            time.sleep(60)

        print "%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%"
        self.initilizeAll()
        print "running schedule core"
        #here we will loop over the json and send on any sets we need to when we need to
        #how to run this once a minute and make sure we dont miss or repeat???
        #since we only support every 5 minutes of time, how about I look at it every 30 seconds and sleep for 120 if I hit an event.
        while True:
            try:
                print "checking schedule"

                #marker for if we got an event this time:
                didSomethingHappen = False

                #first grab the time using the gettime function
                utc = UTC()

                timeObj = datetime.datetime.fromtimestamp(int(self.getTime()), tz=utc)
                DOW = timeObj.weekday()
                min = timeObj.minute
                if min < 10:
                    min = "0" + str(min)
                hour = timeObj.hour
                if hour < 10:
                    hour = "0" + str(hour)
                tm = str(hour) + ":" + str(min)
                print "here is our time and day of week:"
                print tm, DOW
                #its less likely that a time will match, so first lets check for hours and minutes that match
                for device in self.schedDict:
                    mac = self.schedDict[device]['mac']
                    company = self.schedDict[device]['company']
                    name = self.schedDict[device]['name']
                    
                    
                    events = self.schedDict[device]['events']
                    #print "here are the events:"
                    #print events
                    for event in events:
                        #print "here is the event"
                        event = self.schedDict[device]['events'][event]
                        #print event
                        if event['t'] == tm:
                            print "we have a time match"
                            if DOW in event['d'] or str(DOW) in event['d']:
                                print "activating schedule event"
                                print ("Schedule Set: " + str(event['c']) + " To: " + str(event['v']))
                                didSomethingHappen = True
                                j = event['set']
                                #do the set, then send a message on the log channel that the sceduled event has taken place
                                try:
                                    success = self.sets(j, sch=True)
                                    msg = ""
                                    if success == 0:
                                        print "success"
                                        msg = "Schedule Set: " + str(event['c']) + " To: " + str(event['v'])
                                    if success == 1:
                                        print "error 1"
                                        msg = "Schedule FAILED (internal/driver error) to Set: " + str(event['c']) + " To: " + str(event['v'])
                                    if success == 2:
                                        print "error 2"
                                        msg = "Schedule FAILED (no driver callback) to Set: " + str(event['c']) + " To: " + str(event['v'])
                                    if msg != "":
                                        self.sendtodb('log', msg, 0, company, mac, device)
                                except:
                                    #if one breaks, keep looking
                                    continue

                #sleep for 2 minutes if you had an event, this keeps you from calling an event twice, and you can't miss another event, because it wont happen for a least 5 more min
                if didSomethingHappen:
                    print "sleeping 2 minutes"
                    time.sleep(120)
                else:
                    print "sleeping 28 seconds"
                    time.sleep(28)


                pass
            except Exception,e:
                print e
                time.sleep(28)

    def sendtodb(self, channel, value, timestamp, company, mac, deviceName):
        if int(timestamp) == 0:
            timestamp = self.getTime()
        
        try:
            topic = 'meshify/db/%s/%s/%s/%s' % (company, mac, deviceName, channel)
            print topic
            if channel == "sch-":
                #for the JSON structure I had to take off the " " around the value
                msg = """[ { "value":%s, "timestamp":"%s" } ]""" % (str(value), str(timestamp))
            else:
                msg = """[ { "value":"%s", "timestamp":"%s" } ]""" % (str(value), str(timestamp))
            print msg
            self.q.put([topic, msg, 0])
        except:
            print "didn't work to send up MQTT data"

    def message(self, channel, msg):

        fullmsg = msg
        #[{"user":"demo@meshify.com","mac":"000CE373293D","company":"188","payload":{"name":"wipom_[00:0c:e3:73:29:3d:00:21]!.do2","value":"1","expires":"1389369695"},"msgId":4478}]


        #example value: [{'h':'0123','n':'back to running','c':'start','v': 'On','t': '13:55','d': [0,1,2,3,4,5,6]}, {'h':'0123','n':'back to running','c':'start','v': 'On','t': '13:55','d': [0,1,2,3,4,5,6]},{'h':'0123','n':'back to running','c':'start','v': 'On','t': '13:55','d': [0,1,2,3,4,5,6]}, {'h':'0123','n':'back to running','c':'start','v': 'On','t': '13:55','d': [0,1,2,3,4,5,6]} ]
        #only single quotes for now can be sent
        # [{
        #  'h':0123,
        #  'n':'back to running',
        #  'c':'start',
        #  'v': 'On',
        #  't': '13:55',
        #   'd': [0,1,2,3,4,5,6]
        #   }]
        #channel can be sch-add or sch-del
        

        data = msg[0]
        msgId = str(data['msgId'])
        user = str(data['user'])
        mac = str(data['mac'])
        company = str(data['company'])
        d = data['payload']
        name = d['name'].split('.')[0]
        deviceName = name.split('_')[0]
        
        #for testing, todo: change back
        value = d['value']
        if channel == "sch-add":
            print "adding schedule"
            value = value.replace("'", '"')
            events = json.loads(value)

            #first see if this device has a key in our main dictionary
            if self.schedDict.has_key(name):
                print "device already in dictionary"
            else:
                #add this device to the dictionary
                print "adding device to dictionary"
                self.schedDict[name] = {'events': {}, 'mac':mac, 'company':company, 'name':name}

            #now it has a section for the device, lets start adding the events
            returnStr = ""
            for event in events:
                try:
                    n = event['n']
                    fullmsg[0]['payload']['name'] = (name + "." + event['c'])
                    fullmsg[0]['payload']['value'] = event['v']
                    #set up a dictionary for the event details of this event
                    #consiquently this will erase an event with this same hash, but this is ok
                    print "here is the new key in the event"
                    print event['h']
                    self.schedDict[name]['events'][event['h']] = {'set':str(json.dumps(fullmsg)),'h':event['h'], 'n':event['n'],'c':event['c'],'v':event['v'],'t':event['t'],'d':event['d']}
                    print 'here is the event'
                    print self.schedDict[name]['events'][event['h']]
                except:
                    returnStr += "Failed Adding Schedule Event: " + str(n) + " , "
                else:
                    returnStr += "Success Adding Schedule Event: " + str(n) + " , "
            
            self.sendMsgResp(returnStr, msgId)
            print self.schedDict
            #now send back the updated data to the web
            returnJSON = self.rebuildForDevice(name)
        
        
            fullmsg[0]['payload']['name'] = (name + "." + "sch-")
            fullmsg[0]['payload']['value'] = returnJSON

            print fullmsg

            self.sendtodb('sch-', returnJSON, 0, company, mac, name)


        elif channel == "sch-del":
            returnStr = ""

            print "deleting an event with the ID"
            #in this case the value will be a list of hahses that will be deleted
            value = value.replace("'", '"')
            values = json.loads(value)
            print values
            
            for val in values:
                try:
                    n = self.schedDict[name]['events'][val]['n']
                except:
                    n = "Unknown ID"
                try:
                    del self.schedDict[name]['events'][val]
                except:
                    returnStr += "Failed Deleting Schedule Event: " + str(n) + " , "
                else:
                    returnStr += "Success Deleting Schedule Event: " + str(n) + " , "

            self.sendMsgResp(returnStr, msgId)
            #now send back the updated data to the web
            returnJSON = self.rebuildForDevice(name)
        
        
            fullmsg[0]['payload']['name'] = (name + "." + "sch-")
            fullmsg[0]['payload']['value'] = returnJSON

            print fullmsg

            self.sendtodb('sch-', returnJSON, 0, company, mac, name)
        elif channel == "sch-sync":
            self.sendMsgResp("Schedule Synced", msgId)
            self.initilizeAll()


        #update persistant dictionary
        with open('/root/python_firmware/drivers/schJSON.p', 'wb') as handle:
            pickle.dump(self.schedDict, handle)


        

        
        
        #thread.start_new_thread(self.sets, (j,))

        







    def sendMsgResp(self, val, msgId):
        lc = self.getTime()
        value = val
        msg = """[ { "value":"%s", "timestamp":"%s", "msgId":"%s" } ]""" % (value, str(lc), msgId)
        topic = "meshify/responses/" + msgId
        self.q.put([topic, str(msg), 2])


    def rebuildForDevice(self, name):
        print "building json for return message"
        newJSON = []
        for event in self.schedDict[name]['events']:
            print event
            print self.schedDict[name]['events'][event]['h'], self.schedDict[name]['events'][event]['n'], self.schedDict[name]['events'][event]['c'], self.schedDict[name]['events'][event]['v'], self.schedDict[name]['events'][event]['t'], self.schedDict[name]['events'][event]['d']
            newJSON.append({'h':self.schedDict[name]['events'][event]['h'],
                            'n':self.schedDict[name]['events'][event]['n'],
                            'c':self.schedDict[name]['events'][event]['c'],
                            'v':self.schedDict[name]['events'][event]['v'],
                            't':self.schedDict[name]['events'][event]['t'],
                            'd':self.schedDict[name]['events'][event]['d'],
                            })
        data = str(json.dumps(newJSON))
        print "here is the device JSON"
        print data
        return data

        
    def initilizeAll(self):
        #here I want to send all of the current schedules for all devices on startup, this could use a lot of data maybe
        print "updating everything on startup"
        for name in self.schedDict:
            mac = self.schedDict[name]['mac']
            company = self.schedDict[name]['company']
            name = self.schedDict[name]['name']
            msg = self.rebuildForDevice(name)
            self.sendtodb('sch-', msg, 0, company, mac, name)

            
        pass


class UTC(tzinfo):
    """UTC"""
    def utcoffset(self, dt):
        return ZERO
    def tzname(self, dt):
        return "UTC"
    def dst(self, dt):
        return ZERO

utc = UTC()