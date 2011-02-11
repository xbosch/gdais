from PyQt4.QtCore import pyqtSignal, QCoreApplication, QString

import signal, sys

from connection import FileConnection, SerialConnection
from instrument import Instrument
from parser import Parser
from recorder import Recorder

TAG = "[main]"

def on_new_packet(packet):
    print TAG, "New packet received:", packet.instrument_packet.name
    if packet.data:
        print TAG, "  ", packet.data


if __name__ == "__main__":
#    quit_signal = pyqtSignal()
    
    def signal_handler(signum, frame):
        print TAG, "Signal %s received, exiting..." % signum
        app.quit()
    
    app = QCoreApplication(sys.argv)
    
    instrument = Instrument("/home/pau/feina/UPC/projecte/code/GDAIS/conf/instruments/gps.json")
    
    recorder = Recorder()
    recorder.begin(instrument)
    
    parser = Parser()
    parser.new_packet_parsed.connect(on_new_packet)
    parser.new_packet_parsed.connect(recorder.on_new_packet)
    parser.begin(instrument)
    
    connection = FileConnection()
    connection.new_data_received.connect(parser.on_new_data_received)
    connection.begin(instrument, "/home/pau/feina/UPC/projecte/code/GDAIS/test/LOF06_short.bin")    
#    connection = SerialConnection()
#    connection.new_data_received.connect(parser.on_new_data_received)
#    connection.begin(instrument)
    
    signal.signal(signal.SIGINT, signal_handler)
#    quit_signal.connect(app.quit)
    
    sys.exit(app.exec_())
