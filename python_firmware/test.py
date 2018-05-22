import core
import time
import pickle


try:
    version = pickle.load( open( "coreVersion.p", "rb" ) )
    version = int(version)
    print version
except:
    version = 0
    print "couldn't load version from pickle"



try:
    json_data=open('deviceList.txt')
    data = json.load(json_data)
    url = data["core"]
    print url
    
    #build a list of urls for your device driver buckets 
    for i in data:
        print i
        if i != "core":
            self.deviceUrlList.append(data[i])
            print i
            print data[i]
        
    pickle.dump( self.deviceUrlList, open( "deviceUrls.p", "wb" ) )
except:
