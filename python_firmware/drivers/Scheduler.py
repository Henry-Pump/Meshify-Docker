"""Hold scheduler classes and functions."""
import time
from Channel import Channel
from Maps import adv_vfd_ipp_map as maps
_ = None

plc_ip_address = "10.20.4.36"


class ScheduleRun:
    """Hold config for a schedule history run."""

    def __init__(self, index_, type_="Schedule"):
        """Initialize the class."""
        self.index_ = index_
        self.json = False
        if type_ in ["Schedule", "History"]:
            self.type_ = type_
        else:
            self.type_ = "Schedule"
            print("SERIOUS ERROR! {} IS NOT A VALID TYPE FOR ScheduleRun with Index = {}".format(type_, index_))
        self.channels = [
            Channel(plc_ip_address, "sch_{}_id{}".format(self.type_, self.index_),
                    "sch_Run{}[{}].id".format(self.type_, self.index_), "DINT", 0.5, 3600),
            Channel(plc_ip_address, "sch_{}_controlmode{}".format(self.type_, self.index_),
                    "sch_Run{}[{}].controlmode".format(self.type_, self.index_), "STRING", _, 3600, map_=maps['pid_controlmode']),
            Channel(plc_ip_address, "sch_{}_controlsp{}".format(self.type_, self.index_),
                    "sch_Run{}[{}].controlSetpoint".format(self.type_, self.index_), "REAL", 0.5, 3600),
            Channel(plc_ip_address, "sch_{}_complparam{}".format(self.type_, self.index_),
                    "sch_Run{}[{}].completionParameter".format(self.type_, self.index_), "STRING", _, 3600, map_=maps['completion_parameter']),
            Channel(plc_ip_address, "sch_{}_complcomp{}".format(self.type_, self.index_),
                    "sch_Run{}[{}].completionComparison".format(self.type_, self.index_), "STRING", _, 3600, map_=maps['completion_comparison']),
            Channel(plc_ip_address, "sch_{}_compltarget{}".format(self.type_, self.index_),
                    "sch_Run{}[{}].completionValueTarget".format(self.type_, self.index_), "REAL", 0.5, 3600),
            Channel(plc_ip_address, "sch_{}_complactual{}".format(self.type_, self.index_),
                    "sch_Run{}[{}].completionValueCurrent".format(self.type_, self.index_), "REAL", 10.0, 3600),
            Channel(plc_ip_address, "sch_{}_bbltotal{}".format(self.type_, self.index_),
                    "sch_Run{}[{}].BBLTotal".format(self.type_, self.index_), "REAL", 10.0, 3600)
        ]

    def read(self, force_send=False):
        """Read values of the schedule history from the PLC."""
        new_value = False
        for c in self.channels:
            if c.read(force_send):
                new_value = True
        return new_value

    def jsonify(self):
        """Give a JSON-ready object."""
        return {
                "id": self.channels[0].value,
                "control_mode": self.channels[1].value,
                "control_setpoint": self.channels[2].value,
                "completion_parameter": self.channels[3].value,
                "completion_comparison": self.channels[4].value,
                "completion_value_target": self.channels[5].value,
                "completion_value_actual": self.channels[6].value,
                "completion_bbl_total": self.channels[7].value,
                "timestamp": time.time()
            }
