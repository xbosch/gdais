from PyQt4.QtCore import pyqtSignal, QThread
from struct import Struct

class ParsedPacket(object):
    
    def __init__(self, raw_data, packet=None, parsed_data=None):
        self.raw_data = raw_data
        self.instrument_packet = packet
        self.data = parsed_data
        self.info = ""


class Parser(QThread):

    TAG = "[Parser]"
    
    # Signal for new packet received event
    new_packet_parsed = pyqtSignal(ParsedPacket)
    
    def __init__(self, parent = None):
        QThread.__init__(self, parent)

    def begin(self,  instrument):
        self.packets = instrument.rx_packets
        for packet in self.packets.itervalues():
            packet.struct = Struct(instrument.byte_order_char + packet.struct_format())
        self.start()
    
    def run(self):
        self.exec_()

    def on_new_data_received(self, raw_data):
        if raw_data[0] and raw_data[0] in self.packets:
            packet_num = raw_data[0]
            packet = self.packets[packet_num]
            data = raw_data[1:]
            if len(data) == packet.struct.size:
                parsed_data = packet.struct.unpack(str(data))
                parsed_packet = ParsedPacket(raw_data, packet, parsed_data)
                self.new_packet_parsed.emit(parsed_packet)
            else:
                parsed_packet = ParsedPacket(raw_data, packet)
                parsed_packet.info = "Wrong packet length: " + str(len(data))
                parsed_packet.info += ", expected:" + str(packet.struct.size)
        else:
            parsed_packet = ParsedPacket(raw_data)
            if raw_data[0]:
                parsed_packet.info = "Unknown packet id: " + hex(raw_data[0])
            else:
                parsed_packet.info = "Empty packet received"
        
        if parsed_packet.info:
            print self.TAG, parsed_packet.info
