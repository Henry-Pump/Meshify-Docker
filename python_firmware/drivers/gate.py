import types
import traceback
import binascii
import threading
import time
import thread
import os
import struct
import sys
import serial




class start():
    """\
        This class extends one of our base classes and is intended as an
        example of a concrete, example implementation, but it is not itself
        meant to be included as part of our developer API. Please consult the
        base class documentation for the API and the source code for this file
        for an example implementation.
        
        """
    
    # here are the setting defaults
    DEF_HEXDEC = True
    DEF_EOLN = None
    DEF_CHARTOUT = 2.0
    
    # a sanity value to prevent an infinite rcv_buffer creation
    DEF_MAX_READ = 1000
    
    def __init__(self, name=None, number=None, mac=None, Q=None, mcu=None, companyId=None, offset=None, mqtt=None):
       
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
        self.address = 1
	self.debug = True
	self.mcu = mcu
        self.currentDict = {}
        self.lastDict = {}
        self.version = "1"
        #success = self.mcu.relay2(1)
        #time.sleep(5)
        #success = self.mcu.relay2(0)
	
	#self.mcu.relay1(0)
	
        #self.mcu.relay2(0)
        
        #self.mcu.relay1(1)
        
        #self.mcu.relay2(1)
        self.sendtodb("version", self.version, 0)
        self.sendtodb("activate", str(0), 0)
        

    
    def sendtodb(self, channel, value, timestamp):

        if int(timestamp) == 0:
            timestamp = self.getTime()
        
        topic = 'meshify/db/%s/%s/%s/%s' % (self.company, self.mac, self.deviceName, channel)
        print topic
        msg = """[ { "value":"%s", "timestamp":"%s" } ]""" % (str(value), str(timestamp))
        print msg
        self.q.put([topic, msg, 0])
    
   
    


    
   
    
    

    # Settable channels' callbacks
    
    
    def gate_dout1(self, name, value):
        success = self.mcu.digitalOut1(str(value))
        self.sendtodb(name, str(value), 0)

        #return True/False
        return success
    
        
    def gate_dout2(self, name, value):
        success = self.mcu.digitalOut2(str(value))
        self.sendtodb(name, str(value), 0)

        #return True/False
        return success

    def gate_dout3(self, name, value):
        success = self.mcu.digitalOut3(str(value))
        self.sendtodb(name, str(value), 0)

        #return True/False
        return success
    
    def gate_dout4(self, name, value):
        success = self.mcu.digitalOut4(str(value))
        self.sendtodb(name, str(value), 0)

        #return True/False
        return success
        
    def gate_dout5(self, name, value):
        success = self.mcu.digitalOut5(str(value))
        self.sendtodb(name, str(value), 0)

        #return True/False
        return success

   
        
    def gate_relay2(self, name, value):
        value = int(value)
        success = self.mcu.relay2(value)
        self.sendtodb(name, str(value), 0)

        #return True/False
        return success


    
    def gate_relay1(self, name, value):
        value = int(value)
        success = self.mcu.relay1(value)
        self.sendtodb(name, str(value), 0)

    def gate_activate(self, name, value):
        success = self.mcu.relay2(1)
        #if success:
        #    self.sendtodb(name, str(1), 0)
        time.sleep(1)
        success = self.mcu.relay2(0)

        #return True/False
        return True
    
    # internal functions & classes
    

    def getTime(self):
        return str(int(time.time() + int(self.offset)))


    def get_eoln(self):
        eoln = SettingsBase.get_setting(self, "eoln")
        if eoln is None:
            return None
        
        if eoln != self.__eoln_save:
            # cache result to avoid repeat processing of escapes
            self.__eoln_save = eoln
            self._eoln = strip_escapes(eoln)
        return self._eoln
    
    
    
  
