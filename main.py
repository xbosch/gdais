from PyQt4.QtCore import pyqtSignal, QCoreApplication, QString, QTimer
from PyQt4.QtNetwork import QTcpServer

import signal, sys

from connection import FileConnection, SerialConnection
from instrument import Instrument
from parser import Parser
from recorder import Recorder

TAG = "[main]"

def on_new_packet(packet):
    print TAG, "New packet received:", packet.instrument_packet.name
    if packet.data:
        fields = [str(f.name) for f in packet.instrument_packet.fields]
        print TAG, '  ', '('+', '.join(["%s: %d" % (x[0], x[1]) for x in zip(fields, packet.data)])+')'


if __name__ == "__main__":
    
    def signal_handler(signum, frame):
        print TAG, "Signal %s received, exiting..." % signum
        app.quit()
    
    app = QCoreApplication(sys.argv)
    
    instrument = Instrument("conf/instruments/gps.json")
#    instrument = Instrument("conf/instruments/compass_f350.json")
    
    recorder = Recorder()
    recorder.begin(instrument)
    
    parser = Parser()
    parser.new_packet_parsed.connect(on_new_packet)
    parser.new_packet_parsed.connect(recorder.on_new_packet)
    parser.begin(instrument)
    
    connection = FileConnection()
    connection.new_data_received.connect(parser.on_new_data_received)
    connection.begin(instrument, "test/LOF06.bin")    
#    connection = SerialConnection()
#    connection.new_data_received.connect(parser.on_new_data_received)
#    connection.begin(instrument)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    tcp_server = QTcpServer()
    if tcp_server.listen():
        print TAG, "TCP server: running"
        print TAG, "TCP server: open a connection to http://localhost:%s to quit GDAIS" % tcp_server.serverPort()
        tcp_server.newConnection.connect(app.quit)
    else:
        print TAG, "Unable to start TCP server:", tcp_server.errorString()
        # define a timer to auto-quit the app after 10 sec
        timer = QTimer()
        timer.timeout.connect(app.quit)
        timer.start(10000)
    
    sys.exit(app.exec_())
