from PyQt4.QtCore import QThread, QString

from datetime import datetime
from numpy import dtype, array
import logging
import os
from tables import *
from time import time

class Recorder(QThread):
    
    BASE_PATH = '/home/pau/feina/UPC/projecte/code/GDAIS/GDAIS-core'
    DATA_PATH = os.path.join(BASE_PATH, 'data')

    def __init__(self):
        QThread.__init__(self)
        
        # HDF-5 data object
        self.h5file = None
        
        # default logger
        self.log = logging.getLogger('GDAIS.Recorder')

    def begin(self, equipment):
        dir = os.path.join(self.DATA_PATH, equipment.short_name)
        self.log.info("Data output directory: '{0}'".format(dir))
        if not os.path.exists(dir):
            # TODO: race condition if directory created between the two calls, quite unprobable
            os.makedirs(dir)
        
        txt = "{0}_{1}.h5"
        filename = txt.format(equipment.short_name, datetime.utcnow().strftime("%Y%m%d_%H%M%S"))
        self.filepath = os.path.join(dir, filename)
        try:
            self.h5file = openFile(self.filepath, mode = "w", title = "{0} data file".format(equipment.name))

        except IOError:
            self.log.error("Error creating HDF5 file: '{0}'".format(self.filepath))
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
    
    def quit(self):
        if self.h5file:
            self.h5file.close()
        QThread.quit(self)
    
    def on_new_packet(self,  packet):
        if packet.data:
            packet.instrument_packet.table.append([packet.data + (time(), )])
            packet.instrument_packet.table.flush()
