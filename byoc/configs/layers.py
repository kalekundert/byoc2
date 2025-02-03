class Layer:

    def __init__(self, payload, provenance=None):
        # Right now this class is just an empty wrapper around a "payload" 
        # object.  But in the future, I'm planning to add some information 
        # about where the payload came from, for the purpose of making nice 
        # error messages.
        self.payload = payload
        self.provenance = provenance
