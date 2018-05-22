import os
import time


print "starting"

errorCount = 0

def check_pid(pid):        
    """ Check For the existence of a unix pid. """
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    else:
        return True

def checkPing():
    time.sleep(15)
    ping = os.popen("/bin/ping google.com -c 1")
    ping = ping.readlines()
    try:
        if int(ping[4].split('%', 1)[0][-2:]) > 0:
            print "ping had errors"
            return False
        else:
            print "connected"
            return True
    except:
        print "error, probably not online"
        return False

while True:
    
    time.sleep(3600)
    if errorCount > 2:
        t = time.time()
        with open("/root/log.txt", "a") as myfile:
            myfile.write("reset from 2 or more errors: " + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t)) + chr(13))
        os.system("/root/reboot")
    
    file = open('/root/main.pid', 'r')
    pid = file.read()
    try:
        pid = int(pid)
        
        running = check_pid(pid)
        if running:
            print "Main.py is Running"
           
        else:
            print "Main.py is NOT Running"
            t = time.time()
            with open("/root/log.txt", "a") as myfile:
                myfile.write("reset from no Main.py running: " + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t)) + chr(13))
            os.system("/root/reboot")
    except:
        try:
            errorCount += 1
        except:
            t = time.time()
            with open("/root/log.txt", "a") as myfile:
                myfile.write("reset from no Main.py running: " + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t)) + chr(13))
            os.system("/root/reboot")

    

    

    tries = 0
    connected = False
    while tries < 10:
        time.sleep(15)
        try:
            file = open('/root/SAT', 'r')
            sat = file.read()
            if sat.strip().lower() == "true" or sat.strip() == "True":
                print "connected to SATs, don't do ping test"
                connected = True
                break
        except:
            print "couldn't open file"
        tries += 1
        connected = checkPing()
        if connected:
            print "connected"
            break
        else:
            print "not connected, trying again"
            continue

    if not connected:
        print "not connected"
        t = time.time()
        with open("/root/log.txt", "a") as myfile:
            myfile.write("reset from no internet: " + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t)) + chr(13))
        os.system("/root/reboot")
        
    
    
    
