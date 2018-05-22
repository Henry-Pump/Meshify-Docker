import types
import traceback
import binascii
import threading
import time
import thread
import os
import struct
import sys
import snap7
import copy
import re
import string

DataBases = 32



class start(threading.Thread):
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
    
    def __init__(self, name=None, number=None, mac=None, Q=None, mcu=None, companyId=None, offset=None, mqtt=None, Nodes=None):
        threading.Thread.__init__(self)
        self.daemon = True
        self.offset = offset
        self.company = companyId
        self.name = name
        self.number = number 
        self.q = Q
        self.deviceName = name + '_[' + mac +  ':' + number[0:2] + ':' + number[2:] + ']!'
        self.chName = "mcogen" + '_[' + mac + ':'
        self.chNameDevice = '_[' + mac + ':'
        print 'device name is:'
        print self.deviceName
        mac2 = mac.replace(":", "")
        self.mac = mac2.upper()
        self.address = 1
        self.debug = True
        self.mcu = mcu
        self.firstRun = True
        self.version = "17"
        self.mqtt = mqtt
        self.nodes = Nodes
        self.registerRepeat = False
        
        #local dictionary of derived nodes ex: localNodes[tank_0199] = self
        self.localNodes = {}

        self.lock = threading.Lock()

        self.client = snap7.client.Client() 



        try:
            os.system("ntpdate pool.ntp.org")
        except:
            pass

        

        



        

        #bitArrays:

       
        #mappings
        self.bitMap = {
            0:"Off",
            1:"On"
            }

        self.measurementTypeMap = {
            0:"None",
            1:"Level",
            2:"Pressure",
            3:"Flow In",
            4:"Flow Out(Water)",
            5:"Flow Out(Oil)",
            6:"Flow Out(Gas)",
            7:"Temperature",
            8:"Discharge Pressure",
            9:"Suction Pressure",
            10:"Tubing Pressure",
            11:"Casing Pressure",
            12:"RPM",
            13:"Level with Control",
            14:"Interface Level",
            15:"Hi Switch",
            16:"Lo Switch"
            }


        self.typeMap = {
            0:"",
            1:"tank",
            2:"sep",
            3:"htr",
            4:"LACT",
            5:"wlhd",
            6:"scrbr",
            7:"comp",
            8: "VRU"
            }

        self.register()

        self.finished = threading.Event()
        threading.Thread.start(self)

    def oneRegisterPerMinute(self):
        time.sleep(60)
        self.registerRepeat = False
        pass
        
    #this is a required function for all drivers, its goal is to upload some piece of data
    #about your device so it can be seen on the web
    def register(self):
        if self.registerRepeat == False:
            self.registerRepeat = True
            thread.start_new_thread(self.oneRegisterPerMinute, ())
            with self.lock:

                #range is a validatoin range
                self.sendtodb("connected", "True", 0)
                block = {
                
                    "type": {"start":0, "length":2, "type":"int", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.typeMap, "range":None},
                    "dname": {"start":4, "length":20,  "type":"str", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":None, "range":None},
                
                    #analog 1 block
                    "a1-type": {"start":(24 + 0), "length":2,  "type":"int", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.measurementTypeMap, "range":None},
                    "a1-proval": {"start":(24 + 2), "length":4,  "type":"real", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":None, "range":None},
                    "a1-upspn": {"start":(24 + 6), "length":4,  "type":"real", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":None, "range":None},
                    "a1-shih": {"start":(24 + 10), "length":4,  "type":"real", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":None, "range":None},
                    "a1-shi": {"start":(24 + 14), "length":4,  "type":"real", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":None, "range":None},
                    "a1-slo": {"start":(24 + 18), "length":4,  "type":"real", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":None, "range":None},
                    "a1-slol": {"start":(24 + 22), "length":4,  "type":"real", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":None, "range":None},
                    "a1-ahih": {"start":(24 + 26), "length":1,  "type":"bit", "possition":0, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "a1-ahi": {"start":(24 + 26), "length":1,  "type":"bit", "possition":1, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "a1-alo": {"start":(24 + 26), "length":1,  "type":"bit", "possition":2, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "a1-alol": {"start":(24 + 26), "length":1,  "type":"bit", "possition":3, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "a1-wrbr": {"start":(24 + 26), "length":1,  "type":"bit", "possition":4, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "a1-config": {"start":(24 + 26), "length":1,  "type":"bit", "possition":5, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "a1-mdbs": {"start":(24 + 26), "length":1,  "type":"bit", "possition":6, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "a1-stmt": {"start":(24 + 26), "length":1,  "type":"bit", "possition":7, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "a1-term": {"start":(24 + 27), "length":1,  "type":"int", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":None, "range":None},
                
                    #analog 2 block
                    "a2-type": {"start":(52 + 0), "length":2,  "type":"int", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.measurementTypeMap, "range":None},
                    "a2-proval": {"start":(52 + 2), "length":4,  "type":"real", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":None, "range":None},
                    "a2-upspn": {"start":(52 + 6), "length":4,  "type":"real", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":None, "range":None},
                    "a2-shih": {"start":(52 + 10), "length":4,  "type":"real", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":None, "range":None},
                    "a2-shi": {"start":(52 + 14), "length":4,  "type":"real", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":None, "range":None},
                    "a2-slo": {"start":(52 + 18), "length":4,  "type":"real", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":None, "range":None},
                    "a2-slol": {"start":(52 + 22), "length":4,  "type":"real", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":None, "range":None},
                    "a2-ahih": {"start":(52 + 26), "length":1,  "type":"bit", "possition":0, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "a2-ahi": {"start":(52 + 26), "length":1,  "type":"bit", "possition":1, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "a2-alo": {"start":(52 + 26), "length":1,  "type":"bit", "possition":2, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "a2-alol": {"start":(52 + 26), "length":1,  "type":"bit", "possition":3, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "a2-wrbr": {"start":(52 + 26), "length":1,  "type":"bit", "possition":4, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "a2-config": {"start":(52 + 26), "length":1,  "type":"bit", "possition":5, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "a2-mdbs": {"start":(52 + 26), "length":1,  "type":"bit", "possition":6, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "a2-stmt": {"start":(52 + 26), "length":1,  "type":"bit", "possition":7, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "a2-term": {"start":(52 + 27), "length":1,  "type":"int", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":None, "range":None},
                

                    #analog 3 block
                    "a3-type": {"start":(80 + 0), "length":2,  "type":"int", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.measurementTypeMap, "range":None},
                    "a3-proval": {"start":(80 + 2), "length":4,  "type":"real", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":None, "range":None},
                    "a3-upspn": {"start":(80 + 6), "length":4,  "type":"real", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":None, "range":None},
                    "a3-shih": {"start":(80 + 10), "length":4,  "type":"real", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":None, "range":None},
                    "a3-shi": {"start":(80 + 14), "length":4,  "type":"real", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":None, "range":None},
                    "a3-slo": {"start":(80 + 18), "length":4,  "type":"real", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":None, "range":None},
                    "a3-slol": {"start":(80 + 22), "length":4,  "type":"real", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":None, "range":None},
                    "a3-ahih": {"start":(80 + 26), "length":1,  "type":"bit", "possition":0, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "a3-ahi": {"start":(80 + 26), "length":1,  "type":"bit", "possition":1, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "a3-alo": {"start":(80 + 26), "length":1,  "type":"bit", "possition":2, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "a3-alol": {"start":(80 + 26), "length":1,  "type":"bit", "possition":3, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "a3-wrbr": {"start":(80 + 26), "length":1,  "type":"bit", "possition":4, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "a3-config": {"start":(80 + 26), "length":1,  "type":"bit", "possition":5, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "a3-mdbs": {"start":(80 + 26), "length":1,  "type":"bit", "possition":6, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "a3-stmt": {"start":(80 + 26), "length":1,  "type":"bit", "possition":7, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "a3-term": {"start":(80 + 27), "length":1,  "type":"int", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":None, "range":None},
                

                    #analog 4 block
                    "a4-type": {"start":(108 + 0), "length":2,  "type":"int", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.measurementTypeMap, "range":None},
                    "a4-proval": {"start":(108 + 2), "length":4,  "type":"real", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":None, "range":None},
                    "a4-upspn": {"start":(108 + 6), "length":4,  "type":"real", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":None, "range":None},
                    "a4-shih": {"start":(108 + 10), "length":4,  "type":"real", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":None, "range":None},
                    "a4-shi": {"start":(108 + 14), "length":4,  "type":"real", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":None, "range":None},
                    "a4-slo": {"start":(108 + 18), "length":4,  "type":"real", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":None, "range":None},
                    "a4-slol": {"start":(108 + 22), "length":4,  "type":"real", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":None, "range":None},
                    "a4-ahih": {"start":(108 + 26), "length":1,  "type":"bit", "possition":0, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "a4-ahi": {"start":(108 + 26), "length":1,  "type":"bit", "possition":1, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "a4-alo": {"start":(108 + 26), "length":1,  "type":"bit", "possition":2, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "a4-alol": {"start":(108 + 26), "length":1,  "type":"bit", "possition":3, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "a4-wrbr": {"start":(108 + 26), "length":1,  "type":"bit", "possition":4, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "a4-config": {"start":(108 + 26), "length":1,  "type":"bit", "possition":5, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "a4-mdbs": {"start":(108 + 26), "length":1,  "type":"bit", "possition":6, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "a4-stmt": {"start":(108 + 26), "length":1,  "type":"bit", "possition":7, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "a4-term": {"start":(108 + 27), "length":1,  "type":"int", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":None, "range":None},
                

                    #analog 5 block
                    "a5-type": {"start":(136 + 0), "length":2,  "type":"int", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.measurementTypeMap, "range":None},
                    "a5-proval": {"start":(136 + 2), "length":4,  "type":"real", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":None, "range":None},
                    "a5-upspn": {"start":(136 + 6), "length":4,  "type":"real", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":None, "range":None},
                    "a5-shih": {"start":(136 + 10), "length":4,  "type":"real", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":None, "range":None},
                    "a5-shi": {"start":(136 + 14), "length":4,  "type":"real", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":None, "range":None},
                    "a5-slo": {"start":(136 + 18), "length":4,  "type":"real", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":None, "range":None},
                    "a5-slol": {"start":(136 + 22), "length":4,  "type":"real", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":None, "range":None},
                    "a5-ahih": {"start":(136 + 26), "length":1,  "type":"bit", "possition":0, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "a5-ahi": {"start":(136 + 26), "length":1,  "type":"bit", "possition":1, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "a5-alo": {"start":(136 + 26), "length":1,  "type":"bit", "possition":2, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "a5-alol": {"start":(136 + 26), "length":1,  "type":"bit", "possition":3, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "a5-wrbr": {"start":(136 + 26), "length":1,  "type":"bit", "possition":4, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "a5-config": {"start":(136 + 26), "length":1,  "type":"bit", "possition":5, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "a5-mdbs": {"start":(136 + 26), "length":1,  "type":"bit", "possition":6, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "a5-stmt": {"start":(136 + 26), "length":1,  "type":"bit", "possition":7, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "a5-term": {"start":(136 + 27), "length":1,  "type":"int", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":None, "range":None},
                
                    #digital 1 block
                    "d1-proval": {"start":(164 + 0), "length":1,  "type":"bit", "possition":0, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "d1-config": {"start":(164 + 0), "length":1,  "type":"bit", "possition":1, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "d1-NCcon": {"start":(164 + 0), "length":1,  "type":"bit", "possition":2, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "d1-s1": {"start":(164 + 0), "length":1,  "type":"bit", "possition":3, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "d1-s2": {"start":(164 + 0), "length":1,  "type":"bit", "possition":4, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "d1-s3": {"start":(164 + 0), "length":1,  "type":"bit", "possition":5, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "d1-s4": {"start":(164 + 0), "length":1,  "type":"bit", "possition":6, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "d1-s5": {"start":(164 + 0), "length":1,  "type":"bit", "possition":7, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "d1-term": {"start":(164 + 1), "length":1,  "type":"int", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":None, "range":None},
                
                    #digital 2 block
                    "d2-proval": {"start":(166 + 0), "length":1,  "type":"bit", "possition":0, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "d2-config": {"start":(166 + 0), "length":1,  "type":"bit", "possition":1, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "d2-NCcon": {"start":(166 + 0), "length":1,  "type":"bit", "possition":2, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "d2-s1": {"start":(166 + 0), "length":1,  "type":"bit", "possition":3, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "d2-s2": {"start":(166 + 0), "length":1,  "type":"bit", "possition":4, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "d2-s3": {"start":(166 + 0), "length":1,  "type":"bit", "possition":5, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "d2-s4": {"start":(166 + 0), "length":1,  "type":"bit", "possition":6, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "d2-s5": {"start":(166 + 0), "length":1,  "type":"bit", "possition":7, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "d2-term": {"start":(166 + 1), "length":1,  "type":"int", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":None, "range":None},
                
                    #digital 3 block
                    "d3-proval": {"start":(168 + 0), "length":1,  "type":"bit", "possition":0, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "d3-config": {"start":(168 + 0), "length":1,  "type":"bit", "possition":1, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "d3-NCcon": {"start":(168 + 0), "length":1,  "type":"bit", "possition":2, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "d3-s1": {"start":(168 + 0), "length":1,  "type":"bit", "possition":3, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "d3-s2": {"start":(168 + 0), "length":1,  "type":"bit", "possition":4, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "d3-s3": {"start":(168 + 0), "length":1,  "type":"bit", "possition":5, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "d3-s4": {"start":(168 + 0), "length":1,  "type":"bit", "possition":6, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "d3-s5": {"start":(168 + 0), "length":1,  "type":"bit", "possition":7, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "d3-term": {"start":(168 + 1), "length":1,  "type":"int", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":None, "range":None},
                
                    #digital 4 block
                    "d4-proval": {"start":(170 + 0), "length":1,  "type":"bit", "possition":0, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "d4-config": {"start":(170 + 0), "length":1,  "type":"bit", "possition":1, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "d4-NCcon": {"start":(170 + 0), "length":1,  "type":"bit", "possition":2, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "d4-s1": {"start":(170 + 0), "length":1,  "type":"bit", "possition":3, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "d4-s2": {"start":(170 + 0), "length":1,  "type":"bit", "possition":4, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "d4-s3": {"start":(170 + 0), "length":1,  "type":"bit", "possition":5, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "d4-s4": {"start":(170 + 0), "length":1,  "type":"bit", "possition":6, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "d4-s5": {"start":(170 + 0), "length":1,  "type":"bit", "possition":7, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "d4-term": {"start":(170 + 1), "length":1,  "type":"int", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":None, "range":None},
                
                    #digital 5 block
                    "d5-proval": {"start":(172 + 0), "length":1,  "type":"bit", "possition":0, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "d5-config": {"start":(172 + 0), "length":1,  "type":"bit", "possition":1, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "d5-NCcon": {"start":(172 + 0), "length":1,  "type":"bit", "possition":2, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "d5-s1": {"start":(172 + 0), "length":1,  "type":"bit", "possition":3, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "d5-s2": {"start":(172 + 0), "length":1,  "type":"bit", "possition":4, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "d5-s3": {"start":(172 + 0), "length":1,  "type":"bit", "possition":5, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "d5-s4": {"start":(172 + 0), "length":1,  "type":"bit", "possition":6, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "d5-s5": {"start":(172 + 0), "length":1,  "type":"bit", "possition":7, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
                    "d5-term": {"start":(172 + 1), "length":1,  "type":"int", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":None, "range":None},
                

                    "devNumber": {"start":176, "length":2, "type":"int", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":None, "range":None}
                
                    }

           
                self.mainList = {}
                for i in range(1, (DataBases + 1)):
                    self.mainList[i] = copy.deepcopy(block)

                #self.count = 3001

    def stop (self):
        self.finished.set()
        self.join()
    
    def sendtodbCH(self, ch, channel, value, timestamp):

        value = value.replace('?', '')

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
    

    def sendtodbDevice(self, channel, value, timestamp, deviceName, ch):

        value = value.replace('?', '')

        if int(ch) < 10:
            ch = "0" + str(ch)

        #this will add your derived nodes the master nodes list, allowing them to receive sets!!
        localNodesName = deviceName + "_" + str(ch) + "99"

        if not self.localNodes.has_key(localNodesName):
            self.localNodes[localNodesName] = True
            self.nodes[localNodesName] = self
            self.nodes["tank_0199"] = self
            #for testing
            


        

        newName = deviceName + self.chNameDevice + str(ch) + ":99]!"

        if int(timestamp) == 0:
            timestamp = self.getTime()
            if timestamp < 1400499858:
                return
        
        topic = 'meshify/db/%s/%s/%s/%s' % (self.company, self.mac, newName, channel)
        print topic
        msg = """[ { "value":"%s", "timestamp":"%s" } ]""" % (str(value), str(timestamp))
        print msg
        self.q.put([topic, msg, 0])

        #small pause to keep us save
        time.sleep(.25)


    def sendtodb(self, channel, value, timestamp):

        value = value.replace('?', '')

        if int(timestamp) == 0:
            timestamp = self.getTime()
            if timestamp < 1400499858:
                return
        
        topic = 'meshify/db/%s/%s/%s/%s' % (self.company, self.mac, self.deviceName, channel)
        print topic
        msg = """[ { "value":"%s", "timestamp":"%s" } ]""" % (str(value), str(timestamp))
        print msg
        self.q.put([topic, msg, 0])
    
    def start(self):
        
        
        
        # you could add other ddo settings here
        thread.start_new_thread(self.loop, ())
        
    
    
    # def stop(): uses XBeeSerial.stop()
    
    
    ## Locally defined functions:



    def run(self):

        
        print self.mainList
        #on startup send the version number
        self.sendtodb("version", str(self.version), 0)
        self.sendtodb("log", "system start up", 0)

        connected = False

        while not connected:
            try:
                self.client.connect('192.168.0.1', 0, 1, 102)
                connected = True
                break
            except:
                try:
                    self.client.connect('192.168.1.3', 0, 1, 102)
                    #self.client.disconnect()
                    connected = True
                    break
                except:
                    time.sleep(5)
       
        self.count = 3001
        hb_count = 0
        while not self.finished.isSet():
            self.count += 1
            
                
            try:
               
                print "################################"
                print "#############sending data ######"
               
                try:
                    area = 0x84
                    for i in range(1, DataBases + 1):
                        try:
                            with self.lock:
                                db = self.client.read_area(area, i, 0, 196) 
                                self.processData(self.mainList[i], i, db)
                        except:
                            try:
                                self.lock.release()
                            except:
                                pass
                            time.sleep(3)
                            continue



                    

                    

                    
                except Exception,e: 
                    time.sleep(10)
                    print(str(e))
                    self.sendtodb("error", str(e), 0)

                

                
                
                if self.count > 3000:
                    self.count = 0
                    try:
                        pass
                    except:
                        pass
            except Exception,e: print(str(e))
    
    
   
    
            
    
    
    
    
    
    
    
    

    
    
    # internal functions & classes

    def processData(self, s7Dict, dbNumber, db):
        #"d1-s5": {"start":(164 + 0), "length":1,  "type":"bit", "possition":7, "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":self.bitMap, "range":None},
        #"d1-term": {"start":(164 + 1), "length":1,  "type":"int", "last_val":"", "multiplier":None, "multiplierVal": "1", "changeType":"number", "change":1 , "valueMap":None, "range":None},
        
        #first grab the device name:
        chName = 'type'

        start = s7Dict[chName]['start']
        length = s7Dict[chName]['length']
        type = s7Dict[chName]['type']
        last_val = s7Dict[chName]['last_val']
        multiplier = s7Dict[chName]['multiplier']
        multiplierVal = s7Dict[chName]['multiplierVal']
        changeType = s7Dict[chName]['changeType']
        change = s7Dict[chName]['change']
        valueMap = s7Dict[chName]['valueMap']
        range = s7Dict[chName]['range']
        
        val = db[int(start):(int(start)+int(length))]
        val = self.int16(val)
        if int(val) == 0:
            print "No device set up on this channel: " + str(dbNumber)
            return
        val =  self.typeMap[int(val)]

        deviceName = val
        
        for chName in s7Dict:

            try:
            
                start = s7Dict[chName]['start']
                length = s7Dict[chName]['length']
                type = s7Dict[chName]['type']
                last_val = s7Dict[chName]['last_val']
                multiplier = s7Dict[chName]['multiplier']
                multiplierVal = s7Dict[chName]['multiplierVal']
                changeType = s7Dict[chName]['changeType']
                change = s7Dict[chName]['change']
                valueMap = s7Dict[chName]['valueMap']
                range = s7Dict[chName]['range']

            

                #possible types: bit, int, real, str
                #first check if its a string
                #then check if its a bit

                if type == 'str':
                    val = db[int(start):(int(start)+int(length))]
                    val = self.hex2str(val)
                    #check to see if its changed:
                    if val != last_val:
                        #it changed:
                        self.sendtodbDevice(chName, str( filter(lambda x: x in string.printable, str(val))  ), 0, deviceName, dbNumber)
                        #update the master info, and return
                        self.mainList[dbNumber][chName]['last_val'] = val
                        print "%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%"
                        print "here are the values"
                        print "chname, last val, val, dbnumber"
                        print chName, last_val, val, dbNumber
                    continue

                #check if its a bit

                if type == 'bit':
                    possition = s7Dict[chName]['possition']
                    val = self.bitArray(db[int(start)], valueMap, int(possition))
                    if val != last_val:
                        #it changed:
                        self.sendtodbDevice(chName, str(val), 0, deviceName, dbNumber)
                        #update the master info, and return
                        self.mainList[dbNumber][chName]['last_val'] = val
                        print "%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%"
                        print "here are the values"
                        print "chname, last val, val, dbnumber"
                        print chName, last_val, val, dbNumber
                    continue

            
                if type == 'real':
                    val = db[int(start):(int(start)+int(length))]
                    val = self.float32(val)
                elif type == 'int':
                    val = db[int(start):(int(start)+int(length))]
                    val = self.int32(val)
                else:
                    print "no type was a match! " + str(type)
                    continue

                try:
                    if range is not None:
                        high = range.split("-")[1]
                        low = range.split("-")[0]
                except:
                    range = None

            



                #check if there is a multiplier
                if multiplier != None:
                    if multiplier == "divide":
                        val = round(float((float(val) / float(multiplierVal))), 2)
                    elif multiplier == "multiply":
                        val = round(float((float(val) * float(multiplierVal))), 2)

                #check and see if we have a range, if its outside the range then just ignore the data and continue
                if range != None:
                    #validate the value is in the range
                    try:
                        if float(val) > float(high) or float(val) < float(low):
                            continue
                    except:
                        print "validation error, skipping value"
                        continue


                #check if the data has changed
                if changeType == "number":
                    #compare last value with a change amount to see if we have enough change to send it
                    #first see if you have an empty string as the last value, if so its the first time and we don't need to compare, but just send the value
                    if str(last_val) == "":
                        if val != last_val:
                            if valueMap != None:
                                self.sendtodbDevice(chName, str(valueMap[val]), 0, deviceName, dbNumber)
                            else:
                                self.sendtodbDevice(chName, str(val), 0, deviceName, dbNumber)
                            self.mainList[dbNumber][chName]['last_val'] = val
                            print "%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%"
                            print "here are the values"
                            print "chname, last val, val, dbnumber"
                            print chName, last_val, val, dbNumber
                            continue
                    elif abs(float(last_val) - float(val)) > change:
                        if valueMap != None:
                            self.sendtodbDevice(chName, str(valueMap[val]), 0, deviceName, dbNumber)
                        else:
                            self.sendtodbDevice(chName, str(val), 0, deviceName, dbNumber)
                        self.mainList[dbNumber][chName]['last_val'] = val
                        print "%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%"
                        print "here are the values"
                        print "chname, last val, val, dbnumber"
                        print chName, last_val, val, dbNumber
            except Exception,e:
                self.sendtodb('error-channel', (str(e) + " " + chName), 0)
                time.sleep(20)
                print e

    
    
       
    def genericSet(self, name, value, id):
        #a1-shih 67 01
        #this is a generic set function, if you don't specify a specific set, it will come here
        print "generic set found"
        print name, value, id
        if name == "sync":
            self.register()
            self.count = 3001
            return True

        print "getting the values"
        start = int(self.mainList[int(id)][str(name)]['start'])
        length = int(self.mainList[int(id)][str(name)]['length'])
        type = self.mainList[int(id)][str(name)]['type']
        
        print id, start, length, type

        if type == "int" and length == 2 and name.split('-')[1] == 'type':
            with self.lock:
                newName = name.split('-')[0] + '-config'
                nstart = int(self.mainList[int(id)][str(newName)]['start'])

                self.client.write_area(0x84, int(id), nstart, bytearray([int(32)]))
        

        if type == "int" and length == 2:
            with self.lock:

                self.client.write_area(0x84, int(id), start, bytearray([int(value)]))
            return True

        if name == "dname":
            wordLen = len(value)
            with self.lock:
                time.sleep(1)
                self.client.write_area(0x84, int(id), 2, bytearray([0, wordLen]))
                self.client.write_area(0x84, int(id), 4, bytearray(str(value)))
                return True


        if type == "real":
            l = re.findall('..',hex(struct.unpack('<I', struct.pack('<f', float(value)))[0]).replace('0x',''))
            byteList = []
            for i in l:
                byteList.append(int(i, 16))
            BA = bytearray(byteList)
            with self.lock:
                time.sleep(1)
                self.client.write_area(0x84, int(id), start, BA)
                return True
        try:
            self.lock.release()
        except:
            pass

                    
    def awc_sync(self, name, value):
        self.register()
        self.count = 3001
        return True
            
    def hex2str(self, x):
        try:
        #x is a bytearray
            return binascii.a2b_hex(''.join(format(val, '02x') for val in x))
        except Exception,e:
            print e

    def int16(self, x):
        #x is a bytearray
        try:
            return int(''.join(format(val, '02x') for val in x), 16)
        except Exception,e:
                print "you are at 1"
                print e

    def int32(self, x):
        try:
            return int(''.join(format(val, '02x') for val in x), 16)
        except Exception,e:
            print "you are at 2"
            print e
    def float32(self, x):
        try:
        #this takes in a 4 byte bytearray and makes it into a signed 32bit float 
            return struct.unpack('!f', ''.join(format(val, '02x') for val in x).decode('hex'))[0]
        except Exception,e:
            print "you are at 3"
            self.sendtodb('error-float32', str(e), 0)
            print e
    
    def int32signed(self, x):
        try:
            if x>0xFFFFFFFF:
                raise OverflowError
            if x>0x7FFFFFFF:
                x=int(0x100000000-x)
                if x<2147483648:
                    return -x
                else:
                    return -2147483648
            return x
        except Exception,e:
            print "you are at 4"
            print e
    
    def bitArray(self, val, valMap, possition):
        #val is a 1 byte string
        #only support 8bits
        
        val = ''.join(format(val, '02x'))
        val = str(val)
        bitStr = bin(int(val, base=16)).replace('0b', '')[::-1]
        while len(bitStr) < 8:
            bitStr =  bitStr + "0"
        print bitStr
        val = valMap[int(bitStr[int(possition)])]
        print val
        return val
        
            
        
    def getTime(self):
        return str(int(time.time() + int(self.offset)))
   
def convert(int_value):
    encoded = format(int_value, 'x')
    length = len(encoded)
    encoded = encoded.zfill(length+length%2)
    return encoded.decode('hex')


