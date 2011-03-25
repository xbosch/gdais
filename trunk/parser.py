from PyQt4.QtCore import pyqtSignal, QThread
import logging, struct


class ParsedPacket(object):
    
    def __init__(self, raw_data, packet=None, parsed_data=None):
        self.raw_data = raw_data
        self.instrument_packet = packet
        self.data = parsed_data
        self.info = ""


class Parser(QThread):
    
    # Signal for new packet received event
    new_packet_parsed = pyqtSignal(ParsedPacket)
    
    # Signal for new data ready to send event
    new_data_ready = pyqtSignal(bytearray)
    
    def __init__(self):
        QThread.__init__(self)
    
    def __del__(self):
        self.log.debug("Deleting parser thread.")

    def begin(self,  instrument):
        self.log = logging.getLogger('GDAIS.'+instrument.short_name+'.Parser')
        
        self.packet_format = instrument.packet_format
        
        self.rx_packets = instrument.rx_packets
        for packet in self.rx_packets.itervalues():
            packet.struct = struct.Struct(instrument.byte_order_char + packet.struct_format())
        
        self.tx_packets = instrument.tx_packets
        for packet in self.tx_packets.itervalues():
            packet.struct = struct.Struct(instrument.byte_order_char + packet.struct_format())
        
        self.start()
    
    def run(self):
        self.exec_()
        self.log.debug("Ending parser thread.")
    
    def on_new_command(self, command):
        self.log.debug("Sending '{0}' command".format(command.name))
        packet = self.tx_packets[command.id]
        data = bytearray()
        if self.packet_format.FORMAT_PACKET_NUM in self.packet_format.tx_format:
            data.append(command.id)
        data.extend(packet.struct.pack(*command.values))
        self.new_data_ready.emit(data)

    def on_new_data_received(self, raw_data):
        if raw_data:
            if self.packet_format.FORMAT_PACKET_NUM in self.packet_format.rx_format:
                packet = None
                if raw_data[0] in self.rx_packets:
                    packet_num = raw_data[0]
                    packet = self.rx_packets[packet_num]
                    data = raw_data[1:]
                else:
                    parsed_packet = ParsedPacket(raw_data)
                    parsed_packet.info = "Unknown packet id: 0x{0:x}".format(raw_data[0])
            else:
                # without packet number only one packet can be defined
                packet = self.rx_packets.values()[0]
                data = raw_data

            if packet:
                if len(data) == packet.struct.size:
                    parsed_data = packet.struct.unpack(str(data))
                    parsed_packet = ParsedPacket(raw_data, packet, parsed_data)
                    self.new_packet_parsed.emit(parsed_packet)
                else:
                    parsed_packet = ParsedPacket(raw_data, packet)
                    parsed_packet.info = "Wrong packet length: {0}, expected: {1}"
                    parsed_packet.info.format(len(data), packet.struct.size)

        else:
            parsed_packet = ParsedPacket(raw_data)
            parsed_packet.info = "Empty packet received"
        
        
        if parsed_packet.info:
            self.log.info(parsed_packet.info)
