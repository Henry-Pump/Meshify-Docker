import array
import time
import thread
import threading
import sys
import os
sys.path.insert(0, '/WEB/python/simplejson-2.zip')
import simplejson as json
import datetime
from datetime import tzinfo, timedelta
ZERO = timedelta(0)

rootPath = "WEB/python/"
rootPath2 = "/userfs/WEB/python/"


#<channel_set name="outlet_[00:13:a2:00:40:a0:48:cb]!.switch" value="off"/>
#that will be sent to the


class schedule:

    def __init__(self, rci1, getTime, mc):
        self.getTime = getTime
        self.rci = rci1
        self.mc = mc



        print "%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%"
        print "starting scheduler"
        #load any schedules from pickle file
        #if we can't get it from the web, look for the pickled version
        try:
            #self.schedDict = pickle.load( open( (rootPath + "schJSON.p"), "rb" ) )
            try:
                f = open((rootPath + "schJSON.p"),'r')
            except:
                f = open((rootPath2 + "schJSON.p"),'r')
            data = f.read()
            self.schedDict = json.loads(data)
            print "found pickled dictionary"
            print self.schedDict
        except:
            print "couldn't load schedule file from pickle"
            self.schedDict = {}

        thread.start_new_thread(self.run, ())
        thread.start_new_thread(self.fileCheckThread, ())


    #[{"user":"demo@meshify.com","mac":"000CE373293D","company":"188","payload":{"name":"wipom_[00:0c:e3:73:29:3d:00:21]!.do2","value":"1","expires":"1389369695"},"msgId":4478}]
    #take that object and replace the .d02 (channel name) with the channel name in the scheduler, and the value with the value, then put back into sets

    #add -> update the list of scheduled events, return in time order

    #del -> remove the one with the hash that was sent. [hash, hash, hash]

    def fileCheckThread(self):
        while True:
            try:
                try:
                    f = open((rootPath + "schJSON.p"),'r')
                except:
                    f = open((rootPath2 + "schJSON.p"),'r')
                data = file.read()
                file.close()
                #!!!!delete the file!!!
                os.remove(rootPath + "schedule.json")
                self.message(data, "sch-add")
                self.initilizeAll()
            except:
                time.sleep(10)
                print "didn't find the json file"


    def run(self):
        #sleep for a minute to make sure the core is ready
        time.sleep(30)

        try:
            t = self.getTime()
        except:
            #try and sleep another minute
            time.sleep(60)
            t = self.getTime()

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
                tm = str(hour) + ":" + str(min)
                print "here is our time and day of week:"
                print tm, DOW
                #its less likely that a time will match, so first lets check for hours and minutes that match

                #now I need to know if the current time "tm" is between 't' and 'et' by looking at 'r' and its value like '5m'
                for device in self.schedDict:
                    #mac = self.schedDict[device]['mac']
                    #company = self.schedDict[device]['company']
                    name = self.schedDict[device]['name']
                    
                    
                    events = self.schedDict[device]['events']
                    #print "here are the events:"
                    #print events
                    for event in events:
                        #print "here is the event"
                        event = self.schedDict[device]['events'][event]
                        #print event


                        timeList = self.getTimes(event['t'], event['et'], event['r'])
                        print tm
                        print timeList
                        if tm in timeList:
                            print "we have a time match"
                            if DOW in event['d'] or str(DOW) in event['d']:
                                print "activating schedule event"
                                print ("Schedule Set: " + str(event['c']) + " To: " + str(event['v']))
                                didSomethingHappen = True
                                j = event['set']
                                #do the set, then send a message on the log channel that the sceduled event has taken place
                                try:
                                    #this is where we do the set
                                    #<channel_set name="outlet_[00:13:a2:00:40:a0:48:cb]!.switch" value="off"/>
                                    obj = json.loads(j)
                                   

                                    name = obj["name"]
                                    value = obj["value"]


                                    setData = """<channel_set name="%s" value="%s"/>""" % (name, str(value))

                                    print "66666666666666666666666666666666666666666666666666666666666666666"
                                    print setData

                                    success = self.rci.setFromSched(setData)
                                    
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
                                    #if msg != "":
                                    #    self.sendtodb('log', msg, name.split(".")[0])
                                except:
                                    #if one breaks, keep looking
                                    continue

                #sleep for 2 minutes if you had an event, this keeps you from calling an event twice, and you can't miss another event, because it wont happen for a least 5 more min
                if didSomethingHappen:
                    print "sleeping 2 minutes"
                    time.sleep(120)
                else:
                    print "sleeping 28 seconds"
                    time.sleep(10)


                pass
            except Exception,e:
                print e
                time.sleep(28)

    def sendtodb(self, channel, value, name):

        if name.endswith("!"):
            pass
        else:
            name = name + "!"

        #here I need to grab the device manager and look for the device name for the channel set and actually do it here, not returning it to the
        #mistaway driver for the set
        try:
            print "sending to db", channel, value, name
            dm = self.mc.myCore.get_service("device_driver_manager")
            print "worked getting dm"
            newMC = dm.get_driver_object(name)
            print "worked getting the node, now doing the set..."
            print channel
            print value
            print name
            newMC.setProperty(channel, value)
        except:

            print "didn't work to do the set, the reason would have to be the node is no longer on the network"


    def message(self, msg, channel):
        
        
        #msg = [{'tn':'mc13_[00:13:a2:00:40:ba:8a:4c]!','c':'r','d':['0','1','2','3','4','5','6'],'h':'7d8c','n':'Misting from 8am - 10pm every 5 min','t':'08:00','v':'M','et':'22:00','r':'5m','s':'1'}]

        if channel != "sch-sync":
            print "adding schedule part 1"
            msg = msg.replace("'", '"')
            value = json.loads(msg)
            fullmsg = value

        #for digi
        #[{'h':'0123','n':'back to running','c':'start','v': 'On','t': '13:55','d': [0,1,2,3,4,5,6]}, {'h':'0123','n':'back to running','c':'start','v': 'On','t': '13:55','d': [0,1,2,3,4,5,6]},{'h':'0123','n':'back to running','c':'start','v': 'On','t': '13:55','d': [0,1,2,3,4,5,6]}, {'h':'0123','n':'back to running','c':'start','v': 'On','t': '13:55','d': [0,1,2,3,4,5,6]} ]
        
        
        
        
        
        #[{"user":"demo@meshify.com","mac":"000CE373293D","company":"188","payload":{"name":"wipom_[00:0c:e3:73:29:3d:00:21]!.do2","value":"1","expires":"1389369695"},"msgId":4478}]


        #example value: [{'h':'0123','n':'back to running','c':'start','v': 'On','t': '13:55','d': [0,1,2,3,4,5,6]}, {'h':'0123','n':'back to running','c':'start','v': 'On','t': '13:55','d': [0,1,2,3,4,5,6]},{'h':'0123','n':'back to running','c':'start','v': 'On','t': '13:55','d': [0,1,2,3,4,5,6]}, {'h':'0123','n':'back to running','c':'start','v': 'On','t': '13:55','d': [0,1,2,3,4,5,6]} ]
        #only single quotes for now can be sent
        # [{
        #  'h':0123, (hash)
        #  'n':'back to running',
        #  'c':'start',
        #  'v': 'On',
        #  't': '13:55',
        #   'd': [0,1,2,3,4,5,6]
        #   }]
        #channel can be sch-add or sch-del
        

        #data = msg[0]
        #msgId = str(data['msgId'])
        #user = str(data['user'])
        #mac = str(data['mac'])
        #company = str(data['company'])
        #d = data['payload']

        #name = wipom_[00:0c:e3:73:29:3d:00:21]!


        if channel == "sch-add":
            print "adding schedule part 2"
            #value = value.replace("'", '"')
            #events = json.loads(value)
            events = value
            print events

            

            #now it has a section for the device, lets start adding the events
            returnStr = ""
            for event in events:

                name = event['tn'] #wipom_[00:0c:e3:73:29:3d:00:21]!

                deviceName = name.split('_')[0] #wipom

                #first see if this device has a key in our main dictionary
                if self.schedDict.has_key(name):
                    print "device already in dictionary"
                else:
                    #add this device to the dictionary
                    print "adding device to dictionary"
                    self.schedDict[name] = {'events': {}, 'name':name}

                try:
                    n = event['tn'] + "!." + event['c'] #mc13z_[00:13:a2:00:40:ba:8a:4c]!.r
                    
                    obj = {}
                    obj["name"] = n
                    obj["value"] = event['v']

                    #set up a dictionary for the event details of this event
                    #consiquently this will erase an event with this same hash, but this is ok
                    print "here is the new key in the event"
                    print event['h']
                    self.schedDict[name]['events'][event['h']] = {'set':str(json.dumps(obj)),'tn':event['tn'],'h':event['h'], 'n':event['n'],'c':event['c'],'v':event['v'],'t':event['t'],'d':event['d'],'et':event['et'],'r':event['r']}
                    print 'here is the event'
                    print self.schedDict[name]['events'][event['h']]
                except:
                    returnStr += "Failed Adding: " + str(n) + " , "
                else:
                    returnStr += "Success Adding: " + str(n) + " , "
            
            #self.sendMsgResp(returnStr)
            print self.schedDict

            #now send back the updated data to the web
            returnJSON = self.rebuildForDevice(name)
        
        
            #fullmsg[0]['payload']['name'] = (name + "." + "sch-")
            #fullmsg[0]['payload']['value'] = returnJSON

            print fullmsg

            self.sendtodb('sch-', returnJSON, name)


        elif channel == "sch-del":
            returnStr = ""

            print "deleting an event with the ID"
            #in this case the value will be a list of hahses that will be deleted
            
            values = value
            print values
            
            name = ""
            for name in self.schedDict:
                for val in values:
                    try:
                        n = self.schedDict[name]['events'][val]['n']
                    except:
                        continue
                    try:
                        del self.schedDict[name]['events'][val]
                    except:
                        returnStr += "Failed Deteting: " + str(n) + " , "
                    else:
                        returnStr += "Success Deteting: " + str(n) + " , "

                #self.sendMsgResp(returnStr)
                #now send back the updated data to the web
                returnJSON = self.rebuildForDevice(name)
        
        
            #fullmsg[0]['payload']['name'] = (name + "." + "sch-")
            #fullmsg[0]['payload']['value'] = returnJSON

            print fullmsg

            self.sendtodb('sch-', returnJSON, name)


        elif channel == "sch-sync":
            #self.sendMsgResp("Schedule Synced", msgId)
            self.initilizeAll()


        #update persistant dictionary 
        #pickle.dump( self.schedDict, open( (rootPath + "schJSON.p"), "wb" ) )
        try:
            f = open((rootPath + "schJSON.p"),'r')
        except:
            f = open((rootPath2 + "schJSON.p"),'r')
        f.write(json.dumps(self.schedDict))
        f.close()

        

        
        
        #thread.start_new_thread(self.sets, (j,))

        







    def sendMsgResp(self, val):
        pass
        #self.mc.setProperty("log", val)


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
                            'tn':self.schedDict[name]['events'][event]['tn'],
                            'r':self.schedDict[name]['events'][event]['r'],
                            'et':self.schedDict[name]['events'][event]['et'],
                            })
        data = str(json.dumps(newJSON))
        print "here is the device JSON"
        print data
        return data

        
    def initilizeAll(self):
        try:
            #check the schedule.json file for anything added to the schedule
            #this file is only giving me new data
            

            #here I want to send all of the current schedules for all devices on startup, this could use a lot of data maybe
            print "updating everything on startup"
            for name in self.schedDict:
                #mac = self.schedDict[name]['mac']
                #company = self.schedDict[name]['company']
                name = self.schedDict[name]['name']
                msg = self.rebuildForDevice(name)
                self.sendtodb('sch-', msg, name)
                upld = self.mc.myCore.get_service("presentation_manager")
                upload = upld.driver_get("Uploader")
                upload.upload_data()

        except:
            pass
    
    def getTimes(self, start, end, inc):

        myList = []
        currentTime = 0
        myList.append(start)

        if inc == 0 or inc == None or inc == "0":
            inc = None

        if inc is not None:
            #hInc = hour increment
            #mInc = minute increment
            if inc.endswith("m"):
                inc = inc[:-1]
                mInc = int(inc)
                hInc = 0
            elif inc.endswith("h"):
                mInc = 0 
                inc = inc[:-1]
                hInc = int(inc)

            while currentTime <= int(end.replace(":", "")):
                sH = int(start.split(":")[0])
                sM = int(start.split(":")[1])


                sH += hInc
                sM += mInc

                if sM > 59:
                    hours, minutes = divmod(sM, 60)
                    sM = minutes
                    sH += hours

                #new time
                if sM < 10:
                    sM = "0" + str(sM)
                else:
                    sM = str(sM)

                
                sH = str(sH)

                newTime = sH + ":" + sM


    

                newTime = sH + ":" + sM

                currentTime = int(newTime.replace(":", ""))
                start = newTime
                #print "new time:"
                #print currentTime
                if currentTime <= int(end.replace(":", "")):
                    #the time fits in the window, so add it!!
                    myList.append(newTime)


        return myList


class UTC(tzinfo):
    """UTC"""
    def utcoffset(self, dt):
        return ZERO
    def tzname(self, dt):
        return "UTC"
    def dst(self, dt):
        return ZERO

utc = UTC()