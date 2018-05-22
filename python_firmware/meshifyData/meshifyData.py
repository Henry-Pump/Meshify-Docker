


import urllib
try:
    import json
except:
    import simplejson as json
import pickle

MAC = "00409D53168A"

class meshifyData():
    
    def __init__(self, MAC):
        self.mac = MAC[0:6] + "FF-FF" + MAC[6:]
        print "here is the mac: " + self.mac
        #set the defaults
        self.param_dict = {}
        
    def checkConfig(self):

        url = "http://control.meshify.com/api2/gatewayconfig/" + self.mac
         
        try:
            f = urllib.urlopen(url)
        except:
           print "Error opening url for remote config"
           #return the defaults 
           return None

        try: 
            s = f.read()
            print s
            if len(s) < 5:
                return None
            data = json.loads(s)
            #if we get there then replace the deviceList.txt
            myfile = open('/root/python_firmware/deviceList.txt', 'w')
            myfile.write(s)
            myfile.close()
            return data 
        except Exception,e:
            print e
            #return the defaults 
            return None

    def checkAPI(self):
    
          
        offset = -21600
        dst = False
        companyId = "1"


        url = "http://machines.meshify.com/api/gateway?macaddressForTimezone=" + self.mac
         
        try:
            f = urllib.urlopen(url)
        except:
           print "Error opening url"
           #return the defaults 
           return offset, dst, companyId

        try: 
            s = f.read()
            print s
            data = json.loads(s)
            offset = int(data["offset"])
            dst = bool(int(data["dst"]))
            print bool(int("0"))
            companyId = data["companyId"]
            return offset, dst, companyId
        except Exception,e:
            print e
            #return the defaults 
            return -21600, False, "1"

    def getdata(self):
        #if the API fails and the company ID of 1 is returned then you need to
        #check and see if you have pickled anything.
        #if it doesn't fail, and it gives you something other than 1
        #then you need to repickle the object
        self.offset, self.dst, self.companyId = self.checkAPI()
        if self.companyId == "1":
            try:
                self.param_dict = pickle.load( open( "params.p", "rb" ) )
            except:
                print self.offset, self.dst, self.companyId
                return self.offset, self.dst, self.companyId
            try:
                self.offset = self.param_dict["offset"]
                self.dst = self.param_dict["dst"]
                self.companyId = self.param_dict["companyId"]
            except:
                return -21600, False, "1"

            return self.offset, self.dst, self.companyId

            
        else:
            self.param_dict["offset"] = self.offset
            self.param_dict["dst"] = self.dst
            self.param_dict["companyId"] = self.companyId
            pickle.dump( self.param_dict, open( "params.p", "wb" ) )
            print self.param_dict
            print self.offset, self.dst, self.companyId
            return self.offset, self.dst, self.companyId
        


