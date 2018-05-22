class sample(object):


    # Using slots saves memory by keeping __dict__ undefined.
    __slots__ = ["timestamp", "value"]

    def __init__(self, value=0, timestamp=0):
        
        self.timestamp = timestamp
        self.value = value


    
