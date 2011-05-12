from PyQt4.QtCore import pyqtSignal, QThread
import logging, struct

from instrument import PacketFormat


class ParsedPacket(object):
    
    def __init__(self, raw_data, packet=None, parsed_data=None):
        self.raw_data = raw_data
        self.instrument_packet = packet
        self.data = parsed_data
        self.info = ''
        self.log = logging.getLogger('GDAIS.Parser')


class Parser(QThread):
    
    # Signal for new packet received event
    new_packet_parsed = pyqtSignal(ParsedPacket)
    
    # Signal for new data ready to send event
    new_data_ready = pyqtSignal(bytearray)
    
    def __init__(self):
        QThread.__init__(self)
        
        # Flag to control when quit has been called and stop processing new signals
        self.exiting = False
        
        # Default logger
        self.log = logging.getLogger('GDAIS.Parser')

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
        self.log.debug("Ending parser thread")
    
    def quit(self):
        self.exiting = True
        QThread.quit(self)
    
    def on_new_command(self, command):
        if not self.exiting:
            self.log.debug("Sending '{0}' command (0x{1:X})".format(command.name, command.id))
            packet = self.tx_packets[command.id]
            data = bytearray()
            if PacketFormat.FormatField.packet_num in self.packet_format.tx_format:
                data.append(command.id)
            # TODO: should know values type and convert them correctly
            values = map(int, command.values)
            data.extend(packet.struct.pack(*values))
            
            self.new_data_ready.emit(data)
        
        else:
            self.log.error("Received new command while exiting")

    def on_new_data_received(self, raw_data):
        if raw_data:
            if PacketFormat.FormatField.packet_num in self.packet_format.rx_format:
                packet = None
                if raw_data[0] in self.rx_packets:
                    packet_num = raw_data[0]
                    packet = self.rx_packets[packet_num]
                    data = raw_data[1:]
                else:
                    parsed_packet = ParsedPacket(raw_data)
                    txt = "Unknown packet id: 0x{0:X} (Raw Data: {1})"
                    txt_raw =  ' '.join(['0x{0:X}'.format(d) for d in raw_data])
                    parsed_packet.info = txt.format(raw_data[0], txt_raw)
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
                    txt = "Wrong packet length: {0}, expected: {1} (Raw Data: {2})"
                    txt_raw =  ' '.join(['0x{0:X}'.format(d) for d in raw_data])
                    parsed_packet.info = txt.format(len(data), packet.struct.size, txt_raw)

        else:
            parsed_packet = ParsedPacket(raw_data)
            parsed_packet.info = "Empty packet received"
        
        
        if parsed_packet.info:
            self.log.info(parsed_packet.info)
