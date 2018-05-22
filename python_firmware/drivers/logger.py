import datetime as dt
import time

class Logger(object):
    ''' This logger reports status messages to an M1 channel. It can be turned on and off.

    Attributes:
        channel_name: the M1 channel name for reporting logs
        message_sender: function that sends the log message, with the following arguments:
            (channel, message, qos)
        enabled: whether or not ot send log messages

    '''

    def __init__(self, channel_name, message_sender, enabled=False):
        self.channel_name = channel_name
        self.enabled = enabled
        self.message_sender = message_sender
        self.last_send = dt.datetime.utcnow()
        self.buffer = ""
        print("Logger initialized, reporting to channel " + self.channel_name)
    
    def log_message(self, message):

        now = dt.datetime.utcnow()
        # meshify database can only save one message per second per channel, so we buffer text

        if self.enabled:
            self.buffer += str(message)
            if (now - self.last_send).total_seconds() > 1:
                print("Sending log to %s: %s" % (self.channel_name, message))
                try:
                    self.message_sender(self.channel_name, self.buffer, 0)
                    self.last_send = now
                    self.buffer = ""
                except Exception as e:
                    print("Logger error: " + e)
            else:
                print("Buffered messages on %s" % self.channel_name)
                self.buffer += " ... "

    def enable(self):
        self.enabled = True
        print("Logger %s enabled" % self.channel_name)
        self.log_message("Logging enabled")
    
    def disable(self):
        if self.buffer:
            time.sleep(1)
        self.log_message("Logging disabled")
        print("Logger %s disabled" % self.channel_name)
        self.enabled = False


    def is_enabled(self):
        return self.enabled