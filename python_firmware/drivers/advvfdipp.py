"""Driver for connecting Advanced VFD IPP to Meshify."""

import threading
from device_base import deviceBase
from Channel import Channel, write_tag
from Maps import adv_vfd_ipp_map as maps
from Scheduler import ScheduleRun
import json
import time

try:
    with open("persist.json", 'r') as persist_file:
        persist = json.load(persist_file)
except Exception:
    persist = {}

try:
    persist['last_schedule_history']
except KeyError:
    persist['last_schedule_history'] = {"id": -1}

_ = None

plc_ip_address = "10.20.4.36"


def reverse_map(value, map_):
    """Perform the opposite of mapping to an object."""
    for x in map_:
        if map_[x] == value:
            return x
    return None


channels = [
    Channel(plc_ip_address, "flowrate", "val_Flowmeter", "REAL", 5.0, 3600),
    Channel(plc_ip_address, "fluidlevel", "val_FluidLevel", "REAL", 10.0, 3600),
    Channel(plc_ip_address, "intakepressure", "val_IntakePressure", "REAL", 4.0, 3600),
    Channel(plc_ip_address, "intaketemperature", "val_IntakeTemperature", "REAL", 2.0, 3600),
    Channel(plc_ip_address, "tubingpressure", "val_TubingPressure", "REAL", 2.0, 3600),
    Channel(plc_ip_address, "pidcontrolmode", "sts_PID_Control", "STRING", _, 3600, map_=maps['pid_controlmode']),
    Channel(plc_ip_address, "wellstatus", "Device_Status_INT", "STRING", _, 3600, map_=maps['device_status']),
    Channel(plc_ip_address, "vfdfrequency", "PowerFlex755.val_SpeedFdbk", "REAL", 1.0, 3600),
    Channel(plc_ip_address, "flowtotal", "Flow_Total[0]", "REAL", 100.0, 3600),
    Channel(plc_ip_address, "energytotal", "Energy_Total[0]", "REAL", 100.0, 3600),
    Channel(plc_ip_address, "vfdcurrent", "PowerFlex755.val_OutCurrent", "REAL", 1.0, 3600),
    Channel(plc_ip_address, "downholesensorstatus", "Downhole_Sensor_Status_INT", "STRING", _, 3600, map_=maps['dh_sensor_status']),
    Channel(plc_ip_address, "fluidspecificgravity", "cfg_FluidSpecificGravity", "REAL", 0.01, 14400),
    Channel(plc_ip_address, "flowtotalyesterday", "Flow_Total[1]", "REAL", 1.0, 14400),
    Channel(plc_ip_address, "energytotalyesterday", "Energy_Total[1]", "REAL", 1.0, 14400),
    Channel(plc_ip_address, "alarmflowrate", "alarm_Flowmeter", "STRING", _, 3600, map_=maps['alarm']),
    Channel(plc_ip_address, "alarmintakepressure", "alarm_IntakePressure", "STRING", _, 3600, map_=maps['alarm']),
    Channel(plc_ip_address, "alarmintaketemperature", "alarm_IntakeTemperature", "STRING", _, 3600, map_=maps['alarm']),
    Channel(plc_ip_address, "alarmtubingpressure", "alarm_TubingPressure", "STRING", _, 3600, map_=maps['alarm']),
    Channel(plc_ip_address, "alarmfluidlevel", "alarm_FluidLevel", "STRING", _, 3600, map_=maps['alarm']),
    Channel(plc_ip_address, "alarmvfd", "alarm_VFD", "STRING", _, 3600, map_=maps['alarm']),
    Channel(plc_ip_address, "alarmlockout", "alarm_Lockout", "STRING", _, 3600, map_=maps['lockout']),
    Channel(plc_ip_address, "runpermissive", "Run_Permissive_INT", "STRING", _, 3600, map_=maps['permissive']),
    Channel(plc_ip_address, "startpermissive", "Start_Permissive_INT", "STRING", _, 3600, map_=maps['permissive']),
    Channel(plc_ip_address, "startcommand", "cmd_Start", "BOOL", _, 3600),
    Channel(plc_ip_address, "stopcommand", "cmd_Stop", "BOOL", _, 3600),
    Channel(plc_ip_address, "flowsetpoint", "cfg_PID_FlowSP", "REAL", 0.5, 3600),
    Channel(plc_ip_address, "fluidlevelsetpoint", "cfg_PID_FluidLevelSP", "REAL", 0.5, 3600),
    Channel(plc_ip_address, "manualfrequencysetpoint", "cfg_PID_ManualSP", "REAL", 0.5, 3600),
    Channel(plc_ip_address, "tubingpressuresetpoint", "cfg_PID_TubingPressureSP", "REAL", 0.5, 3600),
    Channel(plc_ip_address, "pressureshutdownlimit", "AIn_IntakePressure.Val_LoLim", "REAL", 0.5, 14400),
    Channel(plc_ip_address, "pressurestartuplimit", "AIn_IntakePressure.Val_HiLim", "REAL", 0.5, 14400),
    Channel(plc_ip_address, "temperatureshutdownlimit", "AIn_IntakeTemperature.Val_HiLim", "REAL", 0.5, 14400),
    Channel(plc_ip_address, "temperaturestartuplimit", "AIn_IntakeTemperature.Val_LoLim", "REAL", 0.5, 14400),
    Channel(plc_ip_address, "sensorheight", "cfg_DHSensorDistToIntake", "REAL", 0.5, 14400),
    Channel(plc_ip_address, "sch_enabled", "sch_enabled", "BOOL", _, 3600)
]

scheduler_history = [
    ScheduleRun(0, type_="History"), ScheduleRun(1, type_="History"), ScheduleRun(2, type_="History"),
    ScheduleRun(3, type_="History"), ScheduleRun(4, type_="History"), ScheduleRun(5, type_="History"),
    ScheduleRun(6, type_="History"), ScheduleRun(7, type_="History"), ScheduleRun(8, type_="History"),
    ScheduleRun(9, type_="History")
]

scheduler_schedule = [
    ScheduleRun(0, type_="Schedule"), ScheduleRun(1, type_="Schedule"), ScheduleRun(2, type_="Schedule"),
    ScheduleRun(3, type_="Schedule"), ScheduleRun(4, type_="Schedule"), ScheduleRun(5, type_="Schedule"),
    ScheduleRun(6, type_="Schedule"), ScheduleRun(7, type_="Schedule"), ScheduleRun(8, type_="Schedule"),
    ScheduleRun(9, type_="Schedule")
]


class start(threading.Thread, deviceBase):
    """Start class required by Meshify."""

    def __init__(self, name=None, number=None, mac=None, Q=None, mcu=None, companyId=None, offset=None, mqtt=None, Nodes=None):
        """Initialize the driver."""
        threading.Thread.__init__(self)
        deviceBase.__init__(self, name=name, number=number, mac=mac, Q=Q, mcu=mcu, companyId=companyId, offset=offset, mqtt=mqtt, Nodes=Nodes)

        self.daemon = True
        self.version = "3"
        self.finished = threading.Event()
        self.forceSend = False
        threading.Thread.start(self)

    # this is a required function for all drivers, its goal is to upload some piece of data
    # about your device so it can be seen on the web
    def register(self):
        """Register the driver."""
        self.sendtodb("log", "BOOM! Booted.", 0)

    def run(self):
        """Actually run the driver."""
        global persist
        wait_sec = 30
        for i in range(0, wait_sec):
            print("advvfdipp driver will start in {} seconds".format(wait_sec - i))
            time.sleep(1)
        print("BOOM! Starting advvfdipp driver...")
        send_loops = 0
        while True:
            if self.forceSend:
                print "FORCE SEND: TRUE"
            for c in channels:
                if c.read(self.forceSend):
                    self.sendtodb(c.mesh_name, c.value, 0)

            for sch_h in scheduler_history:
                sch_h.read()
                this_sch_h = sch_h.jsonify()
                if this_sch_h['id'] > persist['last_schedule_history']['id']:
                    persist['last_schedule_history'] = this_sch_h
                    print(json.dumps(this_sch_h, indent=4))
                    self.sendtodbJSON("run_history", json.dumps(this_sch_h), this_sch_h['timestamp'])
                    with open("persist.json", 'w') as persist_file:
                        json.dump(persist, persist_file, indent=4)

            for sch_s in scheduler_schedule:
                if sch_s.read(self.forceSend):
                    self.sendtodbJSON("run_schedule", json.dumps(sch_s.jsonify()), 0)

            print("advvfdipp driver still alive...")
            if self.forceSend:
                if send_loops > 2:
                    print("Turning off forceSend")
                    self.forceSend = False
                    send_loops = 0
                else:
                    send_loops += 1

    def advvfdipp_sync(self, name, value):
        """Sync all data from the driver."""
        self.forceSend = True
        self.sendtodb("log", "synced", 0)
        return True

    def advvfdipp_addtoschedule(self, name, value):
        """Add an entry into the scheduler."""
        new_sch = json.loads(value)
        try:
            id = int(new_sch['id'])
            control_mode = {"tag": "sch_RunSchedule[{}].controlMode".format(id), "val": reverse_map(new_sch['control_mode'], maps['pid_controlmode'])}
            control_setpoint = {"tag": "sch_RunSchedule[{}].controlSetpoint".format(id), "val": new_sch['control_setpoint']}
            completion_parameter = {"tag": "sch_RunSchedule[{}].completionParameter".format(id), "val": reverse_map(new_sch['completion_parameter'], maps['completion_parameter'])}
            completion_comparison = {"tag": "sch_RunSchedule[{}].completionComparison".format(id), "val": reverse_map(new_sch['completion_comparison'], maps['completion_comparison'])}
            completion_value_target = {"tag": "sch_RunSchedule[{}].completionValueTarget".format(id), "val": new_sch['completion_value_target']}

            ch_to_write = [id, control_mode, control_setpoint, completion_parameter, completion_comparison, completion_value_target]
            for ch in ch_to_write:
                w = write_tag(plc_ip_address, ch['tag'], ch['val'])
                print(w)
            return True
        except KeyError:
            print("part of the schedule entry is missing")
            return False
