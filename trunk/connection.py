from PyQt4.QtCore import pyqtSignal, QSocketNotifier, QThread, QTimer
import serial


class Connection(QThread):
    
    TAG = "[Connection]"
    
    DEFAULT_BUFFER_SIZE = 8
    
    # Signal for new data packet received event
    new_data_received = pyqtSignal(bytearray)
    
    def __init__(self):
        QThread.__init__(self)
    
    def begin(self,  instrument):
        self.instrument = instrument
        self.packet = bytearray('')
        self.old_data = None
        print self.TAG, "Connected:", self.io_conn
        
        format = self.instrument.packet_format
        if format.FORMAT_END_BYTES in format.rx_format:
            self.buffer_size = self.DEFAULT_BUFFER_SIZE
        else:
            # suppose all packets of the same length as there's no end mark
            packet = instrument.rx_packets.values()[0]
            self.buffer_size = packet.struct.size # struct added by parser
        
        self.start()
    
    def run(self):
        self.exec_()
    
    def read_data(self, fd):
        format = self.instrument.packet_format
        while True:
            data = self.io_conn.read(self.buffer_size)
            if not data:
                break
            
            if not self.packet:
                if self.old_data:
                    data = self.old_data + data
                if format.FORMAT_START_BYTES in format.rx_format:
                    for i in xrange(len(data) - len(format.start_bytes) + 1):
                        if data[i:i + len(format.start_bytes)] == bytearray(format.start_bytes):
                            self.packet += data[len(format.start_bytes) + i:]
                            break
                else:
                    self.packet += data
            else:
                self.packet += data
            
            if format.FORMAT_END_BYTES in format.rx_format:
                for i in xrange(len(data) - len(format.end_bytes) + 1):
                    if data[-i - len(format.end_bytes):-i] == bytearray(format.end_bytes):
                        self.new_data_received.emit(self.packet[:-i - len(format.end_bytes)])
                        self.old_data = self.packet[-i:]
                        self.packet = bytearray('')
                        break
            else:
                if len(self.packet) >= self.buffer_size:
                    self.new_data_received.emit(self.packet[:self.buffer_size])
                    self.old_data = self.packet[self.buffer_size:]
                    self.packet = bytearray('')


class SerialConnection(Connection):
    
    TAG = "[SerialConnection]"
    
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
            print self.TAG, "Closing serial port"
            self.io_conn.close()
    
    def begin(self,  instrument):
        try:
            self.io_conn = serial.Serial()
            self.io_conn.port = instrument.connection.port
            self.io_conn.baudrate = instrument.connection.baudrate
            self.io_conn.bytesize = self.BYTESIZE[instrument.connection.data_bits]
            self.io_conn.parity = self.PARITY[instrument.connection.parity]
            self.io_conn.stopbits = self.STOPBITS[instrument.connection.stop_bits]
            self.io_conn.timeout = 0 # non-blocking mode (return immediately on read)
            self.io_conn.open()
        except serial.SerialException:
            print self.TAG,  "Device can not be found or can not be configured"
            raise
        
        Connection.begin(self, instrument)
    
    def run(self):
        # TODO: initialization of instrument if needed
        
        notifier = QSocketNotifier(self.io_conn.fileno(), QSocketNotifier.Read)
        notifier.activated.connect(self.read_data)
        
        # TODO: TMP #
#        self.timer.start(1000)
        # END TMP #
        
        Connection.run(self)
    
    # TODO: TMP #
#    def on_timeout(self):
#        self.io_conn.write('\x11')
    # END TMP #


class BlockingSerialConnection(SerialConnection):
    
    TAG = "[BlockingSerialConnection]"
    
    RX_TIMEOUT = 5000
    
    def __init__(self):
        SerialConnection.__init__(self)
        
        self.rx_timeout = QTimer()
        self.rx_timeout.setSingleShot(True)
    
    def run(self):
        # send command after receiving a response packet
        self.new_data_received.connect(self.send_command)
        
        # define a timeout, if response not received send the command again
        self.rx_timeout.timeout.connect(self.send_command_timeout)
        self.rx_timeout.start(self.RX_TIMEOUT)
        
        # send the first command
        self.send_command()
        
        SerialConnection.run(self)
    
    def send_command(self):
        self.io_conn.write('\x11')
        
        # restart reception timeout
        self.rx_timeout.start(self.RX_TIMEOUT)
    
    def send_command_timeout(self):
        print self.TAG, "Timeout! response packet not received"
        self.send_command()


class FileConnection(Connection):
    
    TAG = "[FileConnection]"
    
    def __del__(self):
        if self.io_conn:
            print self.TAG, "Closing input file"
            self.io_conn.close()

    def begin(self,  instrument, file_name):
        try:
            self.io_conn = open(file_name,  'rb')
        except IOError:
            print self.TAG, "The file does not exist, exiting gracefully"
            self.quit()
        
        Connection.begin(self, instrument)
    
    def run(self):
        self.read_data(self.io_conn.fileno())
        
        Connection.run(self)
