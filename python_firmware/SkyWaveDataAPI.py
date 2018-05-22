import array
import serial
import time
import thread
import threading
import os
import binascii


class skywave():

    def __init__(self, setCallback, mac, state, Q, mcu):
        self.q = Q
        self.mcu = mcu
        self.sets = setCallback
        self.mac = mac
        self.lock = threading.Lock()
        self.updateState = state
        self.SAT_COM, self.reconnecting = self.updateState()
        

        line = self.mac
        n = 2
        macList = [line[i:i+n] for i in range(0, len(line), n)]
        self.zigMac = ""
        for i in macList:
            self.zigMac = self.zigMac + i.lower() + ":"

        #wait 15 seconds to make sure the 3g didn't work
        time.sleep(15)
        self.SAT_COM, self.reconnecting = self.updateState()
        self.conType = None
        while self.SAT_COM == False and self.reconnecting == True:
            self.SAT_COM, self.reconnecting = self.updateState()
            self.conType = self.connectSerail()
            if self.conType != None:
                break
        try:
            self.ser.open
            time.sleep(2)

            self.ser.flushInput() #flush input buffer, discarding all its contents
            self.ser.flushOutput()#flush output buffer, aborting current output
        
            #start the listening thread
            thread.start_new_thread(self.run, ())

            #while SAT_COM == False and reconnection == True do a handshake every few hours until something changes, either 3g comes back or you connect to the sats
            while self.SAT_COM == False and self.reconnecting == True:
                print "sending handshake"
                print "SAT COM is"
                print self.SAT_COM
                time.sleep(3)
                self.handshake()
                time.sleep(3)
                time.sleep(600)
                self.SAT_COM, self.reconnecting = self.updateState()

            print "handshake done"
            print self.SAT_COM
            print self.reconnecting
        except:
            pass

        

        
    def handshake(self):
        data = "hs:" + self.mac
        self.send(data)

    def connectSerail(self):
        if self.conType != None:
            try:
                self.ser.close()
            except:
                pass
        try:
            self.ser = serial.Serial(port='/dev/ttyS20', baudrate=9600, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, xonxoff=False, timeout=1, rtscts=False, dsrdtr=False)
            self.ser.write('ATE0' + chr(13))
            print "connected on ttsyS2"
            return "232"
        except:
            try:
                self.ser = serial.Serial(port='/dev/ttyUSB10', baudrate=9600, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, xonxoff=False, timeout=1, rtscts=False, dsrdtr=False)
                self.ser.write('ATE0' + chr(13))
                print "connected on USB0"
                return "232"
            except:
                try:
                    #set up rs232 for link to DeapSea
                    ans = False
                    #make sure the baud rate gets set
                    while ans == False:
                        ans = self.mcu.set232Baud(9600)
                        time.sleep(1)
                    self.ser = self.mcu.rs232
                    print "connected on M1 rs232"
                    time.sleep(1)
                    self.ser.write('ATE0' + chr(13))
                    return "M1"
                except:
                    print "couldn't connect to com port for the SAT connection, retrying in 10 sec"
                    time.sleep(10)
                    return None
        
    def send(self, input):
        with self.lock:
            #clear completed messages
            self.ser.read(512)
            self.ser.write("AT%MGRS" + chr(13))
            time.sleep(2)
            resp = self.ser.read(512)
            print "232 response:"
            print resp
            if resp == "":
                print "reseting 232 interface in send"
                self.connectSerail()
                #self.mcu.rs232reset()
                #self.mcu.set232Baud(9600)
            msg = '"AT%MGRT=' + ('"%s",2,129.1,1,"%s"' % (str(binascii.b2a_hex(os.urandom(4))), input))
            self.ser.write(msg + chr(13))
            time.sleep(2)
            
        #with self.lock:
         #   input = makePacket(str(input))
         #
          #  #print type(input)
          
          #  clear = '04'
          #  self.ser.write(clear.decode("hex"))
          #  time.sleep(1)
          #  self.ser.write(input.decode("hex"))
          #  time.sleep(2)


    def passToSets(self, msg):
        #[{"user":"demo@meshify.com","mac":"000CE373293D","company":"188","payload":{"name":"wipom_[00:0c:e3:73:29:3d:00:21]!.do2","value":"1","expires":"1389369695"},"msgId":4478}]
        
        #i need msg id and name and value
        #short version will be like this: deviceName/last4ofTech/channel/value/msgid
        #the above would be: wipom/0021/do2/1/9898
        #build the full name back:
        m = msg.split('/')
        if m[0] == "main":
            name = m[0] + "." + m[2]
        else:
            name = m[0] + "_[" + self.zigMac + m[1][0:2] + ":" + m[1][2:4] + "]!." + m[2]
        
        #now build the json back:
        j = '[{"user":"demo@meshify.com","mac":"%s","company":"1","payload":{"name":"%s","value":"%s","expires":"1389369695"},"msgId":"%s"}]' % (self.mac, name, m[3], m[4])
        thread.start_new_thread(self.sets, (j,))
        pass

    def run(self):
        #sleep for 30 seconds on start
        time.sleep(30)
        #if reconnecting is False, then we are back on 3g, so kill this thread
        while self.reconnecting == True:
            self.SAT_COM, self.reconnecting = self.updateState()
            time.sleep(1)
            print "sat looping again"
            try:
                try:
                    val = self.q.get(block=False, timeout=1)
                except Exception,e:
                    print "####################"
                    print "did't get from sat Q"
                    print e
                else:
                    print "here is the sat Item"
                    print val
                    #val[0] = topic val[1] = json val[2] = qos
                    # meshify/db/188/000CE373293D/wipom_[00:0c:e3:73:29:3d:00:21]!/ai1
                    #[ { "value":"0", "timestamp":"1422962934" } ]

                    #send format will be: deviceName/last4ofTech/channel/value
                    #example: wipom/0021/do2/1

                    #response: value/id

                    if val[0].split('/')[1] == "responses":
                        value = eval(val[1])[0]['value']
                        id = eval(val[1])[0]['msgId']
                        data = str(value) + "/" + str(id)
                    else:
                        a = val[0].split('/')
                        channel = a[5]
                        deviceName = a[4].split('_')[0]
                        last4 = a[4].split('_')[1].replace(':', '').replace(']!', '')[-4:]
                        val = eval(val[1])[0]['value']
                        data = deviceName + "/" + str(last4) + "/" + channel + "/" + str(val)

                    print "sending up data"
                    print data
                    self.send(data)

                    pass
                with self.lock:
                    
                    
                    #clear out the read data
                    self.ser.read(512)

                    self.ser.write("AT%MGFN" + chr(13))
                    time.sleep(2)
                    h = self.ser.read(512)
                    print "232 response:"
                    print h
                    if h == "":
                        print "reseting 232 interface in main loop"
                        self.connectSerail()
                        #self.mcu.rs232reset()
                        #self.mcu.set232Baud(9600)
                        continue

                    h = h.replace("\r\n%MGFN: ", "")
                    h = h.replace("\r\n\r\nOK\r\n", "")
                    h = h.split("\r\n")
                    lst = []
                    for i in h:
                        lst.append(i.split(",")[0].replace('"', ""))

                    for item in lst:
                        #clear out data line
                        self.ser.read(512)
                        self.ser.write('AT%MGFG="' + item + '",1' + chr(13))
                        time.sleep(2)
                        str1 = self.ser.read(512)
                        print "232 response:"
                        print str1
                        if str1.split(",")[3] == "129":
                            print "we have a match"
                            msg = str1.split(",")[7].split('"')[1].replace("\\01", "")
                            if msg == 'reg':
                                thread.start_new_thread(self.handshake, ())
                            else:
                                thread.start_new_thread(self.passToSets, (msg,))

                    """
                    response = self.ser.read(2048)
                    #print response
                    try:
                        line = response.encode('hex')
        
        
                        #print line
                        lst = makeList(line)
    
                        for i in lst:
                            i = unEscape(i)
                           # print i
                            if i[8:12] == "d507":
                                #print "we have a new message!!"
                                #print "the length is:"
                                l = int(('0x' + i[36:40]), 16)
                                #print l
                                print "message is:"
                                msg = i[40: (40 + (l * 2))]
                                print msg.decode("hex")
                                if msg.decode("hex") == 'reg':
                                    self.handshake()
                                else:
                                    self.passToSets(msg.decode("hex"))"""
        
        
        
                   
        
            except Exception,e:
                print "####################"
                print e
                print "big loop failed on Sat RUN"
        self.send('unreg')



def makePacket(msg):
    #this function takes in any ascii string and packages it into a hex string to be sent to the modem, it returns a string of hex characters
    print"making message"
    print msg
    hexstr = '0x03'
    #first get crc
    #the length of the message will be the length of the message + 4 bytes
    
    msgLen = len(msg)
    msgLen = format(msgLen, '#06x')
    msgLen = str(msgLen)
    msgPart1 = msgLen[:4]
    msgPart2 = '0x' + msgLen[-2:]
    #print msgPart1, msgPart2
    
    packetLen = len(msg) + 22
    #print packetLen
    packetLen = format(packetLen, '#06x')
    packetLen = str(packetLen)
    part1 = packetLen[:4]
    part2 = '0x' + packetLen[-2:]
    sum1 = 0x03 + int(part1, 16) + int(part2, 16) + 0xC5 + 0xC2 + 0x00 + 0x00 + 0x00 + 0x00 + 0xC0 + 0x00 + 0x00 + 0x00 + 0x00 + 0x02 + 0x58 + 0x00 + 0x00 + 0x00 + 0x00 + 0x00 + 0x00 + 0x00 + int(msgPart1, 16) + int(msgPart2, 16)
    #print sum1
    #print part1, part2
    packetLen = packetLen.replace('0x', '')
    #print packetLen
    sum2 = 0x00
    for i in array.array('B', msg):
        char = hex(i)
        #print char
        sum2 += int(char, 16)
    crc = 0xFFFF - (sum1 + sum2)
    #print crc
    #print hex(crc)
    list = '03' + part1.replace('0x', '') + part2.replace('0x', '') + 'c5c200000000c000000000025800000000000000' + msgPart1.replace('0x', '') + msgPart2.replace('0x', '')
    #print list
    for i in array.array('B', msg):
        char = str(hex(i)).replace('0x', '')
        list += char
    list += str(format(crc, '#06x')).replace('0x', '')
    #here are data is complete without the beginning 01 and end 04, so we can escape characters now
    list = escape(list)
    list = '01' + list + '04'
    #print list
    return list



def escape(line):
    #escape characters
    n = 2
    line = [line[i:i+n] for i in range(0, len(line), n)]
    #print line
    for i in range(len(line)):
        
        if line[i] == "01":
            line[i] = "1021"
    
        elif line[i] == "04":
            line[i] = "1024"
 
        elif line[i] == "10":
            line[i] = "1030"
  
        elif line[i] == "11":
            line[i] = "1031"

        elif line[i] == "13":
            line[i] = "1033"



    newData = ""
    #print line
    for i in line:
        #print i
        newData += str(i)
    
    #print "here is the new list"
    #print newData
    return newData

def unEscape(line):
    #unescape characters
    n = 2
    line = [line[i:i+n] for i in range(0, len(line), n)]
    #print line
    for i in range(len(line)):
        if line[i] == "10":
            #print "found a 10"
            if line[i + 1] == "21":
                line[i] = "01"
                line[i + 1] = ""
            elif line[i + 1] == "24":
                line[i] = "04"
                line[i + 1] = ""
            elif line[i + 1] == "30":
                line[i] = "10"
                line[i + 1] = ""
            elif line[i + 1] == "31":
                line[i] = "11"
                line[i + 1] = ""
            elif line[i + 1] == "33":
                line[i] = "13"
                line[i + 1] = ""
    newData = ""
    #print line
    for i in line:
        #print i
        newData += str(i)
    
    #print "here is the new list"
    #print newData
    return newData


def makeList(line):
    lst = []
    #here we will take in a bunch of serial data and make a list of individual responses from the modem
    n = 2
    line = [line[i:i+n] for i in range(0, len(line), n)]
    localLine = ""
    for i in line:
        localLine += i
        if i == "04":
            lst.append(localLine)
            localLine = ""
    return lst


"""
#sum1 = (0x03 + 0x00 + 0x1b + 0xC5 + 0xC2 + 0x00 + 0x00 + 0x00 + 0x00 + 0xC0 + 0x00 + 0x00 + 0x00 + 0x00 + 0x02 + 0x58 + 0x00 + 0x00 + 0x00 + 0x00 + 0x00 + 0x00 + 0x00 + 0x00 + 0x05 + 0x68 + 0x65 + 0x6c + 0x6c + 0x6f )

#crc = 0xfb27
#input = '01030006C682102105103020FE7804'

#print type(input)

input = makePacket('lewis is cool')

print type(input)

#input = '0103001bc5c200000000c000000000025800000000000000000568656c6c6ffb2704'

#data = data.decode('hex')

#for i in array.array('B', "hello")

ser = serial.Serial(port='/dev/tty.usbserial', baudrate=9600, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, xonxoff=False, timeout=2, rtscts=False, dsrdtr=False, interCharTimeout=.05)
ser.open
time.sleep(2)

ser.flushInput() #flush input buffer, discarding all its contents
ser.flushOutput()#flush output buffer, aborting current output

#ser.sendBreak(duration=0.25)
#time.sleep(1)
#ser.write(input.decode("hex"))
#print "sending",input.decode("hex")
clear = '04'
ser.write(clear.decode("hex"))
time.sleep(1)

ser.write(input.decode("hex"))
time.sleep(2)

while True:
    time.sleep(1)
    response = ser.read(2048)
    print response
    try:
        line = response.encode('hex')
        
        
        print line
        lst = makeList(line)
    
        for i in lst:
            i = unEscape(i)
            print i
            if i[8:12] == "d507":
                print "we have a new message!!"
                print "the length is:"
                l = int(('0x' + i[36:40]), 16)
                print l
                print "message is:"
                msg = i[40: (40 + (l * 2))]
                print msg.decode("hex")

        
        
        
    except:
        print "didn't work on hex :("
ser.close()


"""

















