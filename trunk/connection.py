from PyQt4.QtCore import pyqtSignal, QSocketNotifier, QThread, QTimer

import logging, serial

import instrument
from instrument import PacketFormat


class Connection(QThread):
    
    DEFAULT_BUFFER_SIZE = 8
    
    # Signal for new data packet received event
    new_data_received = pyqtSignal(bytearray)

    @staticmethod
    def create(conn, *args, **kwds):
        conn_type = instrument.ConnectionCfg.Type
        connection = {
            conn_type.serial: SerialConnection,
            conn_type.file:     FileConnection
        }.get(conn.type, None)
        
        if not connection:
            raise Exception('Connection type not implemented')
        
        return connection(*args, **kwds)
    
    def __init__(self):
        QThread.__init__(self)
        
        # bytearray() to store received packet bytes
        self.packet = bytearray()
        
        # bytearray() to store remaining data after receiving a complete packet
        self.old_data = None
        
        # last position in self.packet checked for packet end
        self.last_index = 0
        
        # flag for exiting the read_data iteration
        self.exiting = False
    
    def __del__(self):
        self.log.debug("Deleting connection thread")
    
    def begin(self,  instrument):
        # instrument description
        self.instrument = instrument
        
        self.log.info("Connected: {0}".format(self.io_conn))
        
        # input read buffer size
        self.buffer_size = self.DEFAULT_BUFFER_SIZE
        
        format = instrument.packet_format
        if not PacketFormat.FormatField.end_bytes in format.rx_format and \
            not PacketFormat.FormatField.start_bytes in format.rx_format and \
            not PacketFormat.FormatField.packet_num in format.rx_format:
                # suppose all packets of the same length
                packet = instrument.rx_packets.values()[0]
                self.buffer_size = packet.struct.size # struct added by parser
        
        # auxiliary variables used in data reception
        if PacketFormat.FormatField.start_bytes in format.rx_format:
            self.start_bytes = bytearray(format.start_bytes)
            self.start_bytes_len = len(self.start_bytes)

        if PacketFormat.FormatField.end_bytes in format.rx_format:
            self.end_bytes = bytearray(format.end_bytes)
            self.end_bytes_len = len(self.end_bytes)
        
        self.start()
    
    def run(self):
        self.exec_()
        self.log.debug("Ending connection thread")
    
    def send_data(self, data):
        format = self.instrument.packet_format
        
        if PacketFormat.FormatField.start_bytes in format.tx_format:
            self.io_conn.write(bytearray(format.start_bytes))
        
        self.io_conn.write(str(data))
        
        if PacketFormat.FormatField.end_bytes in format.tx_format:
            self.io_conn.write(bytearray(format.end_bytes))
    
    def read_data(self, fd):
        format = self.instrument.packet_format
        while not self.exiting:
            data = self.io_conn.read(self.buffer_size)
            if not data:
                # continue reading until some data is read
                break
            
            self.sleep(1)
            
            if not self.packet:
                # starting a new packet, using the remaining data from previous packet
                if self.old_data:
                    data = self.old_data + data
                if PacketFormat.FormatField.start_bytes in format.rx_format:
                    # search for packet start bytes marker in input data
                    for i in range(len(data) - self.start_bytes_len + 1):
                        if data[i:i + self.start_bytes_len] == self.start_bytes:
                            # packet start bytes found, append new data without start bytes
                            data = data[i + self.start_bytes_len:]
                            self.packet += data
                            self.last_index = 0 # move index to the beginning of the packet
                            break
                else:
                    # no start bytes mark, just use this data as the packet start
                    self.packet += data
            else:
                # already started a packet, append new data
                self.packet += data
            
            if self.packet:
                if PacketFormat.FormatField.end_bytes in format.rx_format:
                    # search for packet end bytes in input data
                    for i in range(self.last_index, len(self.packet) - self.end_bytes_len + 1):
                        if self.packet[i:i + self.end_bytes_len] == self.end_bytes:
                            # Packet end bytes found, emit the new packet without end bytes,
                            # store exceeding data and prepare for next packet
                            self._new_packet_found(
                                packet_data=self.packet[:i],
                                excess_data=self.packet[i + self.end_bytes_len:]
                            )
                            break
                            
                        self.last_index += 1
                    
                elif PacketFormat.FormatField.start_bytes in format.rx_format:
                    # As there is no end bytes marker but start bytes marker is defined,
                    # try to find the start of the next packet and cut there
                    for i in range(self.last_index, len(self.packet) - self.start_bytes_len + 1):
                        if self.packet[i:i + self.start_bytes_len] == self.start_bytes:
                            # next packet start bytes found, emit the new packet without end bytes,
                            # store exceeding data and prepare for next packet
                            self._new_packet_found(
                                packet_data=self.packet[:i],
                                excess_data=self.packet[i:]
                            )
                            break
                            
                        self.last_index += 1
                    
                elif PacketFormat.FormatField.packet_num in format.rx_format:
                    # Having no end bytes marker nor start bytes marker, try to obtain
                    # the data length from the instrument description using packet number
                    if self.packet[0] in self.instrument.rx_packets:
                        packet_len = self.instrument.rx_packets[self.packet[0]].struct.size
                        packet_len += 1 # packet number
                        if len(self.packet) >= packet_len:
                            self._new_packet_found(
                               packet_data=self.packet[:packet_len],
                               excess_data=self.packet[packet_len:]
                            )
                        
                    else:
                        # Packet number not in list of known packets, emit the unidentified
                        # packet and hope that the next packet will be recognized
                        self._new_packet_found(
                           packet_data=self.packet,
                           excess_data=None
                        )
                    
                else:
                    # Without end bytes nor start bytes marker just try to get a fixed
                    # length data bytes, store not used data and prepare for next packet
                    if len(self.packet) >= self.buffer_size:
                        self._new_packet_found(
                           packet_data=self.packet[:self.buffer_size],
                           excess_data=self.packet[self.buffer_size:]
                        )
    
    def _new_packet_found(self, packet_data, excess_data):
        # emit the new packet data
        self.new_data_received.emit(packet_data)
        
        # store not used data and prepare for next packet
        self.old_data = excess_data
        self.packet = bytearray('')


class SerialConnection(Connection):
    
    # Serial Constants
    BYTESIZE = {
                    5: serial.FIVEBITS,
                    6: serial.SIXBITS,
                    7: serial.SEVENBITS,
                    8: serial.EIGHTBITS
                }
    
    PARITY = {
                'N': serial.PARITY_NONE,
                'E': serial.PARITY_EVEN,
                'O': serial.PARITY_ODD
            }
    
    STOPBITS = {
                    1: serial.STOPBITS_ONE,
                    2: serial.STOPBITS_TWO
                }
    
    def __del__(self):
        if self.io_conn:
            self.log.debug("Clearing serial port buffers (In and Out)")
            self.io_conn.flushOutput()
            self.io_conn.flushInput()
            self.log.info("Closing serial port")
            self.io_conn.close()
        Connection.__del__(self)
    
    def begin(self,  instrument):
        self.log = logging.getLogger('GDAIS.'+instrument.short_name+'.SerialConnection')
        
        self.io_conn = serial.Serial()
        self.io_conn.port = instrument.connection.serial_port
        self.io_conn.baudrate = instrument.connection.baudrate
        self.io_conn.bytesize = self.BYTESIZE[instrument.connection.data_bits]
        self.io_conn.parity = self.PARITY[instrument.connection.parity]
        self.io_conn.stopbits = self.STOPBITS[instrument.connection.stop_bits]
        self.io_conn.timeout = 0 # non-blocking mode (return immediately on read)
        try:
            self.io_conn.open()
        except serial.SerialException:
            self.log.exception("Device can not be found or can not be configured")
        else:
            Connection.begin(self, instrument)
    
    def run(self):
        notifier = QSocketNotifier(self.io_conn.fileno(), QSocketNotifier.Read)
        notifier.activated.connect(self.read_data)
        
        Connection.run(self)


class FileConnection(Connection):
    
    def __del__(self):
        if self.io_conn:
            self.log.info("Closing input file")
            self.io_conn.close()
        Connection.__del__(self)

    def begin(self,  instrument):
        self.log = logging.getLogger("GDAIS."+instrument.short_name+".FileConnection")
        try:
            self.io_conn = open(instrument.connection.filename,  'rb')
        except IOError:
            self.log.exception("The file does not exist, exiting gracefully")
        else:
            Connection.begin(self, instrument)
    
    def run(self):
        self.read_data(self.io_conn.fileno())
        Connection.run(self)
    
    def quit(self):
        self.exiting = True
        Connection.quit(self)
    
    def send_data(self, data):
        # file connection can't send data
        raise NotImplementedError
