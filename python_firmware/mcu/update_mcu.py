#from subprocess import call
import os
import time

def update_mcu(filename):
    try:
        os.system("/root/mcu2boot")
    except:
        pass
    time.sleep(5)
  
    cmd = "stm32flash -w " + filename + " -v -g 0x0 /dev/ttyUSB1"
    return_code = "1"
    try:
        os.system(cmd)
        #return_code = call(cmd, shell=True)
    except Exception,e:
        return str(e)
    print return_code
    if return_code == 0 or return_code == "0":
        print "it worked"
        success = True
    else:
        print "it failed maybe"
        success = False

    try:
        os.system("/root/mcu2reset")
    except:
        pass

    return success
