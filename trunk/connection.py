from PyQt4.QtCore import pyqtSignal, QSocketNotifier, QThread, QTimer

import logging, serial

import instrument
from instrument import PacketFormat


class Connection(QThread):
    
    DEFAULT_BUFFER_SIZE = 8
    
    # Signal for new data packet received event
    new_data_received = pyqtSignal(bytearray)
    
    # Signal for new data packet received event
    error_occurred = pyqtSignal()

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
        
        # I/O connection
        self.io_conn = None
        
        # bytearray() to store received packet bytes
        self.packet = bytearray()
        
        # bytearray() to store remaining data after receiving a complete packet
        self.old_data = None
        
        # last position in self.packet checked for packet end
        self.last_index = 0
        
        # flag for exiting the read_data iteration
        self.exiting = False
        
        # flag for when a new packet is found in the input buffer
        self.packet_found = False
        
        # default logger
        self.log = logging.getLogger('GDAIS.Connection')
    
    def __del__(self):
        self.log.debug("Deleting connection thread")
    
    def begin(self,  instrument):
        # instrument description
        self.instrument = instrument
        
        self.log.info("Connected: {0}".format(self.io_conn))
        
        # input read buffer size
        self.buffer_size = self.DEFAULT_BUFFER_SIZE
        
        # auxiliary variables used in data reception
        format = instrument.packet_format
        if (not PacketFormat.FormatField.end_bytes in format.rx_format and
            not PacketFormat.FormatField.start_bytes in format.rx_format and
            not PacketFormat.FormatField.packet_num in format.rx_format):
                # suppose all packets of the same length
                packet = instrument.rx_packets.values()[0]
                self.buffer_size = packet.struct.size # struct added by parser
            
        else:
            if PacketFormat.FormatField.start_bytes in format.rx_format:
                self.start_bytes = bytearray(format.start_bytes)
                self.start_bytes_len = len(self.start_bytes)

            if PacketFormat.FormatField.end_bytes in format.rx_format:
                self.end_bytes = bytearray(format.end_bytes)
                self.end_bytes_len = len(self.end_bytes)
        
        # auxiliary functions used in data reception
        if PacketFormat.FormatField.start_bytes in format.rx_format:
            self._find_packet_start = self._find_packet_start_mark
        
        if PacketFormat.FormatField.end_bytes in format.rx_format:
            self._find_packet_end = self._find_packet_end_mark
        elif PacketFormat.FormatField.start_bytes in format.rx_format:
            if (PacketFormat.FormatField.packet_num in format.rx_format or
                len(self.instrument.rx_packets) == 1):
                self._find_packet_end = self._find_packet_end_next_start_or_len
            else:
                self._find_packet_end = self._find_packet_end_next_start
        elif PacketFormat.FormatField.packet_num in format.rx_format:
            self._find_packet_end = self._find_packet_end_len
        
        self.start()
    
    def run(self):
        self.exec_()
        self.log.debug("Ending connection thread")
    
    def send_data(self, data):
        format = self.instrument.packet_format
        raw_data = bytearray()
        
        if PacketFormat.FormatField.start_bytes in format.tx_format:
            raw_data += bytearray(format.start_bytes)
        
        raw_data += data
        
        if PacketFormat.FormatField.end_bytes in format.tx_format:
            raw_data += bytearray(format.end_bytes)
        
        txt_raw =  ' '.join(['0x{0:X}'.format(d) for d in raw_data])
        self.log.debug("Sending Raw Data: {0}".format(txt_raw))
        
        self.io_conn.write(str(raw_data))
    
    def read_data(self, fd):
        format = self.instrument.packet_format
        while not self.exiting:
            data = self.io_conn.read(self.buffer_size)
            if not data:
                # continue reading until some data is read
                break
            
            #TODO: used when reading from file
            #self.sleep(1)
            
            if not self.packet:
                # starting a new packet, using the remaining data from previous packet
                if self.old_data:
                    data = self.old_data + data
                    self.old_data = None
                self._find_packet_start(data)
            else:
                # already started a packet, append new data
                self.packet += data
            
            if self.packet:
                self._find_packet_end()
            
            if self.packet_found:
                self.packet_found = False
                break
    
    def _find_packet_start(self, data):
        """Find a new packet start in the given data array.
        
        This is the default function for a new packet start. As it has no info
        about packet format it just uses the given data as the beggining
        of a new packet.
        
        See also: _find_packet_start_mark
        """
        self.packet += data
    
    def _find_packet_start_mark(self, data):
        """Find a new packet start in the given data array, using a start mark.
        
        Search for packet start bytes marker in input data and, if found,
        save it as the beginning of a new packet.
        
        See also: _find_packet_start
        """
        for i in range(len(data) - self.start_bytes_len + 1):
            if data[i:i + self.start_bytes_len] == self.start_bytes:
                # packet start bytes found, append new data without start bytes
                self.packet += data[i + self.start_bytes_len:]
                self.last_index = 0 # move index to the beginning of the packet
                break
    
    def _find_packet_end(self):
        """Find current packet end.
        
        This is the default function for packet end search. As it has no info
        about packet format it just tries to get a fixed length of data bytes,
        saves not used data and prepares for the next packet.
        
        See also: _find_packet_end_mark, _find_packet_end_len,
                        _find_packet_end_next_start
        """
        if len(self.packet) >= self.buffer_size:
            self._new_packet_found(
               packet_data=self.packet[:self.buffer_size],
               excess_data=self.packet[self.buffer_size:]
            )
    
    def _find_packet_end_mark(self):
        """Find current packet end, using end bytes mark.
        
        Search for packet end bytes mark in the current packet input data. If
        found, emit the new packet without end bytes, save exceding data and
        prepare for the next packet.
        
        See also: _find_packet_end
        """
        for i in range(self.last_index, len(self.packet) - self.end_bytes_len + 1):
            if self.packet[i:i + self.end_bytes_len] == self.end_bytes:
                self._new_packet_found(
                    packet_data=self.packet[:i],
                    excess_data=self.packet[i + self.end_bytes_len:]
                )
                break
        self.last_index += i
    
    def _find_packet_end_next_start(self):
        """Find current packet end, using next packet start bytes mark.
        
        Search for next packet start bytes mark in the current packet input
        data. If found, emit the new packet, save exceding data and prepare for
        the next packet.
        
        Note that this method will lock the system when the instrument sends
        a single packet and waits for the next command, as then there will not
        be any packet after the current one to be detected. In this case, it
        would be better to use _find_packet_end_next_start_or_len method.
        
        See also: _find_packet_end, _find_packet_end_next_start_or_len
        """
        for i in range(self.last_index, len(self.packet) - self.start_bytes_len + 1):
            if self.packet[i:i + self.start_bytes_len] == self.start_bytes:
                self._new_packet_found(
                    packet_data=self.packet[:i],
                    excess_data=self.packet[i:]
                )
                break
        self.last_index += i
    
    def _find_packet_end_len(self):
        """Find current packet end, using its length.
        
        Get expected packet length from the instrument information, using the
        current packet first byte as the packet number. If the current packet
        data length is enough, emit the new packet, save exceding data and
        prepare for the next packet.
        
        If the packet number is not in the instrument's packet list, but there
        is only one packet defined, use its lenght. In other cases, emit the
        current data as a new package and wait for the next one.
        
        Note that this method may lock the system when it is waiting for a
        reply but some bytes are lost and the instrument does not send more
        data. If packet format includes start bytes, it would be better to use
        _find_packet_end_next_start_or_len method.
        
        See also: _find_packet_end, _find_packet_end_next_start_or_len
        """
        if self.packet[0] in self.instrument.rx_packets:
            packet_len = self.instrument.rx_packets[self.packet[0]].struct.size
            packet_len += 1 # packet number
            if len(self.packet) >= packet_len:
                self._new_packet_found(
                   packet_data=self.packet[:packet_len],
                   excess_data=self.packet[packet_len:]
                )
        elif len(self.instrument.rx_packets) == 1:
            # In case of having only a packet defined, we can know directly
            # its length, even if there is no packet number to identify it
            packet_len = self.instrument.rx_packets.values()[0].struct.size
            if PacketFormat.FormatField.packet_num in format.rx_format:
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
    
    def _find_packet_end_next_start_or_len(self):
        """Find current packet end, using start bytes mark or the length.
        
        Check if there is a new packet in the current input data bytes, first
        searching for next packet start bytes and, if it is not found, using
        the packet length if the packet number is known.
        
        See also: _find_packet_end, _find_packet_end_next_start,
                        _find_packet_end_len
        """
        self._find_packet_end_next_start()
        if not self.packet_found:
            self._find_packet_end_len()
    
    def _new_packet_found(self, packet_data, excess_data):
        # emit the new packet data
        self.new_data_received.emit(packet_data)
        
        # store not used data and prepare for next packet
        self.old_data = excess_data
        self.packet = bytearray('')
        
        # set new packet found flag
        self.packet_found = True


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
        if self.io_conn and self.io_conn.isOpen():
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
            self.log.exception("Serial device can not be found or configured")
            self.error_occurred.emit()
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
            self.log.exception("The input file does not exist")
            self.error_occurred.emit()
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
