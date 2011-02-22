from PyQt4.QtCore import QThread, QString

from datetime import datetime
from numpy import dtype, array
import os
from tables import *
from time import time

class Recorder(QThread):
    
    TAG = "[Recorder]"

    def __init__(self,  parent = None):
        QThread.__init__(self, parent)
        self.filename = "data/equip1/equip1"
        self.filename += "_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".h5"
    
    def __del__(self):
        self.h5file.close()

    def begin(self, instrument):
        self.h5file = openFile(self.filename, mode = "w", title = "Equip1 data file")

        self.tables = {}
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
