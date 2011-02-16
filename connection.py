from PyQt4.QtCore import pyqtSignal, QSocketNotifier, QThread, QTimer
import serial


class Connection(QThread):
    
    DEFAULT_BUFFER_SIZE = 8
    
    # Signal for new data packet received event
    new_data_received = pyqtSignal(bytearray)
    
    def __init__(self, parent = None):
        QThread.__init__(self, parent)

    def begin(self,  instrument):
        self.instrument = instrument
        self.packet = bytearray('')
        self.old_data = None
        print self.TAG, "Connected:", self.input
        
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
            data = self.input.read(self.buffer_size)
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
    
    # TODO: TMP #
    def __init__(self, parent = None):
        Connection.__init__(self,  parent)
        self.timer = QTimer()
        self.timer.timeout.connect(self.on_timeout)
    # END TMP #
    
    def __del__(self):
        if self.input:
            print self.TAG, "Closing serial port"
            self.input.close()

    def begin(self,  instrument):
        try:
            self.input = serial.Serial()
            self.input.port = instrument.connection.port
            self.input.baudrate = instrument.connection.baudrate
            self.input.bytesize = self.BYTESIZE[instrument.connection.data_bits]
            self.input.parity = self.PARITY[instrument.connection.parity]
            self.input.stopbits = self.STOPBITS[instrument.connection.stop_bits]
            self.input.timeout = 0 # non-blocking mode (return immediately on read)
            self.input.open()
        except serial.SerialException:
            print self.TAG,  "Device can not be found or can not be configured"
            raise
        
        Connection.begin(self, instrument)
    
    def run(self):
        # TODO: initialization of instrument if needed
        
        notifier = QSocketNotifier(self.input.fileno(), QSocketNotifier.Read)
        notifier.activated.connect(self.read_data)
        
        # TODO: TMP #
        self.timer.start(1000)
        # END TMP #
        
        Connection.run(self)
    
    # TODO: TMP #
    def on_timeout(self):
        self.input.write('\x11')
    # END TMP #


class FileConnection(Connection):
    
    TAG = "[FileConnection]"
    
    def __del__(self):
        if self.input:
            print self.TAG, "Closing input file"
            self.input.close()

    def begin(self,  instrument, file_name):
        try:
            self.input = open(file_name,  'rb')
        except IOError:
            print self.TAG, "The file does not exist, exiting gracefully"
            self.quit()
        
        Connection.begin(self, instrument)
    
    def run(self):
        self.read_data(self.input.fileno())
        
        Connection.run(self)
