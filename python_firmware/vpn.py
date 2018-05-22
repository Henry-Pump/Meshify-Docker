import socket
import fcntl
import struct
import os
import time
import pickle
import requests
import json
import sys
import subprocess
#this class will have methods for adding port forwarding, saving the port forward, deleting the port forward, turning the VPN on/off

"""
iptables -t nat -I PREROUTING -p tcp --dport 80 -j DNAT --to 192.168.1.2:80
iptables -I FORWARD -p tcp -d 192.168.1.2 --dport 80 -j ACCEPT
iptables -t nat -I POSTROUTING -j MASQUERADE

"""


class vpn():

    def __init__(self):

        try:
            with open('/root/python_firmware/drivers/portsJSON.p', 'rb') as handle:
                self.forwardingMap = pickle.load(handle)
                
            print "found pickled dictionary"
            print self.forwardingMap
        except:
            print "couldn't load devices from pickle"
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

    def delForward(self, number):


        string1 = "iptables -t nat -D PREROUTING -p tcp --dport %s -j DNAT --to %s:%s" % (str(self.forwardingMap[str(number)]["port"]), str(self.forwardingMap[str(number)]["externalIP"]), str(self.forwardingMap[str(number)]["externalPort"]))
        #string2 = "iptables -I FORWARD -p tcp -d %s --dport %s -j ACCEPT" % (str(ip), str(port))
        #string3 = "iptables -t nat -I POSTROUTING -j MASQUERADE"
        os.system(string1)
        #time.sleep(1)
        #os.system(string2)
        #time.sleep(1)
        #os.system(string3)

        self.forwardingMap[str(number)]["port"] = ""
        self.forwardingMap[str(number)]["externalPort"] = ""
        self.forwardingMap[str(number)]["externalIP"] = ""

        with open('/root/python_firmware/drivers/portsJSON.p', 'wb') as handle:
            pickle.dump(self.forwardingMap, handle)

            print "you are here"




    def addForward(self, number, port, exPort, ip):
        string1 = "iptables -t nat -I PREROUTING -p tcp --dport %s -j DNAT --to %s:%s" % (str(port), str(ip), str(exPort))
        string2 = "iptables -I FORWARD -p tcp -d %s --dport %s -j ACCEPT" % (str(ip), str(port))
        string3 = "iptables -t nat -I POSTROUTING -j MASQUERADE"
        os.system(string1)
        time.sleep(1)
        os.system(string2)
        time.sleep(1)
        os.system(string3)

        os.system("iptables -I INPUT -j ACCEPT")
        os.system("iptables -I FORWARD -j ACCEPT")
        os.system("iptables -I OUTPUT -j ACCEPT")

        self.forwardingMap[str(number)]["port"] = str(port)
        self.forwardingMap[str(number)]["externalPort"] = str(exPort)
        self.forwardingMap[str(number)]["externalIP"] = str(ip)

        with open('/root/python_firmware/drivers/portsJSON.p', 'wb') as handle:
            pickle.dump(self.forwardingMap, handle)

    def turnOff(self):
        os.system("killall openvpn")

    def turnOn(self, url, username, password, mac, subnet, ip, domain):
        os.system("killall openvpn")
        time.sleep(5)
        self.get_vpn_config(url, username, password, mac, subnet, ip, domain)
        time.sleep(10)

        subprocess.call('cd /root/python_firmware/vpn_certs;/usr/sbin/openvpn /root/python_firmware/vpn_certs/vpn.conf &', shell=True)
    
        #txt = commands.getstatusoutput("cd /root/python_firmware/vpn_certs;/usr/sbin/openvpn /root/python_firmware/vpn_certs/vpn.conf &")
        #os.system("cd /root/python_firmware/vpn_certs;/usr/sbin/openvpn /root/python_firmware/vpn_certs/vpn.conf &")
            
    def get_ip_address(self, ifname):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            return socket.inet_ntoa(fcntl.ioctl(
                s.fileno(),
                0x8915,  # SIOCGIFADDR
                struct.pack('256s', ifname[:15])
            )[20:24])
        except:
            return "VPN Off"


    def run_command(self, command):
        p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        return iter(p.stdout.readline, b'')

    def get_vpn_config(self, url, username, password, mac, subnet, ip, domain):
        if url == "" or url == None:
            url = "http://54.221.213.207:5000"
        login_data = {
                'url':url,
                'username':username,
                'password':password,
                'mac':mac,
                'subnet':subnet,
                'ip':ip,
                'domain':domain
            }
        #SERVER = "http://54.196.172.36:5000"
        rootFilename = os.path.dirname(os.path.realpath(sys.argv[0])) + "/vpn_certs/"
        print "starting....."
        with requests.Session() as x:
            print login_data
            g = x.post((login_data['url'] + "/config"), data=json.dumps(login_data),
                    headers={"Content-Type": 'application/json'})
            print g
            res = json.loads(g.text)
        
        mac = login_data['mac']
        f = open((rootFilename + 'ca.crt'),'w')
        #print res['ca_crt']
        f.write(res['ca_crt'])
        f.close()

        filename = (rootFilename + "%s.crt") % (mac)
        f = open(filename,'w')
        #print res['client_crt']
        f.write(res['client_crt'])
        f.close() 

        filename = (rootFilename + "%s.key") % (mac)
        f = open(filename,'w')
        #print res['client_key']
        f.write(res['client_key'])
        f.close()

        f = open((rootFilename + 'vpn.conf'),'w')
        f.write(res['conf'])
        #print res['conf']
        f.close()
        return





