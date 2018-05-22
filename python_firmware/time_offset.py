


import urllib
import json

MAC = "00409DFF-FF53168A"

class meshifyData():
    
    def __init__(self, MAC):
        self.mac = MAC[0:6] + "FF-FF" + MAC[7:]
        #set the defaults
        self.offset = -21600
        self.dst = False
        self.companyId = "1"

    def getdata(self):
    
  



        url = "http://demo.meshify.com/api/gateway?macaddressForTimezone=" + MAC
         
        try:
            f = urllib.urlopen(url)
        except:
           print "Error opening url"
           #return the defaults 
           return self.offset, self.dst, self.companyId

        try: 
            s = f.read()
            print s
            data = json.loads(s)
            self.offset = int(data["gmt_offset"])
            self.dst = bool(int(data["dst"]))
            print bool(int("0"))
            self.companyId = data["CompanyId"]
            return self.offset, self.dst, self.companyId
        except:
            #return the defaults 
            return self.offset, self.dst, self.companyId


