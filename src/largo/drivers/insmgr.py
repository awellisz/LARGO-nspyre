from nspyre import InstrumentManager

class MyInstrumentManager(InstrumentManager):
    def __init__(self):
        super().__init__(register_gateway=False)
        # self.register_gateway(port=42068) # remote server (not used)
        self.register_gateway(port=42067) # local server
