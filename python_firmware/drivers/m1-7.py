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
import minimalmodbus
import minimalmodbusM1
import pickle
import json
import vpn
import subprocess
import socket
import copy
try:
    from xmodem import XMODEM
except:
    pass
import zlib
from device_base import deviceBase
try:
    from modbus import modbus_rtu
except:
    pass
from struct import *
try:
    import modbus
    from modbus import defines as cst
    from modbus import modbus_tcp
except:
    print "no tcp modbus"
try:
    from pycomm.ab_comm.clx import Driver as ClxDriver
    from pycomm.ab_comm.slc import Driver as SlcDriver
except:
    print "no Ethernet/IP support"
try:
    import logger
except:
    print "Missing logger"
    pass

_NUMBER_OF_BYTES_PER_REGISTER = 2



analogMap = {

    "uval":"units_high",
    "lval":"units_low",
    "uvolts":"volts_high",
    "lvolts":"volts_low",
    "low":"alarm_low",
    "high":"alarm_high",
    "Not Yet":"action_high",
    "N/A":"action_low",
    "change":"change_amount",
    "minrep":"min_period",
    "grp":"grp",
    "mult":"multiplier",
    "int":"interval",
    "ch":"change_amount"
    }

analogToChannelMap = {
    "units_high":"uval",
    "units_low":"lval",
    "volts_high":"uvolts",
    "volts_low":"lvolts",
    "alarm_low":"low",
    "alarm_high":"high",
    "change_amount":"change",
    "min_period":"minrep",
    "grp":"grp"
    }


class start(threading.Thread, deviceBase):
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
        deviceBase.__init__(self, name=name, number=number, mac=mac, Q=Q, mcu=mcu, companyId=companyId, offset=offset, mqtt=mqtt, Nodes=Nodes)
        
        self.daemon = True

        self.vpn = vpn.vpn()

        self.modbusInterfaces = {}
        self.lock = threading.Lock()
        self.analogLock = threading.Lock()
        self.flyFileLocation = "/root/python_firmware/drivers/output.py"
        self.lastData = ""
        self.fileLoading = False
        #self.mcu.digitalOut1(str(1))
        #self.mcu.digitalOut2(str(1))
        #self.mcu.digitalOut3(str(1))
        #self.mcu.digitalOut4(str(1))

        self.version = "29"

        self.sysReboot = False
        #check and see if we are going to update the mcu code
        if os.path.isfile('/root/python_firmware/drivers/gsmgps.py'):
            print "found new gsmgps file"
            os.system("/bin/mv -f /root/python_firmware/drivers/gsmgps.py /root/python_firmware/mcu/gsmgps.py")
            #try and delte the file just in case
            os.system("/bin/rm -f /root/python_firmware/drivers/gsmgps.py")
            os.system("/bin/rm -f /root/python_firmware/drivers/gsmgps.pyc")
            self.sysReboot = True
        if os.path.isfile('/root/python_firmware/drivers/mcu_main.py'):
            print "found new mcu_main file"
            os.system("/bin/mv -f /root/python_firmware/drivers/mcu_main.py /root/python_firmware/mcu/mcu_main.py")
            #try and delte the file just in case
            os.system("/bin/rm -f /root/python_firmware/drivers/mcu_main.py")
            os.system("/bin/rm -f /root/python_firmware/drivers/mcu_main.pyc")
            self.sysReboot = True
        if os.path.isfile('/root/python_firmware/drivers/device_base.py'):
            print "found new device_base file"
            os.system("/bin/mv -f /root/python_firmware/drivers/device_base.py /root/python_firmware/device_base.py")
            #try and delte the file just in case
            os.system("/bin/rm -f /root/python_firmware/drivers/device_base.py")
            os.system("/bin/rm -f /root/python_firmware/drivers/device_base.pyc")
            self.sysReboot = True
        if os.path.isfile('/root/python_firmware/drivers/vpn.py'):
            print "found new vpn file"
            os.system("/bin/mv -f /root/python_firmware/drivers/vpn.py /root/python_firmware/vpn.py")
            #try and delte the file just in case
            os.system("/bin/rm -f /root/python_firmware/drivers/vpn.py")
            os.system("/bin/rm -f /root/python_firmware/drivers/vpn.pyc")
            self.sysReboot = True


        
        

        #modbus dictionary for the ComBox
        #multiplier can be multiply or divide or None
        #changeType = number or percent
        #
        

        self.com1Reads = 0
        self.com1Errors = 0
        self.com2Reads = 0 
        self.com2Errors = 0

        self.pulses = None

        self.modbus_logger = logger.Logger(channel_name="log-modbus",message_sender=self.sendtodb,enabled=True)

        self.IOmap = {
            "1":"On",
            1:"On",
            0:"Off",
            "0":"Off"
            }

        #load stored DIO forward rules
        #load stored location spoofing data:
        try:
            with open('/root/python_firmware/drivers/dioForward.p', 'rb') as handle:
                self.dioForward = pickle.load(handle)
                
            print "found pickled dictionary"
            print self.dioForward
        except:
            print "couldn't load locSpoof from pickle"
            self.dioForward = {
                "cloop":{"on":"off","deviceName":"M1","channel":"cloop","unitNum":"1"},
                "din1":{"on":"off","deviceName":"M1","channel":"din1","unitNum":"1"},
                "din2":{"on":"off","deviceName":"M1","channel":"din2","unitNum":"1"},
                "din3":{"on":"off","deviceName":"M1","channel":"din3","unitNum":"1"},
                "din4":{"on":"off","deviceName":"M1","channel":"din4","unitNum":"1"},
                "analog1":{"on":"off","deviceName":"M1","channel":"analog1","unitNum":"1"},
                "analog2":{"on":"off","deviceName":"M1","channel":"analog2","unitNum":"1"},
                "analog3":{"on":"off","deviceName":"M1","channel":"analog3","unitNum":"1"},
                "analog4":{"on":"off","deviceName":"M1","channel":"analog4","unitNum":"1"},
                "dout1":{"on":"off","deviceName":"M1","channel":"dout1","unitNum":"1"},
                "dout2":{"on":"off","deviceName":"M1","channel":"dout2","unitNum":"1"},
                "dout3":{"on":"off","deviceName":"M1","channel":"dout3","unitNum":"1"},
                "dout4":{"on":"off","deviceName":"M1","channel":"dout4","unitNum":"1"},
                "relay1":{"on":"off","deviceName":"M1","channel":"relay1","unitNum":"1"},
                "vin":{"on":"off","deviceName":"M1","channel":"vin","unitNum":"1"},
                "bat":{"on":"off","deviceName":"M1","channel":"bat","unitNum":"1"},
                "temp":{"on":"off","deviceName":"M1","channel":"temp","unitNum":"1"},
                "pulse":{"on":"off","deviceName":"M1","channel":"pulse","unitNum":"1"},
                "ver":{"on":"off","deviceName":"M1","channel":"ver","unitNum":"1"},
                "modcom":{"on":"off","deviceName":"M1","channel":"ver","unitNum":"1"}
                }


        #load stored analog input data
        try:
            with open('/root/python_firmware/drivers/analogData.p', 'rb') as handle:
                self.analogData = pickle.load(handle)
                
            print "found analogData dictionary"
            print self.analogData
        except:
            print "couldn't load analogData from pickle"
            self.analogData = { 
                "vin":{"units_high":30,
                       "units_low":0,
                       "volts_high":30,
                       "volts_low":0,
                       "alarm_low":0,
                       "alarm_high":30,
                       "action_high":None,
                       "action_low":None,
                       "change_amount":0.5,
                       "min_period":600,
                       "grp":(3600*6),
                       "last_value":"",
                       "last_send_time":0
                    },
                "bat":{"units_high":30,
                       "units_low":0,
                       "volts_high":30,
                       "volts_low":0,
                       "alarm_low":0,
                       "alarm_high":30,
                       "action_high":None,
                       "action_low":None,
                       "change_amount":0,
                       "min_period":3600,
                       "grp":None,
                       "last_value":"",
                       "last_send_time":0
                    },
                "analog1":{"units_high":30,
                       "units_low":0,
                       "volts_high":30,
                       "volts_low":0,
                       "alarm_low":0,
                       "alarm_high":30,
                       "action_high":None,
                       "action_low":None,
                       "change_amount":0,
                       "min_period":30,
                       "grp":None,
                       "last_value":"",
                       "last_send_time":0
                    },
                "analog2":{"units_high":30,
                       "units_low":0,
                       "volts_high":30,
                       "volts_low":0,
                       "alarm_low":0,
                       "alarm_high":30,
                       "action_high":None,
                       "action_low":None,
                       "change_amount":0,
                       "min_period":30,
                       "grp":None,
                       "last_value":"",
                       "last_send_time":0
                    },
                "analog3":{"units_high":30,
                       "units_low":0,
                       "volts_high":30,
                       "volts_low":0,
                       "alarm_low":0,
                       "alarm_high":30,
                       "action_high":None,
                       "action_low":None,
                       "change_amount":0,
                       "min_period":30,
                       "grp":None,
                       "last_value":"",
                       "last_send_time":0
                    },
                "analog4":{"units_high":30,
                       "units_low":0,
                       "volts_high":30,
                       "volts_low":0,
                       "alarm_low":0,
                       "alarm_high":30,
                       "action_high":None,
                       "action_low":None,
                       "change_amount":0,
                       "min_period":30,
                       "grp":None,
                       "last_value":"",
                       "last_send_time":0
                    },
                "cloop":{"units_high":20,
                       "units_low":3,
                       "volts_high":20,
                       "volts_low":3,
                       "alarm_low":0,
                       "alarm_high":30,
                       "action_high":None,
                       "action_low":None,
                       "change_amount":0,
                       "min_period":30,
                       "grp":None,
                       "last_value":"",
                       "last_send_time":0
                    },
                "pulse":{"multiplier":1,
                       "change_amount":20,
                       "interval":1800,
                       "last_value":"",
                       "last_send_time":0
                    }

                
                }


        #load stored location spoofing data:
        try:
            with open('/root/python_firmware/drivers/locSpoof.p', 'rb') as handle:
                self.locSpoof = pickle.load(handle)
                
            print "found pickled dictionary"
            print self.locSpoof
        except:
            print "couldn't load locSpoof from pickle"
            self.locSpoof = { "on":"off","mode":"forward","mac":None}




        #load stored value for updating device address on boot
        try:
            with open('/root/python_firmware/drivers/adrsetonboot.p', 'rb') as handle:
                self.adrsetonboot = pickle.load(handle)
                
            print "found adrsetonboot"
            print self.adrsetonboot
        except:
            print "couldn't load adrsetonboot from pickle"
            self.adrsetonboot = False

        #load stored modbus mappings
        try:
            with open('/root/python_firmware/drivers/deviceaddress.p', 'rb') as handle:
                self.deviceaddress = pickle.load(handle)
                
            print "found pickled dictionary"
            print self.deviceaddress
        except:
            print "couldn't load deviceaddress from pickle"
            self.deviceaddress = 1

        #load stored modbus mappings
        try:
            with open('/root/python_firmware/drivers/modbusMap.p', 'rb') as handle:
                self.modbusMap = pickle.load(handle)
                
            print "found pickled dictionary"
            print self.modbusMap
        except:
            print "couldn't load modbusMap from pickle"
            self.modbusMap = { }

        #load stored geo data
        try:
            with open('/root/python_firmware/drivers/geoData.p', 'rb') as handle:
                self.geoData = pickle.load(handle)
            print "found pickled Geo Data"
            print self.geoData
        except:
            print "couldn't load modbusMap from pickle"
            self.geoData = {}

        if self.adrsetonboot or self.adrsetonboot == "True" or self.adrsetonboot == True:
            self.changeDeviceAddress(int(self.deviceaddress))
            print "updating addresses for modbus"


        self.register()

        self.finished = threading.Event()
        threading.Thread.start(self)
        self.last_xbee_sig_time = 0
        
        
    #this is a required function for all drivers, its goal is to upload some piece of data
    #about your device so it can be seen on the web
    def register(self):
        self.sync = True
        self.sendtodb("connected", "True", 0)
        #{'c':'none','b':'9600','p':'none','s':'1','f':'Off'}
        self.last_signal = 0
        self.last_gps = ""
        self.last_gps_time = 0
        self.last_power = ""
        self.last_pulses = -21
        self.last_xbee_sig_time = 0


        self.syncGeoTags()

        with self.lock:
            self.syncModbus()
            for comport in self.modbusMap:
                for address in self.modbusMap[comport]["addresses"]:
                    for channelName in self.modbusMap[comport]["addresses"][address]:
                        self.modbusMap[comport]["addresses"][address][channelName]["la"] = ""
                
        


        self.forwardingMap = {
                            "1": {
                                                "port":"",
                                                "externalPort":"",
                                                "externalIP":""
                                            },
                            "2": {
                                                "port":"",
                                                "externalPort":"",
                                                "externalIP":""
                                            },
                            "3": {
                                                "port":"",
                                                "externalPort":"",
                                                "externalIP":""
                                            },
                            "4": {
                                                "port":"",
                                                "externalPort":"",
                                                "externalIP":""
                                            }
                
                            }
        
        self.last_alarms = ""
        self.last_state = ""
        self.last_tct1 = ""
        self.last_tsp1 = ""
        self.last_tmd1 = ""
        self.last_tst1 = ""

        self.vpnCheckUp()
        #self.count = 3001

    def stop (self):
        self.finished.set()
        self.join()
    
    def analogDataSync(self, all=True):

        with self.analogLock:
            for item in self.analogData:
                self.analogData[item]["last_value"] = ""

                if all:
                    for channel in self.analogData[item]:
                        name = None
                        if item == "analog1" and channel in analogToChannelMap:
                            name = "a1-" + analogToChannelMap[channel]
                        elif item == "analog2" and channel in analogToChannelMap:
                            name = "a2-" + analogToChannelMap[channel]
                        elif item == "analog3" and channel in analogToChannelMap:
                            name = "a3-" + analogToChannelMap[channel]
                        elif item == "analog4" and channel in analogToChannelMap:
                            name = "a4-" + analogToChannelMap[channel]
                        elif item == "cloop" and channel in analogToChannelMap:
                            name = "cl-" + analogToChannelMap[channel]

                        if name is not None:
                            self.sendtodb(name, str(self.analogData[item][channel]), 0)
        

        

    def vpnCheckUp(self):
        #get ip address and subnet mask 
        p = subprocess.Popen("/sbin/uci get network.lan.netmask", stdout=subprocess.PIPE, shell=True)
        (output, err) = p.communicate()
        mask = output.replace("\n","")
        self.sendtodb("getmask", mask, 0)
        p = subprocess.Popen("/sbin/uci get network.lan.ipaddr", stdout=subprocess.PIPE, shell=True)
        (output, err) = p.communicate()
        ip = output.replace("\n","")
        self.sendtodb("ip", ip, 0)
        try:
            for i in range(1,5):
                for channel in self.vpn.forwardingMap[str(i)]:
                    if self.vpn.forwardingMap[str(i)][channel] != self.forwardingMap[str(i)][channel]:
                        print "new value found in the vpn"
                        if channel == "port":
                            newchannel = ("port" + str(i))
                        elif channel == "externalPort":
                            newchannel = ("eport" + str(i))
                        elif channel == "externalIP":
                            newchannel = ("ip"  + str(i))
                       
                        self.sendtodb(str(newchannel), str(self.vpn.forwardingMap[str(i)][channel]), 0)
                        self.forwardingMap[str(i)][channel] = self.vpn.forwardingMap[str(i)][channel]
            self.sendtodb("vpnip", str(self.vpn.get_ip_address("tun0")), 0)
        except Exception,e:
            print e

        
    
        
    def start(self):
        
        
        
        # you could add other ddo settings here
        thread.start_new_thread(self.loop, ())
        
    
    
    # def stop(): uses XBeeSerial.stop()
    
    
    ## Locally defined functions:

    def readCountThread(self):
        item = "modcom"
        #here I will calculate the rate of reads and errors from the modbus/ethernet IP
        initValue = self.dioForward[item]["on"] + "," + self.dioForward[item]["deviceName"] + "," + self.dioForward[item]["unitNum"] + "," + self.dioForward[item]["channel"]
        
        
        
        self.sendtodb("fwd-modcom", initValue,0)
        last_newCom1Errors = -100
        last_newCom2Errors = -100
        last_newCom1Reads = -100
        last_newCom2Reads = -100
        lastModCom = ""
        while True:
            currentCom1Errors = self.com1Errors
            currentCom2Errors = self.com2Errors
            currentCom1Reads = self.com1Reads
            currentCom2Reads = self.com2Reads
            time.sleep(60)
            newCom1Errors = (self.com1Errors - currentCom1Errors)
            newCom2Errors = (self.com2Errors - currentCom2Errors)
            newCom1Reads = (self.com1Reads - currentCom1Reads)
            newCom2Reads = (self.com2Reads - currentCom2Reads)

            if abs(last_newCom1Errors - newCom1Errors) > 1 or (newCom1Errors == 0 and last_newCom1Errors != 0):
                self.sendtodb("c1err", str(newCom1Errors), 0)
                last_newCom1Errors = newCom1Errors
            
            if abs(last_newCom2Errors - newCom2Errors) > 1 or (newCom2Errors == 0 and last_newCom2Errors != 0):
                self.sendtodb("c2err", str(newCom2Errors), 0)
                last_newCom2Errors = newCom2Errors

            if abs(last_newCom1Reads - newCom1Reads) > 1 or (newCom1Reads == 0 and last_newCom1Reads != 0):
                self.sendtodb("c1rd", str(newCom1Reads), 0)
                last_newCom1Reads = newCom1Reads

            if abs(last_newCom2Reads - newCom2Reads) > 1 or (newCom2Reads == 0 and last_newCom2Reads != 0):
                self.sendtodb("c2rd", str(newCom2Reads), 0)
                last_newCom2Reads = newCom2Reads
            
            if self.dioForward[item]["on"].lower() == "on":
                if int(newCom1Errors) + int(newCom2Errors) > 3:
                    val = "Off"
                else:
                    val = "On"
                if val != lastModCom:
                    lastModCom = val
                    ch = self.dioForward[item]["unitNum"]
                    deviceName = self.dioForward[item]["deviceName"]
                    chName = self.dioForward[item]["channel"]

                    if self.locSpoof["on"].lower() == "on":

                        if self.locSpoof["mode"].lower() == "forward":
                            self.sendtodbLoc(ch, chName, val, 0, deviceName, self.locSpoof["mac"])
                        elif self.locSpoof["mode"].lower() == "copy":
                            self.sendtodbLoc(ch, chName, val, 0, deviceName, self.locSpoof["mac"])
                            self.sendtodb(item, val, 0)
                    else:
                        self.sendtodbDev(ch, chName, val, 0, deviceName)
                        self.sendtodb(item, val, 0)

            


        


    def run(self):

        #check and see if you need to update all of the modbus device addresses
        

        #example of how to serve modbus rtu data
        #serial = self.mcu.rs485
        #server = modbus_rtu.RtuServer(serial)
        #server.start()
        #slave_1 = server.add_slave(1)
        #slave_1.add_block('0', 3, 3000, 2)
        #slave_1.set_values("0", 100, [25,99])

        self.last = {}

        #start ftp server
        os.system("/usr/sbin/pure-ftpd &")


        #start thread for checking GPIO ports
        thread.start_new_thread(self.dioThread, ())

        #start data counting thread
        thread.start_new_thread(self.get_network_bytes, ())


        #start thread for rs232 for air quaility guys
        #thread.start_new_thread(self.RS232Thread, ())

        #on startup send the version number
        self.sendtodb("version", str(self.version), 0)
        self.sendtodb("log", "system start up", 0)

        #reboot the system to install the latest cpu files, this can cause an infinate reboot cycle if we get the cloud version wrong
        if self.sysReboot:
            #sleep a little just incase we get stuck in a reboot cycle, its always good to wait
            print "waiting for restart"
            time.sleep(30)
            os.system("/root/normalStart.sh")

        
        while self.modbusInterfaces == {}:
            with self.lock:
                for com in self.modbusMap:
                    port = self.modbusMap[com]["c"]
                    if port not in self.modbusInterfaces:
                        if port == "M1-232":
                            baud = self.modbusMap[com]["b"]
                            if baud == "":
                                baud = 9600
                            else:
                                baud = int(baud)
                            #set up rs232 for link to DeapSea
                            connected = False
                            #make sure the baud rate gets set
                            while connected == False:
                                connected = self.mcu.set232Baud(baud)
                                time.sleep(1)
                            serial2 = self.mcu.rs232

                            self.instrument2 = minimalmodbusM1.Instrument(1, serial2)
                            self.instrument2.address = 1
                            self.modbusInterfaces[port] = self.instrument2
                            print "added M1 232 interface"
                        elif port == "M1-485":
                            baud = self.modbusMap[com]["b"]
                            if baud == "":
                                baud = 9600
                            else:
                                baud = int(baud)
                            #set up rs232 for link to DeapSea
                            connected = False
                            #make sure the baud rate gets set
                            while connected == False:
                                connected = self.mcu.set485Baud(baud)
                                time.sleep(1)
                            serial4 = self.mcu.rs485
                            
                            self.instrument1 = minimalmodbusM1.Instrument(1, serial4)
                            self.instrument1.address = 1
                            self.modbusInterfaces[port] = self.instrument1
                            print "added M1 485 interface"
                        elif port == "M1-MESH":
                            baud = self.modbusMap[com]["b"]
                            if baud == "":
                                baud = 9600
                            else:
                                baud = int(baud)
                            #set up rs232 for link to DeapSea
                            connected = False
                            #make sure the baud rate gets set
                            
                            serialX = self.mcu.xbee

                            self.instrument1 = minimalmodbusM1.Instrument(1, serialX)
                            self.instrument1.address = 1
                            self.modbusInterfaces[port] = self.instrument1
                            print "added M1 XBEE interface"
                        elif port == "TCP":
                            print "adding TCP interface for modbus"
                            ip = self.modbusMap[com]["b"]
                            p = self.modbusMap[com]["p"]
                            self.tcpInstrument = modbus_tcp.TcpMaster(host=ip, port=int(p))
                            self.modbusInterfaces[port] = self.tcpInstrument
                            print "done tcp"
                            print port
                            print self.modbusInterfaces[port]
                        elif port == "ETHERNET/IP":
                            print "adding Ethernet/IP interface for modbus?"
                            ip = self.modbusMap[com]["b"]
                            self.ethernetInstrument = ClxDriver()
                            try:
                                self.ethernetInstrument.open(ip)
                            except:
                                print "Cannot connect to Ethernet/IP (control Logix) device at: ", ip
                            #p = self.modbusMap[com]["p"]
                            #Since my ethernet IP lib will timeout crazy fast, I plan on just
                            #reconnecting with each loop, so I won't try to make my connection string here
                            self.modbusInterfaces[port] = self.ethernetInstrument
                            print "done Ethernet/IP"
                            print port
                            print self.modbusInterfaces[port]
                        elif port == "ETHERNET/IP-MICRO":
                            print "adding Ethernet/IP interface for modbus?"
                            ip = self.modbusMap[com]["b"]
                            self.ethernetInstrument =  SlcDriver()
                            try:
                                self.ethernetInstrument.open(ip)
                            except:
                                print "Cannot connect to Ethernet/IP (micrologix) device at: ", ip
                            #p = self.modbusMap[com]["p"]
                            #Since my ethernet IP lib will timeout crazy fast, I plan on just
                            #reconnecting with each loop, so I won't try to make my connection string here
                            self.modbusInterfaces[port] = self.ethernetInstrument
                            print "done Ethernet/IP-MIRCO"
                            print port
                            print self.modbusInterfaces[port]
                        else:
                            connected = False
                            tries = 0
                            while not connected:
                                tries += 1
                                port = self.modbusMap[com]["c"]
                                baud = self.modbusMap[com]["b"]
                                if port == None or port == "none" or port == "None":
                                    connected = True
                                    continue
                                if baud == "":
                                    baud = 9600
                                else:
                                    baud = int(baud)
                                try:
                                    instrument = minimalmodbus.Instrument(port, 1) # port name, slave address (in decimal)
                                    instrument.serial.baudrate = baud
                                    instrument.serial.timeout  = 1 # seconds
                                    instrument.address = 1
                                    connected = True
                                    self.modbusInterfaces[port] = instrument
                                    print "added custom interface: " + port
                                    break
                                except Exception,e:
                                    if tries > 10:
                                        connected = True
                                        break
                                    self.sendtodb("error", str(e), 0)
                                    time.sleep(20)
            
            time.sleep(30)

        time.sleep(10)
       
        self.count = 3001
        hb_count = 0
        
        thread.start_new_thread(self.readCountThread, ())

        while not self.finished.isSet():
            self.count += 1
            time.sleep(5)
                
            try:
               
                print "################################"
                print "#############sending data ######"
               
                try:
                    
                    self.processModbus()
                except Exception,e: 
                    print(str(e))
                    self.sendtodb("error2", str(e), 0)

            except Exception,e: print(str(e))
                    # We only want the modbus logger to run for one loop, so now that loop is done, catch it here
            if self.modbus_logger.is_enabled():
                self.modbus_logger.disable()
                self.sendtodb("modbusdebug", "Off", 0)
        
    
    
    
    
    

    
    
    # internal functions & classes

    def processModbus(self):
       # "mdl": {"length":16, "address":769, "type":"int", "last_val":"", "multiplier":None, "multiplierVal": "1"},

        print "checking modbus"
        print self.modbusMap
        self.modbus_logger.log_message("MODBUS: -info- Starting modbus loop")
        for com in self.modbusMap:

            
            for address in self.modbusMap[com]["addresses"]:
                #get the modbus instrument
                instrument = self.modbusInterfaces[self.modbusMap[com]["c"]]
                #tcp and ethernet/IP does the device address differently, this only applies to the modbus RTU
                if self.modbusMap[com]["c"] != "TCP" and self.modbusMap[com]["c"] != "ETHERNET/IP":
                    try:
                        instrument.address = int(address)
                    except:
                        continue
                ch_un = address
                
                self.modbus_logger.log_message("MODBUS: -info- Reading device number %s" % str(address))

                for chName in self.modbusMap[com]["addresses"][address]:
                    with self.lock:
                        #time.sleep(1)
                        #"{'chn':'2-1-v','dn':'M1','da':'1','le':'16','a':'301','f':'3','t':'int','la':null,'m':'none','mv':'1','ct':'number','c':'1','vm':null,'r':'1-200','s':'On'}"
                        #for a bytearray we will have a new argument called bytearray or bytearraybs for byte swapped. 
                        #"t":"bytearray","bytary":{1:{"chan":"alm1","val0":"Off","val1":"On"},2:{"chan":"alm2","val0":"Off","val1":"On"},3:{},4:{},5:{},6:{},7:{},8:{},9:{},10:{},11:{},12:{},13:{},14:{},15:{}}
                        try:
                            status = self.modbusMap[com]["addresses"][address][chName]['s']

                            #if the status is no on, continue
                            if status != "On":
                                continue

                            #see if it has the update for a unit number for each register, if not, use the device address
                            try:
                                unitNumber = int(str(self.modbusMap[com]["addresses"][address][chName]['un']))
                                ch = unitNumber
                            except:
                                ch = ch_un
                            if int(ch) < 10:
                                ch = "0" + str(ch)

                            deviceName = str(self.modbusMap[com]["addresses"][address][chName]['dn'])
                            functioncode = str(self.modbusMap[com]["addresses"][address][chName]['f'])
                            length = int(str(self.modbusMap[com]["addresses"][address][chName]['le']))
                            regAddress = str(self.modbusMap[com]["addresses"][address][chName]['a'])
                            type = str(self.modbusMap[com]["addresses"][address][chName]['t'])
                            last_val = self.modbusMap[com]["addresses"][address][chName]['la']
                            multiplier = str(self.modbusMap[com]["addresses"][address][chName]['m'])
                            try:
                                if multiplier != "function":
                                    multiplierVal = float(self.modbusMap[com]["addresses"][address][chName]['mv'])
                                else:
                                    multiplierVal = str(self.modbusMap[com]["addresses"][address][chName]['mv'])
                            except:
                                multiplierVal = 1
                            changeType = str(self.modbusMap[com]["addresses"][address][chName]['ct'])

                            m1Channel = str(self.modbusMap[com]["addresses"][address][chName]['m1ch']) + "-v"
                            channel = str(self.modbusMap[com]["addresses"][address][chName]['chn'])

                            try:
                                vn = self.modbusMap[com]["addresses"][address][chName]['vn']
                            except:
                                raise ValueError("Could not read vanity name for register " + regAddress)
                                vn = None

                            self.modbus_logger.log_message("MODBUS: -info- Starting loop for %s on %s " % (vn, regAddress))

                            try:
                                min_time = int(self.modbusMap[com]["addresses"][address][chName]['mrt'])
                                last_time = int(self.modbusMap[com]["addresses"][address][chName]['lrt'])
                            except:
                                self.modbusMap[com]["addresses"][address][chName]['mrt'] = 60
                                self.modbusMap[com]["addresses"][address][chName]['lrt'] = 0
                                min_time = int(self.modbusMap[com]["addresses"][address][chName]['mrt'])
                                last_time = int(self.modbusMap[com]["addresses"][address][chName]['lrt'])

                            #see if there is a period in which you have to get a value, even if it hasn't changed
                            #sudo code: if (current time - last send time ) > period (and period is not None) send up new point
                            try:
                                period = int(self.modbusMap[com]["addresses"][address][chName]['grp'])
                                if period < 10:
                                    period = None
                            except:
                                period = None

                            print "here is your period: ", period
                            print time.time() - last_time

                            #check to see if you need to send based on a period that you need a new value
                            try:
                                if period != None:
                                    if (time.time() - last_time) > period:
                                        send = True
                                    else:
                                        send = False
                                else:
                                    send = False
                            except:
                                send = False

                            print "here is your send value: ", send

                            try:
                                change = int(str(self.modbusMap[com]["addresses"][address][chName]['c']))
                            except:
                                change = 0
                        
                            #load the value map
                            valueMap = self.modbusMap[com]["addresses"][address][chName]['vm']
                            try:
                                if len(valueMap.keys()) < 1:
                                    valueMap = None
                            except:
                                valueMap = None

                            range1 = str(self.modbusMap[com]["addresses"][address][chName]['r'])
                            try:
                                if len(range1) < 3:
                                    range1 = None
                            except:
                                range1 = None
                            if multiplier == "none":
                                multiplier = None
                            if last_val == None or last_val == "none":
                                last_val = ""

                            try:
                                if range1 is not None:
                                    numOfDashes = range1.count('-')
                                    if numOfDashes == 1:
                                        #both positive
                                        high = range1.split("-")[1]
                                        low = range1.split("-")[0]
                                    elif numOfDashes == 2:
                                        #first number is negative
                                        high = range1.split("-")[2]
                                        low = "-" + range1.split("-")[1]
                                    elif numOfDashes == 3:
                                        #both numbers are negative
                                        high = "-" + range1.split("-")[3]
                                        low = "-" + range1.split("-")[1]

                            except:
                                range1 = None


                            #first check for coils:
                            if type == "coil":
                                val = instrument.read_bit(int(regAddress), functioncode=int(functioncode))

                            #now check for byte arrary
                            elif type == "bitarray" or type == "bitarraybs":
                                print "found bytearray"
                                arrayOfBits = self.modbusMap[com]["addresses"][address][chName]['bytary']



                                if type == "bitarraybs":
                                    bs = True
                                else:
                                    bs = False
                            
                                #byte arrays are either 16 bit or 32. But mostly 16 will be supported. Thats up to 
                                if self.modbusMap[com]["c"] == "TCP":
                                    lst = instrument.execute(int(address), int(functioncode), int(regAddress), 1)
                                    val = lst[0]
                                elif self.modbusMap[com]["c"] == "ETHERNET/IP":
                                    val = self.EthernetIPGET(instrument, com, regAddress)
                                    if val == None:
                                        raise ValueError('Ethernet IP read Failed')
                                elif self.modbusMap[com]["c"] == "ETHERNET/IP-MICRO":
                                    val = self.EthernetIPGETMicro(instrument, com, regAddress)
                                    if val == None:
                                        raise ValueError('Ethernet IP MICRO read Failed')
                                else:
                                    val = instrument.read_register(int(regAddress), functioncode=int(functioncode))
                                bits = self.byteArray(val, int(length), bs)
                                print "here are the bits"
                                print bits

                                print arrayOfBits
                                for number in range(int(length)):

                                    try:
                                        if (last_val[number] != bits[number]) or send == True:

                                            bitInfo = arrayOfBits[number + 1]
                                            if bits[number] == 1 or bits[number] == "1":
                                                val = bitInfo["val1"]
                                            elif bits[number] == 0 or bits[number] == "0":
                                                val = bitInfo["val0"]
                                            if bitInfo["chan"] == "":
                                                continue
                                            self.sendtodbDev(ch, bitInfo["chan"], val, 0, deviceName)
                                    except Exception, e:
                                        print "bit error"
                                        print e
                                        bitInfo = arrayOfBits[number + 1]

                                        if bits[number] == 1 or bits[number] == "1":

                                            val = bitInfo["val1"]
                                        elif bits[number] == 0 or bits[number] == "0":
                                            val = bitInfo["val0"]
                                        if bitInfo["chan"] == "":
                                            continue
                                        self.sendtodbDev(ch, bitInfo["chan"], val, 0, deviceName)
                                if (last_val != bits) or send == True:
                                    self.sendtodb(m1Channel, bits, 0)
                                    self.modbusMap[com]["addresses"][address][chName]['la'] = bits
                                    self.modbusMap[com]["addresses"][address][chName]['lrt'] = time.time()
                                continue
                                
                                


                            elif int(length) == 16 and (type == "int" or type == "ints"):
                                if self.modbusMap[com]["c"] == "TCP":
                                    lst = instrument.execute(int(address), int(functioncode), int(regAddress), 1)
                                    val = lst[0]
                                    if type == "ints":
                                        unsigned = val 
                                        val = unsigned - 65535 if unsigned > 32767  else unsigned
                                elif self.modbusMap[com]["c"] == "ETHERNET/IP":
                                    val = self.EthernetIPGET(instrument, com, regAddress)
                                    if val == None:
                                        raise ValueError('Ethernet IP read Failed')
                                elif self.modbusMap[com]["c"] == "ETHERNET/IP-MICRO":
                                    val = self.EthernetIPGETMicro(instrument, com, regAddress)
                                    if val == None:
                                        raise ValueError('Ethernet IP micro read Failed')
                                else:
                                    #must be normal read
                                    print "getting int"
                                    val = instrument.read_register(int(regAddress), functioncode=int(functioncode))
                                    print val
                                    if type == "ints":
                                        unsigned = val 
                                        val = unsigned - 65535 if unsigned > 32767  else unsigned
                            elif int(length) == 32 and (type == "long" or type == "int" or type == "ints"):
                                #must be read long or read float
                                if type == "int" or type == "ints":
                                    if self.modbusMap[com]["c"] == "TCP":
                                        lst = instrument.execute(int(address), int(functioncode), int(regAddress), 2)
                                        val = int(hex(lst[1]).replace('0x','') + hex(lst[0]).replace('0x',''),16)
                                        if type == "ints":
                                            unsigned = val
                                            val = unsigned - 4294967295 if unsigned > 2147483647  else unsigned
                                    elif self.modbusMap[com]["c"] == "ETHERNET/IP":
                                        val = self.EthernetIPGET(instrument, com, regAddress)
                                        if val == None:
                                            raise ValueError('Ethernet IP read Failed')
                                    elif self.modbusMap[com]["c"] == "ETHERNET/IP-MICRO":
                                        val = self.EthernetIPGETMicro(instrument, com, regAddress)
                                        if val == None:
                                            raise ValueError('Ethernet IP micro read Failed')
                                    else:
                                        val = instrument.read_long(int(regAddress), functioncode=int(functioncode))
                                        if type == "ints":
                                            val = self.int32(int(val))
                            elif type == "float" and int(length) == 32:
                                if self.modbusMap[com]["c"] == "TCP":
                                    lst = instrument.execute(int(address), int(functioncode), int(regAddress), 2)
                                    val = round(unpack('f',pack('>HH',lst[0], lst[1],))[0], 3)
                                elif self.modbusMap[com]["c"] == "ETHERNET/IP":
                                    val = self.EthernetIPGET(instrument, com, regAddress)
                                    if val == None:
                                        raise ValueError('Ethernet IP read Failed')
                                elif self.modbusMap[com]["c"] == "ETHERNET/IP-MICRO":
                                    val = self.EthernetIPGETMicro(instrument, com, regAddress)
                                    if val == None:
                                        raise ValueError('Ethernet IP micro read Failed')
                                else:
                                    val = instrument.read_float(int(regAddress), functioncode=int(functioncode))
                                    val = round(val, 3)
                                    print val
                            elif type == "floatbs" and int(length) == 32:
                                if self.modbusMap[com]["c"] == "TCP":
                                    lst = instrument.execute(int(address), int(functioncode), int(regAddress), 2)
                                    val = round(unpack('f',pack('>HH',lst[1], lst[0],))[0], 3)
                                elif self.modbusMap[com]["c"] == "ETHERNET/IP":
                                    val = self.EthernetIPGET(instrument, com, regAddress)
                                    if val == None:
                                        raise ValueError('Ethernet IP read Failed')
                                elif self.modbusMap[com]["c"] == "ETHERNET/IP-MICRO":
                                    val = self.EthernetIPGETMicro(instrument, com, regAddress)
                                    if val == None:
                                        raise ValueError('Ethernet IP micro read Failed')
                                else:
                                    t = instrument.read_registers(int(regAddress), 2, functioncode=int(functioncode))
                                    val = round(self.byteSwap32(t), 2)
                                print val
                            elif type == "floatbsw" and int(length) == 32:
                                t = instrument.read_registers(int(regAddress), 2, functioncode=int(functioncode))
                                val = round(self.byteSwap32(t) ,2)
                                #now write this to registers to address 0 and 1. Because IWI can't figure out how to use 32 bit floats, we are 
                                #breaking it down into 2 integers. 0 = 16 bit integer left of the decimal place
                                # 1 = 16 bit integer right of the decimal place
                                try:
                                    tm = self.modbusInterfaces[self.modbusMap["1"]["c"]]
                                    reg0 = int(str(val).split(".")[0])
                                    reg1 = int(str(val).split(".")[1])
                                    print reg0, reg1
                                    time.sleep(.5)
                                    self.EthernetIPSETMicro(tm, 1, "N7:10", reg0)
                                    #self.instrument2.write_register(0, reg0)
                                    time.sleep(.5)
                                    #self.instrument2.write_register(1, reg1)
                                    self.EthernetIPSETMicro(tm, 1, "N7:11", reg1)
                                    time.sleep(.5)
                                    #self.instrument2.write_register(4, 1)
                                    print "success setting h2s data to plc"
                                except:
                                    print "failed setting registers for IWI"
                                print val

                            else:
                                continue
                            #check if there is a multiplier
                            if multiplier != None:
                                if multiplier == "divide":
                                    val = round(float((float(val) / float(multiplierVal))), 2)
                                elif multiplier == "multiply":
                                    val = round(float((float(val) * float(multiplierVal))), 2)
                                elif multiplier == "function":
                                    x = float(val)
                                    print str(multiplierVal)
                                    try:
                                        val = eval(str(multiplierVal).strip().replace("&", "'"))
                                        print "eval value: "
                                        print val
                                        try:
                                            val = float(val)
                                        except:
                                            type = "str"
                                    except Exception, e:
                                        print e

                            #check and see if we have a range, if its outside the range1 then just ignore the data and continue
                            if range1 != None and type != "coil" and type != "str":
                                #validate the value is in the range
                                try:
                                    if float(val) > float(high) or float(val) < float(low):
                                        continue
                                except:
                                    self.modbus_logger.log_message("MODBUS: Read value outside of specified range. " + str(val))
                                    print "validation error, skipping value"
                                    continue


                            #if we get to this point the read must have worked, so we can count up the succussful read counts
                            if int(com) == 1:
                                self.com1Reads +=1
                            elif int(com) == 2:
                                self.com2Reads += 1

                            #check if the data has changed
                            if changeType == "number":
                                #compare last value with a change amount to see if we have enough change to send it
                                #first see if you have an empty string as the last value, if so its the first time and we don't need to compare, but just send the value
                                if str(last_val) == "":
                                    if val != last_val or send == True:
                                        if valueMap != None:
                                            try:
                                                print "found Value map"
                                                print valueMap
                                                updateVal = valueMap[str(int(val))]
                                                print "new Value", val
                                            except:
                                                updateVal = val

                                            if deviceName != "M1":
                                                if self.locSpoof["on"].lower() == "on":
                                                    if self.locSpoof["mode"].lower() == "forward":
                                                        self.sendtodbLoc(ch, channel, updateVal, 0, deviceName, self.locSpoof["mac"])
                                                    elif self.locSpoof["mode"].lower() == "copy":
                                                        self.sendtodbLoc(ch, channel, updateVal, 0, deviceName, self.locSpoof["mac"])
                                                        self.sendtodb(m1Channel, updateVal, 0)
                                                else:
                                                    self.sendtodbDev(ch, channel, updateVal, 0, deviceName)
                                                    self.sendtodb(m1Channel, updateVal, 0)
                                            else:
                                                self.sendtodb(m1Channel, updateVal, 0)
                                        else:
                                            if deviceName != "M1":
                                                if self.locSpoof["on"].lower() == "on":
                                                    if self.locSpoof["mode"].lower() == "forward":
                                                        self.sendtodbLoc(ch, channel, val, 0, deviceName, self.locSpoof["mac"])
                                                    elif self.locSpoof["mode"].lower() == "copy":
                                                        self.sendtodbLoc(ch, channel, val, 0, deviceName, self.locSpoof["mac"])
                                                        self.sendtodb(m1Channel, val, 0)
                                                else:
                                                    self.sendtodbDev(ch, channel, val, 0, deviceName)
                                                    self.sendtodb(m1Channel, val, 0)
                                            else:
                                                self.sendtodb(m1Channel, val, 0)
                                        self.modbusMap[com]["addresses"][address][chName]['la'] = val
                                        self.modbusMap[com]["addresses"][address][chName]['lrt'] = time.time()
                                        continue
                                elif type == "str":
                                    if (val != last_val and abs(time.time() - last_time) > min_time) or send == True:
                                        if valueMap != None:
                                            if deviceName != "M1":
                                                if self.locSpoof["on"].lower() == "on":
                                                    if self.locSpoof["mode"].lower() == "forward":
                                                        self.sendtodbLoc(ch, channel, valueMap[str(val)], 0, deviceName, self.locSpoof["mac"])
                                                    elif self.locSpoof["mode"].lower() == "copy":
                                                        self.sendtodbLoc(ch, channel, valueMap[str(val)], 0, deviceName, self.locSpoof["mac"])
                                                        self.sendtodb(m1Channel, valueMap[str(val)], 0)
                                                else:
                                                    self.sendtodbDev(ch, channel, valueMap[str(val)], 0, deviceName)
                                            else:
                                                self.sendtodb(m1Channel, valueMap[str(val)], 0)
                                        else:
                                            if deviceName != "M1":
                                                if self.locSpoof["on"].lower() == "on":
                                                    if self.locSpoof["mode"].lower() == "forward":
                                                        self.sendtodbLoc(ch, channel, val, 0, deviceName, self.locSpoof["mac"])
                                                    elif self.locSpoof["mode"].lower() == "copy":
                                                        self.sendtodbLoc(ch, channel, val, 0, deviceName, self.locSpoof["mac"])
                                                        self.sendtodb(m1Channel, val, 0)
                                                else:
                                                    self.sendtodbDev(ch, channel, val, 0, deviceName)
                                                    self.sendtodb(m1Channel, val, 0)
                                            else:
                                                self.sendtodb(m1Channel, val, 0)
                                        self.modbusMap[com]["addresses"][address][chName]['la'] = val
                                        self.modbusMap[com]["addresses"][address][chName]['lrt'] = time.time()
                                        continue
                                elif type == "coil" :
                                    if (val != last_val and abs(time.time() - last_time) > min_time) or send == True:
                                        if valueMap != None:
                                            if deviceName != "M1":
                                                if self.locSpoof["on"].lower() == "on":
                                                    if self.locSpoof["mode"].lower() == "forward":
                                                        self.sendtodbLoc(ch, channel, valueMap[str(val)], 0, deviceName, self.locSpoof["mac"])
                                                    elif self.locSpoof["mode"].lower() == "copy":
                                                        self.sendtodbLoc(ch, channel, valueMap[str(val)], 0, deviceName, self.locSpoof["mac"])
                                                        self.sendtodb(m1Channel, valueMap[str(val)], 0)
                                                else:
                                                    self.sendtodbDev(ch, channel, valueMap[str(val)], 0, deviceName)
                                                    self.sendtodb(m1Channel, val, 0)
                                            else:
                                                self.sendtodb(m1Channel, valueMap[str(val)], 0)
                                        else:
                                            if deviceName != "M1":
                                                if self.locSpoof["on"].lower() == "on":
                                                    if self.locSpoof["mode"].lower() == "forward":
                                                        self.sendtodbLoc(ch, channel, val, 0, deviceName, self.locSpoof["mac"])
                                                    elif self.locSpoof["mode"].lower() == "copy":
                                                        self.sendtodbLoc(ch, channel, val, 0, deviceName, self.locSpoof["mac"])
                                                        self.sendtodb(m1Channel, val, 0)
                                                else:
                                                    self.sendtodbDev(ch, channel, val, 0, deviceName)
                                                    self.sendtodb(m1Channel, val, 0)
                                            else:
                                                self.sendtodb(m1Channel, val, 0)
                                        self.modbusMap[com]["addresses"][address][chName]['la'] = val
                                        self.modbusMap[com]["addresses"][address][chName]['lrt'] = time.time()
                                        continue
                                elif type == "float" or type == "int" or type == "floatbs" or type == "floatbsw" or type == "ints":
                                    print val
                                    if (abs(float(last_val) - float(val)) > change and abs(time.time() - last_time) > min_time) or send == True:
                                        if valueMap != None:
                                            try:
                                                print "found Value map"
                                                print valueMap
                                                updateVal = valueMap[str(int(val))]
                                                print "new Value", val
                                            except:
                                                updateVal = val
                                            if deviceName != "M1":
                                                if self.locSpoof["on"].lower() == "on":
                                                    if self.locSpoof["mode"].lower() == "forward":
                                                        self.sendtodbLoc(ch, channel, updateVal, 0, deviceName, self.locSpoof["mac"])
                                                    elif self.locSpoof["mode"].lower() == "copy":
                                                        self.sendtodbLoc(ch, channel, updateVal, 0, deviceName, self.locSpoof["mac"])
                                                        self.sendtodb(m1Channel, updateVal, 0)
                                                else:
                                                    self.sendtodb(m1Channel, val, 0)
                                                    self.sendtodbDev(ch, channel, updateVal, 0, deviceName)
                                            else:
                                                self.sendtodb(m1Channel, updateVal, 0)
                                        else:
                                            if deviceName != "M1":
                                                if self.locSpoof["on"].lower() == "on":
                                                    if self.locSpoof["mode"].lower() == "forward":
                                                        self.sendtodbLoc(ch, channel, val, 0, deviceName, self.locSpoof["mac"])
                                                    elif self.locSpoof["mode"].lower() == "copy":
                                                        self.sendtodbLoc(ch, channel, val, 0, deviceName, self.locSpoof["mac"])
                                                        self.sendtodb(m1Channel, val, 0)
                                                else:
                                                    self.sendtodbDev(ch, channel, val, 0, deviceName)
                                                    self.sendtodb(m1Channel, val, 0)
                                            else:
                                                self.sendtodb(m1Channel, val, 0)
                                        self.modbusMap[com]["addresses"][address][chName]['la'] = val
                                        self.modbusMap[com]["addresses"][address][chName]['lrt'] = time.time()

                        except Exception,e:
                            print "had an error on the modbus loop"
                            print(str(e))
                            self.modbus_logger.log_message("MODBUS: Error in modbus loop: " + str(e))
                            #count up on the error
                            if int(com) == 1:
                                self.com1Errors +=1
                            elif int(com) == 2:
                                self.com2Errors += 1
                            continue

    def EthernetIPSETMicro(self, instrument, com, regAddress, val):
        try:
            success = instrument.write_tag(regAddress, val)  
        except:
            self.ethernetInstrument = SlcDriver()
            if self.ethernetInstrument.open(self.modbusMap[com]["b"]):
                success = self.ethernetInstrument.write_tag(regAddress, val)  
            else:
                return False
        return success
        

    def EthernetIPGETMicro(self, instrument, com, regAddress):
        try:
            val = round(float(instrument.read_tag(regAddress)), 2)
        except:
            self.ethernetInstrument = SlcDriver()
            if self.ethernetInstrument.open(self.modbusMap[com]["b"]):
                val = round(float(self.ethernetInstrument.read_tag(regAddress)), 2)
            else:
                return None
        return val

    def EthernetIPGET(self, instrument, com, regAddress):
        try:
            val = instrument.read_tag([regAddress])[0][1]
        except:
            self.ethernetInstrument = ClxDriver()
            if self.ethernetInstrument.open(self.modbusMap[com]["b"]):
                val = self.ethernetInstrument.read_tag([regAddress])[0][1]
                print val
            else:
                return None
        return val

    def EthernetIPSET(self, instrument, com, val):
        try:
            success = instrument.write_tag(val)  
        except Exception, e:
            print e
            self.ethernetInstrument = ClxDriver()
            if self.ethernetInstrument.open(self.modbusMap[com]["b"]):
                success = self.ethernetInstrument.write_tag(val)  
            else:
                return False
        return success
   
                    
    def M1_sync(self, name, value):
        self.register()
        self.count = 3001
        return True
    
    
    def syncModbus(self):
        #{'c':'none','b':'9600','p':'none','s':'1','f':'Off'}
        for comport in self.modbusMap:
            data = """{"c":"%s", "b":"%s", "p":"%s", "s":"%s", "f":"%s"}""" % (self.modbusMap[comport]["c"],self.modbusMap[comport]["b"],self.modbusMap[comport]["p"],self.modbusMap[comport]["s"],self.modbusMap[comport]["f"] )
            name = str(int(comport) * 2) + "s"
            self.sendtodbJSON(name, data, 0)
            for address in self.modbusMap[comport]["addresses"]:
                for channelName in self.modbusMap[comport]["addresses"][address]:
                    name = self.modbusMap[comport]["addresses"][address][channelName]["m1ch"]
                    self.sendtodbJSON(name, json.dumps(self.modbusMap[comport]["addresses"][address][channelName]), 0)
                    try:
                        vn = self.modbusMap[comport]["addresses"][address][channelName]["vn"]
                        self.sendtodb(name+"-vn", vn, 0)
                        hi = self.modbusMap[comport]["addresses"][address][channelName]["ah"]
                        self.sendtodb(name+"-hi", hi, 0)
                        low = self.modbusMap[comport]["addresses"][address][channelName]["al"]
                        self.sendtodb(name+"-low", low, 0)
                    except Exception, e:
                        print "error finding vanity name"
                        print e


    
    def handleModbusEntry(self, name, value):

        #odd naming convention needs to be kept up with
        #check if there is an integer in on the left side of "-" for validation
        try:
            test = int(name.split("-")[0]) 
            com = str(test/2)
        except:
            return False


            

        newVal = value.replace("'", '"')
        newJson = json.loads(newVal)
        #{'s': 'Off'}
        #check here to see if this is a deletion 
        if "s" in newJson and not "a" in newJson and newJson["s"] == "Off":
            print "we have a delete request for the channel: " + name
            try:
                for comport in self.modbusMap:
                    for address in self.modbusMap[comport]["addresses"]:
                        for channelName in self.modbusMap[comport]["addresses"][address]:
                            if self.modbusMap[comport]["addresses"][address][channelName]["m1ch"] == name:
                                del self.modbusMap[comport]["addresses"][address][channelName]
                                #now see if there are any other channels at this address, if not delete the address also
                                if len(self.modbusMap[comport]["addresses"][address]) < 1:
                                    del self.modbusMap[comport]["addresses"][address]
                


                self.sendtodb(name, "", 0)
                return True
            except:
                self.sendtodb(name, "", 0)
                return True
                


        


        #we need to see if this is changing from one address to another, if so delete the old one
        #if there usage of this channel, delete it, actually just always deleting it could work, 
        #then if there isn't any other regersters at that address, delete that entire address
        try:
            for comport in self.modbusMap:
                for address in self.modbusMap[comport]["addresses"]:
                    for channelName in self.modbusMap[comport]["addresses"][address]:
                        if self.modbusMap[comport]["addresses"][address][channelName]["m1ch"] == name:
                            del self.modbusMap[comport]["addresses"][address][channelName]
                            #now see if there are any other channels at this address, if not delete the address also
                            if len(self.modbusMap[comport]["addresses"][address]) < 1:
                                del self.modbusMap[comport]["addresses"][address]
                            #self.sendtodb(name, "", 0)


                
            
        except Exception, e:

            try:
                for comport in self.modbusMap:
                    for address in self.modbusMap[comport]["addresses"]:
                        for channelName in self.modbusMap[comport]["addresses"][address]:
                            if self.modbusMap[comport]["addresses"][address][channelName]["m1ch"] == name:
                                del self.modbusMap[comport]["addresses"][address][channelName]
                                #now see if there are any other channels at this address, if not delete the address also
                                if len(self.modbusMap[comport]["addresses"][address]) < 1:
                                    del self.modbusMap[comport]["addresses"][address]
                                #self.sendtodb(name, "", 0)
            except Exception, e:
                print "deletion error"
                print e
            

        channelName = name
        devAddress = newJson["da"]
        newJson["m1ch"] = name

        newEntry = {channelName : newJson}


        #first check and see if the address already exists 
        if devAddress in self.modbusMap[com]["addresses"]:
            #if it is here, then just add a new item to the dictionary
            self.modbusMap[com]["addresses"][devAddress][channelName] = newJson
            pass
        else:
            #make a new address entry for this com port
            self.modbusMap[com]["addresses"][devAddress] = newEntry

        self.sendtodbJSON(name, json.dumps(newJson), 0)
        return True
    
    def handleComSetup(self, name, value):
        interfaces = ["2s","4s","6s","8s","10s","12s","14s","16s","18s","20s"]
        if name in interfaces:

            try:
                com = str(int(name.replace("s","")) / 2)
            except Exception,e:
                print "error with modbus handleComSetup"
                print e
                return False

            #this is the com settings for 232
            #looks like this:{'c':'M1-232','b':'9600','p':'none','s':'1','f':'Off'}
            #c = com port, b = baud, p = parity, s = stop bit, f = flow control

            print value

            #{'c':'none','b':'9600','p':'none','s':'1','f':'Off'}
            newVal = value.replace("'", '"')
            newJson = json.loads(newVal)
            print newJson

            

            port = newJson["c"]
            baud = newJson["b"]
            parity = newJson["p"]
            stopbit = newJson["s"]
            flow = newJson["f"]
            print "I'm at location 12"
            #update the interface:
            connected = False
            tries = 0



             #first check and see if the com port has been set up before
            if com in self.modbusMap:
            
                print "this com port is already here"
                #if the comport is already here, just change its settings and be on your way!
                self.modbusMap[com]["c"] = port
                self.modbusMap[com]["b"] = baud
                self.modbusMap[com]["p"] = parity
                self.modbusMap[com]["s"] = stopbit
                self.modbusMap[com]["f"] = flow
            else:
                #if its new we need to add it, but we need to make sure this is done before we try and add devices to it.
                self.modbusMap[com] = {
                    "c": port,
                    "b": baud,
                    "p":parity,
                    "s":stopbit,
                    "f":flow,
                    "addresses": {}
                    }



            
            if port == "M1-232":
                baud = self.modbusMap[com]["b"]
                if baud == "":
                    baud = 9600
                else:
                    baud = int(baud)
                #set up rs232 for link to DeapSea
                connected = False
                #make sure the baud rate gets set
                while connected == False:
                    connected = self.mcu.set232Baud(baud)
                    time.sleep(1)
                serial2 = self.mcu.rs232

                self.instrument2 = minimalmodbusM1.Instrument(1, serial2)
                self.instrument2.address = 1
                self.modbusInterfaces[port] = self.instrument2
                print "added M1 232 interface"
            elif port == "M1-485":
                baud = self.modbusMap[com]["b"]
                if baud == "":
                    baud = 9600
                else:
                    baud = int(baud)
                #set up rs232 for link to DeapSea
                connected = False
                #make sure the baud rate gets set
                while connected == False:
                    connected = self.mcu.set485Baud(baud)
                    time.sleep(1)
                serial4 = self.mcu.rs485
                            
                self.instrument1 = minimalmodbusM1.Instrument(1, serial4)
                self.instrument1.address = 1
                self.modbusInterfaces[port] = self.instrument1
                print "added M1 485 interface"
            elif port == "M1-MESH":
                baud = self.modbusMap[com]["b"]
                if baud == "":
                    baud = 9600
                else:
                    baud = int(baud)
                #set up rs232 for link to DeapSea
                connected = False
                #make sure the baud rate gets set
                            
                serialX = self.mcu.xbee

                self.instrument1 = minimalmodbusM1.Instrument(1, serialX)
                self.instrument1.address = 1
                self.modbusInterfaces[port] = self.instrument1
                print "added M1 XBEE interface"
            elif port == "TCP":
                ip = self.modbusMap[com]["b"]
                p = self.modbusMap[com]["p"]
                self.tcpInstrument = modbus_tcp.TcpMaster(host=ip, port=int(p))
                self.modbusInterfaces[port] = self.tcpInstrument
            elif port == "ETHERNET/IP":
                print "adding Ethernet/IP interface for modbus?"
                ip = self.modbusMap[com]["b"]
                #p = self.modbusMap[com]["p"]
                #Since my ethernet IP lib will timeout crazy fast, I plan on just
                #reconnecting with each loop, so I won't try to make my connection string here
                self.modbusInterfaces[port] = ip
                print "done Ethernet/IP"
            elif port == "ETHERNET/IP-MICRO":
                print "adding Ethernet/IP interface for modbus?"
                ip = self.modbusMap[com]["b"]
                self.ethernetInstrument =  SlcDriver()
                self.ethernetInstrument.open(ip)
                #p = self.modbusMap[com]["p"]
                #Since my ethernet IP lib will timeout crazy fast, I plan on just
                #reconnecting with each loop, so I won't try to make my connection string here
                self.modbusInterfaces[port] = self.ethernetInstrument
                print "done Ethernet/IP-MIRCO"
                print port
                print self.modbusInterfaces[port]
            else:
                connected = False
                tries = 0
                while not connected:
                    tries += 1
                    port = self.modbusMap[com]["c"]
                    baud = self.modbusMap[com]["b"]
                    if port == None or port == "none" or port == "None":
                        connected = True
                        continue
                    if baud == "":
                        baud = 9600
                    else:
                        baud = int(baud)
                    try:
                        instrument = minimalmodbus.Instrument(port, 1) # port name, slave address (in decimal)
                        instrument.serial.baudrate = baud
                        instrument.serial.timeout  = 1 # seconds
                        instrument.address = 1
                        connected = True
                        self.modbusInterfaces[port] = instrument
                        print "added custom interface: " + port
                        break
                    except Exception,e:
                        if tries > 10:
                            connected = True
                            break
                        self.sendtodb("error", str(e), 0)
                
                

            print "new com port setup"
            print "I'm at location 14"
            print self.modbusMap
            self.sendtodbJSON(name, json.dumps(newJson), 0)
            """self.modbusMap = { "M1-485": {
                                            "port": "/dev/ttySP4",
                                            "baud": "",
                                            "parity":"",
                                            "stopbits":"",
                                            "flowcontrol":"",
                                            "addresses": { 
                                                            "1": {"p4": {"reg":"299","length":32, "address":1, "functioncode":3, "type":"int", "last_val":"", "multiplier":None, "multiplierVal": 1, "changeType":"number", "change":0, "valueMap":None, "range":None}}
                                                          }
                                             }
                                  }
             
                                 """
    def dioThread(self):

        #get modem id on boot
        try:

            mdn = self.mcu.get_modem_id()
            if mdn is not None:
                self.sendtodb("mdn", mdn, 0)
            else:
                mdn = self.mcu.get_modem_id()
                if mdn is not None:
                    self.sendtodb("mdn", mdn, 0)

            time.sleep(1)
            sim = self.mcu.get_sim_id()
            if sim is not None:
                self.sendtodb("sim", sim, 0)
            else:
                sim = self.mcu.get_sim_id()
                if sim is not None:
                    self.sendtodb("sim", sim, 0)
        except:
            pass

        #items to check for change:
        changeDict = {
            "analog1":2,
            "analog2":2,
            "analog3":2,
            "analog4":2,
            "vin":10,
            "bat":1,
            "temp":3,
            "cloop":0.1
            }
        while True:
            try:
                with self.analogLock:
                    self.currentDict = self.mcu.getDict()

                    if self.last_power != "":
                        #check the power state:
                        if float(self.currentDict["vin"]) > 7 and self.last_power == False:
                            print "power coming on, send True"
                            self.last_power = True
                            self.sendtodb("power", "On", 0)
                        elif float(self.currentDict["vin"]) < 7 and self.last_power == True:
                            self.last_power = False
                            self.sendtodb("power", "Off", 0)
                    else:
                        #check the initial state of the power
                        if float(self.currentDict["vin"]) > 7:
                            print "power coming on, send True"
                            self.last_power = True
                            self.sendtodb("power", "On", 0)
                        else:
                            self.last_power = False
                            self.sendtodb("power", "Off", 0)


                    for item in self.currentDict:
                        try:

                            if self.sync == False:
                    
                                #"analog2":{"units_high":30,
                                #"units_low":0,
                                #"volts_high":30,
                                #"volts_low":0,
                                #"alarm_low":0,
                                #"alarm_high":30,
                                #"action_high":None,
                                #"action_low":None,
                                #"change_amount":0,
                                #"min_period":30,
                                #"grp":None,
                                #"last_value":"",
                                #"last_send_time":0
                                #},  
                                # ((high units - low units) / (high volts - low volts) * (current reading - low volts)) + low units

                                if item == "pulse":
                                    if "pulse" not in self.analogData:
                                       self.analogData[item] = {"multiplier":1,
                                                                "change_amount":20,
                                                                "interval":1800,
                                                                "last_value":"",
                                                                "last_send_time":0
                                                                }
                                    #last_val = self.analogData[item]["last_value"]
                                    change = float(self.analogData[item]["change_amount"])
                                    last_time = float(self.analogData[item]["last_send_time"])
                                    interval = int(self.analogData[item]["interval"])
                                    multiplier = float(self.analogData[item]["multiplier"])
                                    #on trigger event send total pulses, and pulses per hour with units
                                    #things to track: interval to check pulses, change amount, multiplier
                                    if abs(int(self.last_pulses) - int(self.currentDict[item])) > int(change) or time.time() - int(last_time) > interval:
                                        self.analogData[item]["last_send_time"] = time.time()

                                        #send up rate per hour
                                        perHour = ( 60 / ((time.time() - int(last_time))/60)) *  abs(int(self.last_pulses) - int(self.currentDict[item]))

                                        self.sendtodb("pph", str(round(perHour * multiplier, 2)), 0)
                                        self.sendtodb("ppm", str(round((perHour/60) * multiplier, 2)), 0)

                                        self.process_pulses(int(self.currentDict[item]), multiplier)
                                        self.last_pulses =  int(self.currentDict[item])
                                    continue

                                if item in self.analogData:
                            


                                    #get its value, its last value, its required change amount, and its last time it sent
                                    val = float(self.currentDict[item])
                                    units_high = float(self.analogData[item]["units_high"])
                                    units_low = float(self.analogData[item]["units_low"])
                                    volts_high = float(self.analogData[item]["volts_high"])
                                    volts_low = float(self.analogData[item]["volts_low"])

                                    val = round(((units_high - units_low) / (volts_high - volts_low) * (val - volts_low)) + units_low, 2)



                                    last_val = self.analogData[item]["last_value"]
                                    change = float(self.analogData[item]["change_amount"])
                                    last_time = float(self.analogData[item]["last_send_time"])
                                    min_time = float(self.analogData[item]["min_period"])
                                    gauranteed_report_period = self.analogData[item]["grp"]
                                    send = False

                                    if gauranteed_report_period != None:
                                        if gauranteed_report_period < 5:
                                            gauranteed_report_period = None


                                    if last_val == "":
                                        last_val = 0
                                        send = True
                                    elif gauranteed_report_period != None:
                                        #if the gauranteed period is met, send = True. Or if its the first run (we know its the first run by the last_val = "" 
                                        if time.time() - last_time > gauranteed_report_period:
                                            send = True
                                        else:
                                            send = False

                                    #check to see if you have reached a meaningful change amount and time or a guaranteed report period
                                    if (abs(float(last_val) - float(val)) > change and abs(time.time() - last_time) > min_time) or send == True:
                                        self.analogData[item]["last_value"] = val
                                        self.analogData[item]["last_send_time"] = time.time()
                                        val = str(val)
                                        if self.dioForward[item]["on"].lower() == "on":
                                            ch = self.dioForward[item]["unitNum"]
                                            deviceName = self.dioForward[item]["deviceName"]
                                            chName = self.dioForward[item]["channel"]

                                            if self.locSpoof["on"].lower() == "on":

                                                if self.locSpoof["mode"].lower() == "forward":
                                                    self.sendtodbLoc(ch, chName, val, 0, deviceName, self.locSpoof["mac"])
                                                elif self.locSpoof["mode"].lower() == "copy":
                                                    self.sendtodbLoc(ch, chName, val, 0, deviceName, self.locSpoof["mac"])
                                                    self.sendtodb(item, val, 0)
                                            else:
                                                self.sendtodbDev(ch, chName, val, 0, deviceName)
                                                self.sendtodb(item, val, 0)
                                        else:
                                            self.sendtodb(item, val, 0)




                                #for binary data, check if its changed, that should always be enough, maybe we can get a guarateed report period later for I/O's

                                elif self.currentDict[item] != self.last[item]:
                                    if item in changeDict:
                                        if abs(float(self.currentDict[item]) - float(self.last[item])) > changeDict[item]:
                                            if self.dioForward[item]["on"].lower() == "on":
                                                ch = self.dioForward[item]["unitNum"]
                                                deviceName = self.dioForward[item]["deviceName"]
                                                chName = self.dioForward[item]["channel"]

                                                if self.locSpoof["on"].lower() == "on":

                                                    if self.locSpoof["mode"].lower() == "forward":
                                                        self.sendtodbLoc(ch, chName, self.currentDict[item], 0, deviceName, self.locSpoof["mac"])
                                                    elif self.locSpoof["mode"].lower() == "copy":
                                                        self.sendtodbLoc(ch, chName, self.currentDict[item], 0, deviceName, self.locSpoof["mac"])
                                                        self.sendtodb(item, self.currentDict[item], 0)
                                                else:
                                                    self.sendtodbDev(ch, chName, self.currentDict[item], 0, deviceName)
                                                    self.sendtodb(item, self.currentDict[item], 0)
                                            else:
                                                self.sendtodb(item, self.currentDict[item], 0)
                                    else:
                                        try:
                                            print "new value for: " + item
                                            if self.dioForward[item]["on"].lower() == "on":
                                                ch = self.dioForward[item]["unitNum"]
                                                deviceName = self.dioForward[item]["deviceName"]
                                                chName = self.dioForward[item]["channel"]

                                                if self.locSpoof["on"].lower() == "on":

                                                    if self.locSpoof["mode"].lower() == "forward":
                                                        self.sendtodbLoc(ch, chName, self.currentDict[item], 0, deviceName, self.locSpoof["mac"])
                                                    elif self.locSpoof["mode"].lower() == "copy":
                                                        self.sendtodbLoc(ch, chName, self.currentDict[item], 0, deviceName, self.locSpoof["mac"])
                                                        self.sendtodb(item, self.currentDict[item], 0)
                                                else:
                                                    self.sendtodbDev(ch, chName, self.currentDict[item], 0, deviceName)
                                                    self.sendtodb(item, self.currentDict[item], 0)
                                            else:
                                                self.sendtodb(item, self.currentDict[item], 0)
                                        except:
                                            pass
                            else:
                                try:
                                    if item == "pulse":
                                        continue
                                    if item in self.analogData:
                                        val = float(self.currentDict[item])
                                        units_high = float(self.analogData[item]["units_high"])
                                        units_low = float(self.analogData[item]["units_low"])
                                        volts_high = float(self.analogData[item]["volts_high"])
                                        volts_low = float(self.analogData[item]["volts_low"])

                                        val = round(((units_high - units_low) / (volts_high - volts_low) * (val - volts_low)) + units_low, 2)
                                
                                        self.analogData[item]["last_value"] = val
                                        self.analogData[item]["last_send_time"] = time.time()
                                        self.currentDict[item] = str(val)

                                    if self.dioForward[item]["on"].lower() == "on":
                                        ch = self.dioForward[item]["unitNum"]
                                        deviceName = self.dioForward[item]["deviceName"]
                                        chName = self.dioForward[item]["channel"]

                                        if self.locSpoof["on"].lower() == "on":

                                            if self.locSpoof["mode"].lower() == "forward":
                                                self.sendtodbLoc(ch, chName, self.currentDict[item], 0, deviceName, self.locSpoof["mac"])
                                            elif self.locSpoof["mode"].lower() == "copy":
                                                self.sendtodbLoc(ch, chName, self.currentDict[item], 0, deviceName, self.locSpoof["mac"])
                                                self.sendtodb(item, self.currentDict[item], 0)
                                        else:
                                            self.sendtodbDev(ch, chName, self.currentDict[item], 0, deviceName)
                                    else:
                                        self.sendtodb(item, self.currentDict[item], 0)
                                except:
                                    pass
                        except Exception, e:
                            print e
                    if self.sync == True:
                        self.sync = False
                    self.last.update(self.currentDict)
                    time.sleep(.5)

                    #check geo fences and signal strength 
                    gps = self.mcu.gps
                  
                    try:
                        lat1 = self.last_gps.split(",")[0]
                        long1 = self.last_gps.split(",")[1]
                        lat2 = gps.split(",")[0]
                        long2 = gps.split(",")[1]
                        distance_traveled = self.mcu.distanceBetween(long1, lat1, long2, lat2)
                    except:
                        distance_traveled = 0

                    if (gps != self.last_gps and abs(time.time() - self.last_gps_time) > 43200) or distance_traveled > 0.0625:
                        if gps != "0.0,-0.0":
                            self.last_gps = gps
                            self.last_gps_time = time.time()
                            self.sendtodb("gps", gps, 0)
                    try:
                        try:
                            if self.mcu.FLY == True:
                                if (time.time() - self.last_xbee_sig_time) > 3600:
                                    self.sendtodb("signal", "0", 0)
                                    self.last_xbee_sig_time = time.time()
                        except:
                            print "not a fly"
                        else:
                            signal = self.mcu.signal
                            if signal is not None:
                                if abs(int(self.last_signal) - int(signal)) > 5:
                                    signalCal = (int(signal) + 8)
                                    self.sendtodb("signal", str(signalCal), 0)
                                    self.last_signal = int(signal)
                    except Exception,e:
                        print "error with signal"
                        print e
                        signal = self.mcu.signal
                        if signal is not None:
                            if abs(int(self.last_signal) - int(signal)) > 5:
                                signalCal = (int(signal) + 8)
                                self.sendtodb("signal", str(signalCal), 0)
                            self.last_signal = int(signal)

                    if len(gps) > 6:

                        for geoTag in self.geoData:
                            lat1 = self.geoData[geoTag]["lat"]
                            long1 = self.geoData[geoTag]["long"]
                            lat2 = gps.split(",")[0]
                            long2 = gps.split(",")[1]

                            distance = self.mcu.distanceBetween(long1, lat1, long2, lat2)
                            if distance > float(self.geoData[geoTag]["distance"]):
                                if self.geoData[geoTag]["alarm"] != "out":
                                    self.geoData[geoTag]["alarm"] = "out"
                                    self.sendtodb("geo_a1", "out", 0)
                            else:
                                if self.geoData[geoTag]["alarm"] != "in":
                                    self.geoData[geoTag]["alarm"] = "in"
                                    self.sendtodb("geo_a1", "in", 0)
                    
            except Exception, e:
                print "in M1"
                print e

    def changeDeviceAddress(self, new):
        with self.lock:
            try:
                for com in self.modbusMap:
                    for address in self.modbusMap[com]["addresses"]:
                        if int(new) != int(address):
                            #this is one we need to repace
                            #1. update all of the device address fields
                            #2. copy the object and replace it back with the correct device address in the main object
                            for chName in self.modbusMap[com]["addresses"][address]:
                                self.modbusMap[com]["addresses"][address][chName]['da'] = str(new)
                            newObj = copy.deepcopy(self.modbusMap[com]["addresses"][address])
                            #attach the copy at the new address
                            self.modbusMap[com]["addresses"][str(new)] = newObj
                            #delete the old object
                            del self.modbusMap[com]["addresses"][address]
                            #update persistant dictionary
                            with open('/root/python_firmware/drivers/modbusMap.p', 'wb') as handle:
                                pickle.dump(self.modbusMap, handle)

            except Exception, e:
                print "error changing address"
                print e
                return "Error Changing Address"
        return True

    def genericSet(self, name, value, id, longId=None):


        if name.startswith("fwd-"):
            self.updateDIOForward(name, value)
            return True

        if "adrsetonboot" in name:
            #save this to a file
            if value == "On" or value == "on" or value == 1 or value == "1" or value == "true" or value == "True":
                val = True
            else:
                val = False

            #update persistant value
            with open('/root/python_firmware/drivers/adrsetonboot.p', 'wb') as handle:
                pickle.dump(val, handle)
            self.sendtodb(name, value, 0)
            return True

        if "deviceaddress" in name:
            print "found new device address"
            success = self.changeDeviceAddress(int(value))
            #hardcoded for flowco, need to adjust main.py to include more detials about which device this is
            self.sendtodbDev("01", "deviceaddress", value, 0, "poc")
            self.sendtodb("deviceaddress", value, 0)

            #update persistant value
            with open('/root/python_firmware/drivers/deviceaddress.p', 'wb') as handle:
                pickle.dump(int(value), handle)
 
            return success

        # Trigger for turning on modbus debugger. It is turned off after one modbus loop
        if "modbusdebug" in name:
            if value == "On" or value == "on" or value == 1 or value == "1" or value == "true" or value == "True":
                val = "On"
                self.modbus_logger.enable()
            else:
                val = "Off"
                self.modbus_logger.disable()

            self.sendtodb("modbusdebug",str(val),0)
            return True

        if "modbuswrite" in name or name == "modbuswrite" or "plcwrite" in name or name == "plcwrite":

            try:
                #[{"com":"1","device_address":"1","register_address":"0","values":[1]},{"com":"1","device_address":"1","register_address":"299","type":"32/16/coil","values":[256]}]
                # [{'com':'1','device_address":'1','register_address':'0','values':[1]}]
                newVal = value.replace("'", '"')
                newJson = json.loads(newVal)
                for set in newJson:
                    com = set["com"]
                    
                    try:
                        regAddress = set["register_address"]
                        device = int(set["device_address"])
                    except:
                        pass
                    try:
                        type = str(set["type"])
                    except:
                        type = False

                    values = set["values"]

                    with self.lock:
                        instrument = self.modbusInterfaces[self.modbusMap[com]["c"]]
                        if self.modbusMap[com]["c"] == "TCP":
                            instrument.execute(device, cst.WRITE_MULTIPLE_REGISTERS, int(regAddress), output_value=values)
                        elif self.modbusMap[com]["c"] == "ETHERNET/IP":
                            self.ethernetInstrument = ClxDriver()
                            self.ethernetInstrument.open(self.modbusMap[com]["b"])
                            instrument = self.ethernetInstrument
                            newLst = []
                            for i in values:
                                typeOfData = instrument.read_tag([str(i[0])])[0][2]
                                if 'INT' in typeOfData or 'BOOL' in typeOfData:
                                    newValue = int(str(i[1]))
                                #elif str(i[2]) == 'BOOL':
                                #    newValue = boot(int(i[1]))
                                else:
                                    newValue = float(str(i[1]))
                                newLst.append((str(i[0]),newValue,str( typeOfData  ) ))
                            print "new List"
                            print newLst
                            self.EthernetIPSET(instrument, com, newLst)
                                
                        elif len(values) == 1 and type == "16":
                            values = values[0]
                            instrument.write_register(int(regAddress), values, functioncode=6)
                            time.sleep(1)
                            newVal = instrument.read_register(int(regAddress))
                            thread.start_new_thread( self.modbusWriteCheckup, ( int(regAddress), newVal)) 
                        elif len(values) == 1 and type == "32":
                            values = float(values[0])
                            instrument.write_float(int(regAddress), values)
                            time.sleep(1)
                            newVal = instrument.read_float(int(regAddress))
                            thread.start_new_thread( self.modbusWriteCheckup, ( int(regAddress), newVal)) 
                        elif len(values) == 1 and type == "coil":
                            values = values[0]
                            instrument.write_bit(int(regAddress), int(values), functioncode=5)
                            time.sleep(1)
                            newVal = instrument.read_bit(int(regAddress), functioncode=int(1))
                            thread.start_new_thread( self.modbusWriteCheckup, ( int(regAddress), newVal)) 
                        elif len(values) == 1 and type == "long":
                            values = values[0]
                            instrument.write_long(int(regAddress), int(values))
                            time.sleep(1)
                            newVal = instrument.read_long(int(regAddress))
                            thread.start_new_thread( self.modbusWriteCheckup, ( int(regAddress), newVal)) 
                        else:
                            instrument.write_registers(int(regAddress), values)

                return True
            except Exception, e:
                print "modbus write error"
                print e
                if "The slave is indicating an error" in e:
                    e = "The slave is indicating an error, can't write regerister"
                return str(e)
            

        print "I'm at location 1"
        try:
            interfaces = ["2s","4s","6s","8s","10s","12s","14s","16s","18s","20s"]
            if name in interfaces:
                with self.lock:
                    print "I'm at location 2"
                    self.handleComSetup(name, value)

                    #update persistant dictionary
                    with open('/root/python_firmware/drivers/modbusMap.p', 'wb') as handle:
                        pickle.dump(self.modbusMap, handle)
                    
                    return True

            try:

                print "I'm at location 3"
                if name.split("-")[2] == 'v':
                    #this is a channel set, for future use
                    pass
            except:
                pass

            #2-1","value":"{'chn':'2-1-v','dn':'M1','le':'16','a':'301','f':'3','t':'int','la':null,'m':'none','mv':'1','ct':'number','c':'1','vm':null,'r':'1-200','s':'On'}"
            interfaces = ["2","4","6","8","10","12","14","16","18","20"]
            if name.split("-")[0] in interfaces:
                with self.lock:
                    success = self.handleModbusEntry(name, value)
                    #update persistant dictionary
                    with open('/root/python_firmware/drivers/modbusMap.p', 'wb') as handle:
                        pickle.dump(self.modbusMap, handle)
                    if success:
                        return True
                    else:
                        return False
        
            
        except Exception,e:
            print(str(e))
            return False


        if name.split("-")[0] == "a1" or name.split("-")[0] == "a2" or name.split("-")[0] == "a3" or name.split("-")[0] == "a4" or name.split("-")[0] == "cl" or name.split("-")[0] == "pls":
            try:
                value = float(value)
            except:
                return(" Value must be a float or integer")
            return self.processAnalog(name, value)
        #analog inputs (a1-4 and cloop) need 4 data points each set for calibration 
        #Volts Low that ties to Units Low
        #Volts hight that ties to Units High
        #if Volts are lower than low, ignore (set to lowest unit value). If Volts are higher than high, ignor (set to highest units value)
        #formula for displaying value: ((high units - low units) / (high volts - low volts) * (current reading - low volts)) + low units
        #high / low alarm matrix for digitl outputs and relay
        #sets from M1 to M1 with I/O mapping, probably dont need

    def modbusWriteCheckup(self, registerAddress, val):
        time.sleep(6)
        print "staring process of modbus ping back"
        print val, registerAddress

        for com in self.modbusMap:
            for address in self.modbusMap[com]["addresses"]:
                ch_un = address
                for chName in self.modbusMap[com]["addresses"][address]:
                    #time.sleep(1)
                    regAddress = str(self.modbusMap[com]["addresses"][address][chName]['a'])
                    print regAddress, registerAddress
                    if int(registerAddress) == int(regAddress):
                        print "we found our match for quick update of modbus write"
                        #see if it has the update for a unit number for each register, if not, use the device address
                        try:
                            unitNumber = int(str(self.modbusMap[com]["addresses"][address][chName]['un']))
                            ch = unitNumber
                        except:
                            ch = ch_un
                        if int(ch) < 10:
                            ch = "0" + str(ch)

                        deviceName = str(self.modbusMap[com]["addresses"][address][chName]['dn'])
                        functioncode = str(self.modbusMap[com]["addresses"][address][chName]['f'])
                        length = int(str(self.modbusMap[com]["addresses"][address][chName]['le']))
                        regAddress = str(self.modbusMap[com]["addresses"][address][chName]['a'])
                        type = str(self.modbusMap[com]["addresses"][address][chName]['t'])
                        last_val = self.modbusMap[com]["addresses"][address][chName]['la']
                        multiplier = str(self.modbusMap[com]["addresses"][address][chName]['m'])
                        try:
                            if multiplier != "function":
                                multiplierVal = float(self.modbusMap[com]["addresses"][address][chName]['mv'])
                            else:
                                multiplierVal = str(self.modbusMap[com]["addresses"][address][chName]['mv'])
                        except:
                            multiplierVal = 1
                        changeType = str(self.modbusMap[com]["addresses"][address][chName]['ct'])

                        m1Channel = str(self.modbusMap[com]["addresses"][address][chName]['m1ch']) + "-v"
                        channel = str(self.modbusMap[com]["addresses"][address][chName]['chn'])

                        

                        try:
                            min_time = int(self.modbusMap[com]["addresses"][address][chName]['mrt'])
                            last_time = int(self.modbusMap[com]["addresses"][address][chName]['lrt'])
                        except:
                            self.modbusMap[com]["addresses"][address][chName]['mrt'] = 60
                            self.modbusMap[com]["addresses"][address][chName]['lrt'] = 0
                            min_time = int(self.modbusMap[com]["addresses"][address][chName]['mrt'])
                            last_time = int(self.modbusMap[com]["addresses"][address][chName]['lrt'])

                        #see if there is a period in which you have to get a value, even if it hasn't changed
                        #sudo code: if (current time - last send time ) > period (and period is not None) send up new point
                        try:
                            period = int(self.modbusMap[com]["addresses"][address][chName]['grp'])
                            if period < 10:
                                period = None
                        except:
                            period = None

                        print "here is your period: ", period
                        print time.time() - last_time

                        
                        #load the value map
                        valueMap = self.modbusMap[com]["addresses"][address][chName]['vm']
                        try:
                            if len(valueMap.keys()) < 1:
                                valueMap = None
                        except:
                            valueMap = None

                        #check if there is a multiplier
                        if multiplier != None:
                            if multiplier == "divide":
                                val = round(float((float(val) / float(multiplierVal))), 2)
                            elif multiplier == "multiply":
                                val = round(float((float(val) * float(multiplierVal))), 2)
                            elif multiplier == "function":
                                x = float(val)
                                print str(multiplierVal)
                                try:
                                    val = eval(multiplierVal.replace("&", "'"))
                                    print "eval value: "
                                    print val
                                    try:
                                        val = float(val)
                                    except:
                                        type = "str"
                                except Exception, e:
                                    print e


                        
                        if valueMap != None:
                            try:
                                print "found Value map"
                                print valueMap
                                updateVal = valueMap[str(int(val))]
                                print "new Value", val
                            except:
                                updateVal = val

                            if deviceName != "M1":
                                if self.locSpoof["on"].lower() == "on":
                                    if self.locSpoof["mode"].lower() == "forward":
                                        self.sendtodbLoc(ch, channel, updateVal, 0, deviceName, self.locSpoof["mac"])
                                    elif self.locSpoof["mode"].lower() == "copy":
                                        self.sendtodbLoc(ch, channel, updateVal, 0, deviceName, self.locSpoof["mac"])
                                        self.sendtodb(m1Channel, updateVal, 0)
                                else:
                                    self.sendtodbDev(ch, channel, updateVal, 0, deviceName)
                                    self.sendtodb(m1Channel, updateVal, 0)
                            else:
                                self.sendtodb(m1Channel, updateVal, 0)
                        else:
                            if deviceName != "M1":
                                if self.locSpoof["on"].lower() == "on":
                                    if self.locSpoof["mode"].lower() == "forward":
                                        self.sendtodbLoc(ch, channel, val, 0, deviceName, self.locSpoof["mac"])
                                    elif self.locSpoof["mode"].lower() == "copy":
                                        self.sendtodbLoc(ch, channel, val, 0, deviceName, self.locSpoof["mac"])
                                        self.sendtodb(m1Channel, val, 0)
                                else:
                                    self.sendtodbDev(ch, channel, val, 0, deviceName)
                                    self.sendtodb(m1Channel, val, 0)
                            else:
                                self.sendtodb(m1Channel, val, 0)
                        self.modbusMap[com]["addresses"][address][chName]['la'] = val
                        self.modbusMap[com]["addresses"][address][chName]['lrt'] = time.time()


    def processAnalog(self, name, value):
        
        with self.analogLock:
            try:
                if name.split("-")[0] == "a1":
                    analogName = "analog1"
                elif name.split("-")[0] == "a2":
                    analogName = "analog2"
                elif name.split("-")[0] == "a3":
                    analogName = "analog3"
                elif name.split("-")[0] == "a4":
                    analogName = "analog4"
                elif name.split("-")[0] == "cl":
                    analogName = "cloop"
                elif name.split("-")[0] == "pls":
                    analogName = "pulse"

                chName = analogMap[name.split("-")[1]]

                self.analogData[analogName][chName] = float(value)

                #update persistant dictionary
                with open('/root/python_firmware/drivers/analogData.p', 'wb') as handle:
                    pickle.dump(self.analogData, handle)
                self.sendtodb(name, value, 0)
            except Exception, e:
                return str(e)

            return True

        pass

    def M1_vpnpf(self, name, value):
        #value = "1,8080,192.168.1.2,80"
        
        v = value.split(",")

        if v[1] == "del":
            self.vpn.delForward(1)
            return True
        else:
            number = v[0]
            port = v[1]
            ip = v[2]
            exPort = v[3]
            self.vpn.addForward(number, port, exPort, ip)
            self.vpnCheckUp()
            self.sendtodb("vpnpf", value, 0)
            return True



    def M1_vpn(self, name, value):
        try:
            #on,lewis@lewis.com,password,subnet,ip,domain
            values = value.split(",")
            if values[0] == "On" or values[0] == "on" or values[0] == 1 or values[0] == "1":
                self.vpn.turnOn("http://54.221.213.207:5000", values[1], values[2], self.mac, values[3], values[4], values[5])
            elif values[0] == "Off" or values[0] == "off" or values[0] == 0 or values[0] == "0":
                self.vpn.turnOff()

            time.sleep(30)
            self.vpnCheckUp()
            #remove the password from the list
            newValues = values[0] + "," + values[1] + "," + " " + "," + values[3] + "," + values[4]
            
              
            self.sendtodb("vpn", newValues, 0)
        except Exception,e:
            print(str(e))
            self.sendtodb("error", (str(e) + "  Most Likely Wrong Username and Password"), 0)
            return str(e)
        return True


    def M1_dout1(self, name, value):
        
        success = self.mcu.digitalOut1(str(value))
        if success:
            self.sendtodb(name, str(value), 0)

            #return True/False
        return success

    
        
    def M1_dout2(self, name, value):
        success = self.mcu.digitalOut2(str(value))
        if success:
            self.sendtodb(name, str(value), 0)

        #return True/False
        return success

    def M1_dout3(self, name, value):
        success = self.mcu.digitalOut3(str(value))
        if success:
            self.sendtodb(name, str(value), 0)

        #return True/False
        return success
    
    def M1_dout4(self, name, value):
        success = self.mcu.digitalOut4(str(value))
        if success:
            self.sendtodb(name, str(value), 0)

        #return True/False
        return success
        
    def M1_dout5(self, name, value):
        success = self.mcu.digitalOut5(str(value))

        if success:
            self.sendtodb(name, str(value), 0)

        #return True/False
        return success

   
        
    def M1_relay2(self, name, value):
        success = self.mcu.relay2(value)

        if success:
            self.sendtodb(name, str(value), 0)

        #return True/False
        return success


    
    def M1_relay1(self, name, value):
        success = self.mcu.relay1(value)

        if success:
            self.sendtodb(name, str(value), 0)


            #return True/False
            return success
        else:
            return False

    def M1_reboot(self, name, value):
        self.sendtodb("log", "success rebooting", 0)
        time.sleep(5)
        os.system("reboot")

    def M1_geo1p(self, name, value):
        self.addGeo_point(1,value)
        self.sendtodb(name, value, 0)
        return True
       
    def M1_geo1d(self, name, value):
        self.addGeo_distance(1, value)
        self.sendtodb(name, value, 0)
        return True
    
    def M1_rs232baud(self, name, value):
        try:
            success = self.mcu.set232Baud(int(value))
            self.sendtodb("rs232baud", str(value), 0)
        except:
            success = False

        return success

    def M1_din2_fw(self, name, value):
        #update digital in 2 forwarding rules
        #"cloop":{"on":"off","deviceName":"M1","channel":"cloop","unitNum":"1"},
        data = value.split(",")

        self.dioForward["din2"]["on"] = data[0]
        self.dioForward["din2"]["deviceName"] = data[0]
        self.dioForward["din2"]["channel"] = data[0]
        self.dioForward["din2"]["unitNum"] = data[0]


    def updateDIOForward(self, name, value):
        data = value.split(",")
        name2 = name.split("-")[1]
        self.dioForward[name2]["on"] = data[0]
        self.dioForward[name2]["deviceName"] = data[1]
        self.dioForward[name2]["channel"] = data[2]
        self.dioForward[name2]["unitNum"] = data[3]

        #update persistant dictionary
        with open('/root/python_firmware/drivers/dioForward.p', 'wb') as handle:
            pickle.dump(self.dioForward, handle)

        self.sendtodb(name, value, 0)
        return True

    def M1_loc_change(self, name, value):
        data = value.split(",")
        if len(data) != 3:
            return "wrong number of values sent, must be exactly 3"
        { "on":"off","mode":"forward","mac":None}
        self.locSpoof["on"] = data[0].lower()
        self.locSpoof["mode"] = data[1].lower()
        self.locSpoof["mac"] = data[2].upper()
        #update persistant dictionary
        with open('/root/python_firmware/drivers/locSpoof.p', 'wb') as handle:
            pickle.dump(self.locSpoof, handle)

        self.sendtodb("loc_change", value, 0)
        return True
        
    def M1_rs232(self, name, value):

        self.mcu.rs232.write(str(value))

        return True

    def RS232Thread(self):

        while True:
            data = self.mcu.rs232.read()
            if len(data) > 2:
                self.sendtodb("rs232", str(data), 0)
            time.sleep(1)

    def get_eoln(self):
        eoln = SettingsBase.get_setting(self, "eoln")
        if eoln is None:
            return None
        
        if eoln != self.__eoln_save:
            # cache result to avoid repeat processing of escapes
            self.__eoln_save = eoln
            self._eoln = strip_escapes(eoln)
        return self._eoln
    
    def addGeo_distance(self, number, distance):
        #self.geoData = {
        #        1: {"lat":"342.3243,
        #             "long":"343.423",
        #            "distance":43
        #            }
        if self.geoData.has_key(int(number)):
            self.geoData[int(number)]["distance"] = float(distance)
        else:
            self.geoData[int(number)] = {"distance":"", "lat":"", "long":"", "alarm":""}
            self.geoData[int(number)]["distance"] = float(distance)

        #update persistant dictionary
        with open('/root/python_firmware/drivers/geoData.p', 'wb') as handle:
            pickle.dump(self.geoData, handle)
    
    def syncGeoTags(self):
        for number in self.geoData:
            self.sendtodb(("geo" + str(number) + "p"), (self.geoData[number]["lat"] + "," + self.geoData[number]["long"]), 0)
            self.sendtodb(("geo" + str(number) + "d"), (self.geoData[number]["distance"]), 0)

    def addGeo_point(self, number, point):
        #self.geoData = {
        #        1: {"lat":"342.3243,
        #             "long":"343.423",
        #            "distance":43
        #            }
        if self.geoData.has_key(int(number)):
            self.geoData[int(number)]["lat"] = point.split(",")[0]
            self.geoData[int(number)]["long"] = point.split(",")[1]

        else:
            self.geoData[int(number)] = {"distance":"", "lat":"", "long":"", "alarm":""}
            self.geoData[int(number)]["lat"] = point.split(",")[0]
            self.geoData[int(number)]["long"] = point.split(",")[1]

        #update persistant dictionary
        with open('/root/python_firmware/drivers/geoData.p', 'wb') as handle:
            pickle.dump(self.geoData, handle)

    def int32(self, x):
        if x>0xFFFFFFFF:
            raise OverflowError
        if x>0x7FFFFFFF:
            x=int(0x100000000-x)
            if x<2147483648:
                return -x
            else:
                return -2147483648
        return x
    
    def byteSwap32(self, array):
        #array is a list of 2 dec numbers
        newVal = ""
        for i in array:
            i = hex(i).replace('0x', '')
            while len(i) < 4:
                i = "0" + i
            print i
            newVal = i + newVal 
        print newVal
        return struct.unpack('!f', newVal.decode('hex'))[0]





    def byteArray(self, val, l=16, bs=False):
        val = ''.join(format(val, '02x'))
        val = str(val)
        while len(val) < (l/4):
            val = "0" + val
        if bs:
            val = val[(len(val)/2):] + val[:(len(val)/2)]
        print val
        bitStr = bin(int(val, base=16)).replace('0b', '')[::-1]
        while len(bitStr) < l:
            bitStr =  bitStr + "0"
        print bitStr
        return bitStr

    def M1_fileloc(self, name, value):
        #@root@python_firmware@main.py,@root@python_firmware@main.py
        try:
            spiderFile = value.split(",")[0]
            flyFile = value.split(",")[1]
            self.flyFileLocation = flyFile.replace("@", "/")
            self.sendtodb("log", "starting file transfer", 0)
            
            #wait for the data to send, then wait a little more
            thread.start_new_thread(self.waitforq, (spiderFile,))
           
        except Exception,e:
            print e

    def waitforq(self, spiderFile):
        print "starting to wait"
        while self.q.qsize() > 0:
            print "This is the size of the Q"
            print self.q.qsize()
            time.sleep(3)
        print "ending long wait"
        self.sendtodb("startfile", spiderFile, 0)
        time.sleep(15)
        self.M1_getfile('n','n')


    def M1_uartsoc(self, name, value):
        #on,ip,port
        on = value.split(",")[0]
        ip = value.split(",")[1]
        port = value.split(",")[2]

        if on.lower() == "on":
            #clear old thread if its running:
            self.runUartSocket = False
            time.sleep(5)
            self.runUartSocket = True
            thread.start_new_thread(self.startUartSoc, (ip, port))
        else:
            self.runUartSocket = False

        return True

    def startUartSoc(self, ip, port):
        print "thread started for socket"
        self.mcu.xbee.fileTransfer = True
        while self.runUartSocket:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                server_address = (ip, int(port))
                sock.connect(server_address)
                try:
                    while self.runUartSocket:
                        data = self.mcu.xbee.read()
                        if data != "":
                            print "sending data"
                            sock.sendall(data)
                            time.sleep(1)
                        else:
                            time.sleep(2)
                except Exception, e:
                    print e
                    time.sleep(5)
            except Exception, e:
                print e
                time.sleep(5)

        self.mcu.xbee.fileTransfer = False

    def M1_getfile(self, name, value):

        self.mcu.xbee.fileTransfer = True
        #clear xbee
        self.mcu.xbee.read()
        modem = XMODEM(self.getc, self.putc)
        stream = file('/tmp/output', 'wb')
        try:
            success = (modem.recv(stream, retry=60))
        except Exception,e:
            self.mcu.xbee.fileTransfer = False
            print e
            success = None
        print success
        self.mcu.xbee.fileTransfer = False
        if success != None:
            stream.close()
            f = open("/tmp/output", "rb")
            data = f.read()
            data = zlib.decompress(data)
            f.close()
            final = open(self.flyFileLocation, "wb")
            final.write(data)
            final.close()
            self.sendtodb("log", "file trasfer success", 0)
        else:
            self.sendtodb("log", "file transfer failed", 0)

    def getc(self, size, timeout=300):
        timeout = timeout * 10
        data = self.lastData
        count = 0
        while len(data) < size:
            count += 1
            time.sleep(.1)
            data += self.mcu.xbee.read()
            if count > timeout and len(data) == 0:
                    return None
            elif count > timeout:
                self.lastData = ""
                return data
        sndData = data[0:size]
        self.lastData = data[size:]
        print "here is the data  ", sndData
        return sndData

    def putc(self, data, timeout=10):
        self.mcu.xbee.write(data)
        return len(data)

    def process_pulses(self, pulses, multiplier):

        #load stored pulse data if we don't have any pulse data
        if self.pulses is None:
            try:
                with open('/root/python_firmware/drivers/pulses.p', 'rb') as handle:
                    self.pulses = pickle.load(handle)
                print "found pickled pulses Data"
                print self.pulses
            except:
                print "couldn't load pulses from pickle"
                self.pulses = {"tr":0,"lr":0}


        #grab the initial usage and add it to the other saved totals totals
        
        try:
                
                
                #determine how much to add to the total
                if self.pulses["lr"] <= pulses:
                    print "pulses increased"
                    #add the amount it increased to the total
                    self.pulses["tr"] += (pulses - self.pulses["lr"])
                else:
                    #on level decreasing, we can assume the modem has reset, so add all of the data up until now
                    self.pulses["tr"] += pulses
                    
                #replace last known amount with new one
                self.pulses["lr"] = pulses


                val = str(int(self.pulses['tr']) * multiplier)


                item = "pulse"
                if self.dioForward[item]["on"].lower() == "on":
                    ch = self.dioForward[item]["unitNum"]
                    deviceName = self.dioForward[item]["deviceName"]
                    chName = self.dioForward[item]["channel"]

                    if self.locSpoof["on"].lower() == "on":

                        if self.locSpoof["mode"].lower() == "forward":
                            self.sendtodbLoc(ch, chName, val, 0, deviceName, self.locSpoof["mac"])
                        elif self.locSpoof["mode"].lower() == "copy":
                            self.sendtodbLoc(ch, chName, val, 0, deviceName, self.locSpoof["mac"])
                            self.sendtodb(item, val, 0)
                    else:
                        self.sendtodbDev(ch, chName, val, 0, deviceName)
                        self.sendtodb(item, val, 0)
                else:
                    self.sendtodb(item, val, 0)
                
                #self.sendtodb("pulse", val, 0)
                        
                #I need pulse multiplier 

                #don't write to flash too often, it will wear the flash out!!
               
                #update persistant dictionary
                with open('/root/python_firmware/drivers/pulses.p', 'wb') as handle:
                    pickle.dump(self.pulses, handle)




        except Exception, e:
            print "error pulses"
            print e
            time.sleep(60)



        #add up totals and keep for persistance 


    def get_network_bytes(self):

        #load stored 3g usage data

        try:
            with open('/root/python_firmware/drivers/3G_usage.p', 'rb') as handle:
                self.usageData = pickle.load(handle)
            print "found pickled 3g usage Data"
            print self.usageData
        except:
            print "couldn't load 3g usage from pickle"
            self.usageData = {"lr":0,"lt":0,"tr":0,"tt":0}

        interface= "3g-3g"

        #grab the initial usage and add it to the other saved totals totals
        count = 240
        writeCount = 20
        while True:
            count += 1
            writeCount += 1
            try:
                
                for line in open('/proc/net/dev', 'r'):
                    if interface in line:
                        data = line.split('%s:' % interface)[1].split()
                        rx_bytes, tx_bytes = (data[0], data[8])
                        rx = float(rx_bytes) / 1000
                        tx = float(tx_bytes) / 1000

                        #determine how much to add to the total
                        if self.usageData["lr"] <= rx:
                            print "data received increased"
                            #add the amount it increased to the total
                            self.usageData["tr"] += (rx - self.usageData["lr"])
                        else:
                            #on level decreasing, we can assume the modem has reset, so add all of the data up until now
                            self.usageData["tr"] += rx
                            self.usageData["lr"] = rx
                            continue
                        #replace last known amount with new one
                        self.usageData["lr"] = rx

                        #determine how much to add to the total
                        if self.usageData["lt"] <= tx:
                            print "data sent increased"
                            #add the amount it increased to the total
                            self.usageData["tt"] += (tx - self.usageData["lt"])
                        else:
                            self.usageData["tt"] += tx
                            self.usageData["lt"] = tx
                            continue
                        #replace last known amount with new one
                        self.usageData["lt"] = tx

                        if count > 240:
                            count = 0
                            self.sendtodb("rx", str(self.usageData['tr']), 0)
                            self.sendtodb("tx", str(self.usageData['tt']), 0)
                            self.sendtodb("rxtx", str(self.usageData['tr']  + self.usageData['tt']  ), 0)
                        
                        #don't write to flash too often, it will wear the flash out!!
                        if writeCount > 10:
                            writeCount = 0
                            #update persistant dictionary
                            with open('/root/python_firmware/drivers/3G_usage.p', 'wb') as handle:
                                pickle.dump(self.usageData, handle)
                        time.sleep(60)




            except Exception, e:
                print "error in 3g data usage"
                print e
                time.sleep(60)



        #add up totals and keep for persistance 

    def M1_cutoff(self, name, value):

        if value == "True" or value == "true" or value == "on" or value == "On" or value == "1" or value == 1:
            self.mcu.cutAllDataOff = True
        else:
            self.mcu.cutAllDataOff = False

        return True
    def M1_setmask(self, name, value):
        mask = value
        #lets do some simple validation:
        ip = ip.strip()
        test = ip.split(".")
        if len(test) == 4:
            for i in test:
                if int(i) < 256:
                    continue
                else:
                    return False
            cmd = "/sbin/uci get network.lan.netmask=" + mask
            os.system(cmd)
            os.system("/sbin/uci commit network")
            os.system("/sbin/ifup lan")
            self.sendtodb("setmask", mask, 0)
            return True
        else:
            return False
        

    def M1_setip(self, name, value):
        ip = value
        #lets do some simple validation:
        ip = ip.strip()
        test = ip.split(".")
        if len(test) == 4:
            for i in test:
                if int(i) < 256:
                    continue
                else:
                    return False
            cmd = "/sbin/uci set network.lan.ipaddr=" + ip
            os.system(cmd)
            os.system("/sbin/uci commit network")
            os.system("/sbin/ifup lan")
            self.sendtodb("setip", ip, 0)
            return True
        else:
            return False


