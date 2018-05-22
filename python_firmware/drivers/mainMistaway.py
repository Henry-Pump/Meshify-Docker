import time
import os
try:
    import json
except:
    import simplejson as json
import thread
import threading




class start(threading.Thread):

    def __init__(self, name=None, number=None, mac=None, Q=None, mcu=None, companyId=None, offset=None, mqtt=None, Nodes=None):
        threading.Thread.__init__(self)
        self.daemon = True
        self.offset = offset
        self.company = companyId
        self.name = name
        self.number = number
        self.q = Q
        self.deviceName = name + '_[' + mac +  ':' + number[0:2] + ':' + number[2:] + ']!'
        print 'device name is:'
        print self.deviceName
        mac2 = mac.replace(":", "")
        self.mac = mac2.upper()
        self.version = "8" #added Nodes in v5
        self.finished = threading.Event()
        
        threading.Thread.start(self)



    #this is a required function for all drivers, its goal is to upload some piece of data
    #about your device so it can be seen on the web
    def register(self):
        #self.mainMistaway_hb('hb', 'On')
        self.sendtodb("connected", "True", 0)

    def stop (self):
        self.finished.set()
        self.join()

    def sendtodb(self, channel, value, timestamp):
        if int(timestamp) == 0:
            timestamp = self.getTime()
            if timestamp < 1400499858:
                return
        
        try:
            topic = 'meshify/db/%s/%s/%s/%s' % (self.company, self.mac, self.deviceName, channel)
            print topic
            if channel == "files":
                #for the file structure I had to take off the " " around the value
                msg = """[ { "value":%s, "timestamp":"%s" } ]""" % (str(value), str(timestamp))
            else:
                msg = """[ { "value":"%s", "timestamp":"%s" } ]""" % (str(value), str(timestamp))
            print msg
            self.q.put([topic, msg, 0])
        except:
            print "didn't work to send up MQTT data"

    def run(self):
        #on startup send the version number
        self.sendtodb("version", str(self.version), 0)
        while True:
            try:
                self.mainMistaway_hb('hb', 'On')
                self.sendtodb("connected", "True", 0)
                time.sleep(3600 * 4)
            except Exception, e:
                print e
                
    def mainMistaway_files(self, name, value):
        name = 'files'

        

        
        
        dict = {}
        for dirname, dirnames, filenames in os.walk(str(value)):
            # print path to all subdirectories first.
            
            
            print "##########################################"
            print "new directory: " + dirname
            print "##########################################"
            # print path to all filenames.
            tempDictParent = {}
            for filename in filenames:
                tempDict = {}
                filepath = os.path.join(dirname, filename)
                try:
                    fileMem = os.stat(filepath).st_size
                    fileDate = os.stat(filepath).st_mtime
                except:
                    fileMem = ""
                    fileDate = ""
                print filepath, fileMem, fileDate
                tempDict["mem"] = fileMem
                tempDict["date"] = fileDate
                tempDictParent[filename] = tempDict
            
            dict[dirname] = tempDictParent

            
            # Advanced usage:
            # editing the 'dirnames' list will stop os.walk() from recursing into there.
            if '.git' in dirnames:
                # don't go into any .git directories.
                dirnames.remove('.git')

        value = json.dumps(dict)
        self.sendtodb(name, value, 0)
        return True
        

    def mainMistaway_hb(self, name, value):
        self.sendtodb(name, value, 0)
        
        
    def getTime(self):
        return str(int(time.time() + int(self.offset)))
    
