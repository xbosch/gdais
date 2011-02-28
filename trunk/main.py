from PyQt4.QtCore import pyqtSignal, QCoreApplication, QString, QTimer
from PyQt4.QtNetwork import QTcpServer

import signal, sys

from connection import BlockingSerialConnection, FileConnection, SerialConnection
from equipment import Equipment
from parser import Parser
from recorder import Recorder

TAG = "[main]"

def on_new_packet(packet):
    print TAG, "New packet received:", packet.instrument_packet.name
    if packet.data:
        fields = [str(f.name) for f in packet.instrument_packet.fields]
        str_fields = ', '.join(["{0}: {1:g}".format(x[0], x[1]) for x in zip(fields, packet.data)])
        print "{0}  ({1})".format(TAG, str_fields)


if __name__ == "__main__":
    
    app = QCoreApplication(sys.argv)
    
    equipment = Equipment("conf/equips/prova.json")
    
    recorder = Recorder()
    recorder.begin(equipment)
    
    for instrument_config in equipment.instruments:
        parser = Parser()
        parser.new_packet_parsed.connect(on_new_packet)
        parser.new_packet_parsed.connect(recorder.on_new_packet)
        parser.begin(instrument_config.instrument)
        
#        connection = SerialConnection()
#        connection.new_data_received.connect(parser.on_new_data_received)
#        connection.begin(instrument_config.instrument)
        connection = BlockingSerialConnection()
        connection.new_data_received.connect(parser.on_new_data_received)
        connection.begin(instrument_config.instrument)
#        connection = FileConnection()
#        connection.new_data_received.connect(parser.on_new_data_received)
#        connection.begin(instrument_config.instrument, "test/LOF06.bin")
    
    print TAG, "TCP server: Starting..."
    tcp_server = QTcpServer()
    if tcp_server.listen(port = 12345):
        print TAG, "TCP server: open a connection to http://localhost:{0} to quit GDAIS".format(tcp_server.serverPort())
        tcp_server.newConnection.connect(app.quit)
    else:
        print TAG, "Unable to start TCP server:", tcp_server.errorString()
        # define a timer to auto-quit the app after 10 sec
        timer = QTimer()
        timer.timeout.connect(app.quit)
        timer.start(10000)
    
    sys.exit(app.exec_())
