"""Define Meshify channel class."""
from pycomm.ab_comm.clx import Driver as ClxDriver
from pycomm.cip.cip_base import CommError, DataError
import time


def read_tag(addr, tag):
    """Read a tag from the PLC."""
    c = ClxDriver()
    try:
        if c.open(addr):
            try:
                v = c.read_tag(tag)
                return v
            except DataError:
                c.close()
                print("Data Error during readTag({}, {})".format(addr, tag))
    except CommError:
        # err = c.get_status()
        c.close()
        print("Could not connect during readTag({}, {})".format(addr, tag))
        # print err
    c.close()
    return False


def read_array(addr, tag, start, end):
    """Read an array from the PLC."""
    c = ClxDriver()
    if c.open(addr):
        arr_vals = []
        try:
            for i in range(start, end):
                tag_w_index = tag + "[{}]".format(i)
                v = c.read_tag(tag_w_index)
                # print('{} - {}'.format(tag_w_index, v))
                arr_vals.append(round(v[0], 4))
            # print(v)
            if len(arr_vals) > 0:
                return arr_vals
            else:
                print("No length for {}".format(addr))
                return False
        except Exception:
            print("Error during readArray({}, {}, {}, {})".format(addr, tag, start, end))
            err = c.get_status()
            c.close()
            print err
            pass
        c.close()


def write_tag(addr, tag, val):
    """Write a tag value to the PLC."""
    c = ClxDriver()
    if c.open(addr):
        try:
            cv = c.read_tag(tag)
            wt = c.write_tag(tag, val, cv[1])
            return wt
        except Exception:
            print("Error during writeTag({}, {}, {})".format(addr, tag, val))
            err = c.get_status()
            c.close()
            print err
        c.close()


class Channel:
    """Holds the configuration for a Meshify channel."""

    def __init__(self, ip, mesh_name, plc_tag, data_type, chg_threshold, guarantee_sec, map_=False, write_enabled=False):
        """Initialize the channel."""
        self.plc_ip = ip
        self.mesh_name = mesh_name
        self.plc_tag = plc_tag
        self.data_type = data_type
        self.last_value = None
        self.value = None
        self.last_send_time = 0
        self.chg_threshold = chg_threshold
        self.guarantee_sec = guarantee_sec
        self.map_ = map_
        self.write_enabled = write_enabled

    def __str__(self):
        """Create a string for the channel."""
        return "{}: {}\nvalue: {},  last_send_time: {}".format(self.mesh_name, self.plc_tag, self.value, self.last_send_time)

    def read(self, force_send=False):
        """Read the value and check to see if needs to be stored."""
        send_needed = False
        send_reason = ""
        if self.plc_tag:
            v = read_tag(self.plc_ip, self.plc_tag)
            if v:
                if self.data_type == 'BOOL' or self.data_type == 'STRING':
                    if self.last_send_time == 0:
                        send_needed = True
                        send_reason = "no send time"
                    elif self.value is None:
                        send_needed = True
                        send_reason = "no value"
                    elif not (self.value == v[0]):
                        if self.map_:
                            if not self.value == self.map_[v[0]]:
                                send_needed = True
                                send_reason = "value change"
                        else:
                            send_needed = True
                            send_reason = "value change"
                    elif (time.time() - self.last_send_time) > self.guarantee_sec:
                        send_needed = True
                        send_reason = "guarantee sec"
                    elif force_send:
                        send_needed = True
                        send_reason = "forced"
                else:
                    if self.last_send_time == 0:
                        send_needed = True
                        send_reason = "no send time"
                    elif self.value is None:
                        send_needed = True
                        send_reason = "no value"
                    elif abs(self.value - v[0]) > self.chg_threshold:
                        send_needed = True
                        send_reason = "change threshold"
                    elif (time.time() - self.last_send_time) > self.guarantee_sec:
                        send_needed = True
                        send_reason = "guarantee sec"
                    elif force_send:
                        send_needed = True
                        send_reason = "forced"
                if send_needed:
                    self.last_value = self.value
                    if self.map_:
                        try:
                            self.value = self.map_[v[0]]
                        except KeyError:
                            print("Cannot find a map value for {} in {} for {}".format(v[0], self.map_, self.mesh_name))
                            self.value = v[0]
                    else:
                        self.value = v[0]
                    self.last_send_time = time.time()
                    print("Sending {} for {} - {}".format(self.value, self.mesh_name, send_reason))
        return send_needed
