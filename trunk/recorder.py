from PyQt4.QtCore import QThread, QString

from datetime import datetime
from numpy import dtype, array
import os
from tables import *
from time import time

class Recorder(QThread):
    
    TAG = "[Recorder]"
    DATA_PATH = "data/"

    def __init__(self):
        QThread.__init__(self)
    
    def __del__(self):
        self.h5file.close()

    def begin(self, equipment):
        dir = self.DATA_PATH + equipment.short_name
        if not os.path.exists(dir):
            os.makedirs(dir) # TODO: race condition if directory created between the two calls, quite unprobable
        
        txt = "{0}/{1}_{2}.h5"
        self.filename = txt.format(dir, equipment.short_name, datetime.now().strftime("%Y%m%d_%H%M%S"))
        try:
            self.h5file = openFile(self.filename, mode = "w", title = "{0} data file".format(equipment.name))

        except IOError:
            print self.TAG, "Error creating HDF5 file: ",  self.filename
            raise
        
        else:
            for instrument_config in equipment.instruments:
                instrument = instrument_config.instrument
                group = self.h5file.createGroup(self.h5file.root, instrument.short_name, instrument.name)
                for packet in instrument.rx_packets.itervalues():
                    format = array([], dtype(packet.types() + [("timestamp", "float64")]))
                    short_name = packet.name.lower().replace(' ','_')
                    packet.table = self.h5file.createTable(group, short_name, format, packet.name)
            self.start()

    def run(self):
        self.exec_()
    
    def on_new_packet(self,  packet):
        if packet.data:
            packet.instrument_packet.table.append([packet.data + (time(), )])
            packet.instrument_packet.table.flush()
