import time
import os
try:
    import json
except:
    import simplejson as json
import thread
import threading
#import requests
import httplib, mimetypes, mimetools, urllib2, cookielib


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
        self.finished = threading.Event()
        self.mcu = mcu
        self.version = "6"
        self.status = "idle"
        threading.Thread.start(self)

    def stop (self):
        self.finished.set()
        self.join()

    def register(self):
        self.sendtodb('version', self.version, 0)

    def sendtodb(self, channel, value, timestamp):
        if int(timestamp) == 0:
            timestamp = self.getTime()
        
        try:
            topic = 'meshify/db/%s/%s/%s/%s' % (self.company, self.mac, self.deviceName, channel)
            print topic
            if channel == "video":
                #for the file structure I had to take off the " " around the value
                msg = """[ { "value":%s, "timestamp":"%s" } ]""" % (str(value), str(timestamp))
            else:
                msg = """[ { "value":"%s", "timestamp":"%s" } ]""" % (str(value), str(timestamp))
            print msg
            self.q.put([topic, msg, 0])
        except:
            print "didn't work to send up MQTT data"

    def run(self):
        time.sleep(5)
        
        self.sendtodb("status", "idle", 0)
        self.sendtodb("version", self.version, 0)
        
        while True:
            try:
                self.uploadFiles()
            except Exception,e:
                    print e
            time.sleep(20)
        
    def uploadFiles(self):
        
        for filename in os.listdir("/root/videos"):
            if filename.endswith(".mp4"):
                print filename, " Is about to upload"
                if self.status == "idle":
                    self.status = "motion triggered"
                thread.start_new_thread(self.updateThread, (self.status, ))
                try:
                    filename = str(filename)
                    data = [['api_password', 'e07e24bfd2e22e2a3702bfd8522b9242af406db8']]
                    lst = [['file', ("/root/videos/" + filename), open("/root/videos/" + filename,'rb').read()]]
                    #lst = [{'file': open("/Users/lewiswight/Desktop/" + filename,'rb') }]
                    #lst = []
                    #lst.append(("/Users/lewiswight/Desktop/" + filename))
                    r = post_multipart("https://upload.wistia.com", '', data, lst)
                    print r
                    value = r
                    self.sendtodb("video", value, 0)
                    os.remove("/root/videos/" + filename)
                except Exception,e:
                    print e

    def updateThread(self, status):
        self.sendtodb("status", status, 0)
        self.status = "idle"
        time.sleep(30)
        self.sendtodb("status", "idle", 0)
        

    def cam_action(self, name, value):
        #self.mcu.digitalOut3(str(1))
        self.status = "web triggered"
        os.system("/bin/echo 0 > /sys/devices/platform/mtcdp/dout1")
        time.sleep(5)
        os.system("/bin/echo 1 > /sys/devices/platform/mtcdp/dout1")
        #self.mcu.digitalOut3(str(0))
        self.sendtodb(name, value, 0)
        return True
    
    def getTime(self):
        return str(int(time.time() + int(self.offset)))


cj = cookielib.CookieJar()
opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
urllib2.install_opener(opener)

def post_multipart(host, selector, fields, files):
    """
        Post fields and files to an http host as multipart/form-data.
        fields is a sequence of (name, value) elements for regular form fields.
        files is a sequence of (name, filename, value) elements for data to be uploaded as files
        Return the server's response page.
        """
    content_type, body = encode_multipart_formdata(fields, files)
    headers = {'Content-Type': content_type,
        'Content-Length': str(len(body))}
    print("http://%s%s" % (host, selector))
    r = urllib2.Request("%s%s" % (host, selector), body, headers)
    return urllib2.urlopen(r).read()

def encode_multipart_formdata(fields, files):
    """
        fields is a sequence of (name, value) elements for regular form fields.
        files is a sequence of (name, filename, value) elements for data to be uploaded as files
        Return (content_type, body) ready for httplib.HTTP instance
        """
    BOUNDARY = mimetools.choose_boundary()
    CRLF = '\r\n'
    L = []
    for (key, value) in fields:
        L.append('--' + BOUNDARY)
        L.append('Content-Disposition: form-data; name="%s"' % key)
        L.append('')
        L.append(value)
    for (key, filename, value) in files:
        L.append('--' + BOUNDARY)
        L.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (key, filename))
        L.append('Content-Type: %s' % get_content_type(filename))
        L.append('')
        L.append(value)
    L.append('--' + BOUNDARY + '--')
    L.append('')
    body = CRLF.join(L)
    content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
    return content_type, body

def get_content_type(filename):
    return mimetypes.guess_type(filename)[0] or 'application/octet-stream'
