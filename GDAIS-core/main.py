from PyQt4.QtCore import pyqtSignal, QCoreApplication, QEventLoop, QObject, QSignalMapper, QString, QThread, QTimer, QUrl
from PyQt4.QtNetwork import QNetworkAccessManager, QNetworkRequest, QTcpServer

import argparse
from collections import deque
import logging
import logging.handlers
import os
import sys

from connection import Connection
from equipment import Equipment, InstrumentConfig, Command
from parser import Parser, ParsedPacket
from recorder import Recorder

class GDAIS(QCoreApplication):
    
    BASE_PATH = '/home/pau/feina/UPC/projecte/code/GDAIS/GDAIS-core'
    
    # Signal to inform that a notification has to be sent
    notify = pyqtSignal(str)

    def __init__(self, argv):
        QCoreApplication.__init__(self, argv)
        
        # parse commandline arguments
        parser = argparse.ArgumentParser(description='General Data Acquisition and Instrument control System (GDAIS)')
        parser.add_argument('equipment',  help='Equipment file (.json) to work with')
        parser.add_argument('-d', action='store_true', default=False, dest='background',
                                            help='Run in background')
        
        args = parser.parse_args()
        self.equipment_file = os.path.abspath(args.equipment)
        self.in_background = args.background
        
        # output logging
        logging.basicConfig(
                            level=logging.DEBUG,
                            format="%(asctime)s [%(name)s] %(levelname)s: %(message)s", 
                            filename=os.path.join(self.BASE_PATH, 'debug.log'),
                            filemode='w')
        self.log = logging.getLogger("GDAIS")
        
        # control server for GDAIS remote control
        self.control_server = ControlServer()
        
        # notifier of GDAIS events to an external server
        self.notifier = Notifier()

        # lists to store instrument controller and initialization threads
        self.instrument_init_controllers = []
        self.instrument_controllers = []

        # create data recorder thread
        self.recorder = Recorder()
        
        # schedule start event to be run when the execution loop starts
        QTimer.singleShot(0, self.start)
    
    def start(self):
        self.log.info("Welcome to GDAIS!")
        
        # start server for remote control
        self.control_server.quit_command_received.connect(self.quit)
        self.control_server.start()

        # load equipment from given file
        self.log.debug("Equipment file: '{0}'".format(self.equipment_file))
        try:
            equipment = Equipment(self.equipment_file)
        except IOError:
            self.log.exception("Couldn't load equipment file")
            QTimer.singleShot(0, self.quit) # exit GDAIS
            return
        
        # start sending logging events to control interface if running in background
        if self.in_background:
            host = '127.0.0.1:6543'
            url = '/log/{0}'.format(equipment.short_name)
            httpHandler = logging.handlers.HTTPHandler(host, url, method='POST')
            httpHandler.setLevel(logging.DEBUG)
            self.log.addHandler(httpHandler)
        
        # load notifier and start it
        self.notifier.equipment = equipment.short_name
        self.notify.connect(self.notifier.notify)
        self.notifier.start()
        
        # notify start event
        self.notify.emit('start')
        
        # start data recorder thread
        self.recorder.begin(equipment)
        
        for instrument_config in equipment.instruments:
                # create instrument controller thread
                instr_ctrl = InstrumentController.create(instrument_config)
                instr_ctrl.new_packet.connect(self.recorder.on_new_packet)
                instr_ctrl.error_ocurred.connect(self.quit)
                
                # store the instrument controller instance
                self.instrument_controllers.append(instr_ctrl)

                # initialize instrument if needed
                if instrument_config.init_commands:
                    instr_init = InstrumentInitialization(instrument_config)
                    instr_init.initialization_finished.connect(instr_ctrl.begin)
                    instr_init.error_ocurred.connect(self.quit)
                
                    # store the init instrument controller instance
                    self.instrument_init_controllers.append(instr_init)
                    
                    self.log.debug("Initialization ready to start")
                    instr_init.begin()
                    
                else:
                    txt = "Instrument '{0}' has no initial configuration"
                    self.log.info(txt.format(instrument_config.instrument.name))
                    instr_ctrl.begin()
    
    def quit(self):
        self.log.info("Exiting!")

        # finish all running instrument initialization threads
        for init_ctrl in self.instrument_init_controllers:
            if init_ctrl.isRunning():
                init_ctrl.quit()
                init_ctrl.wait()
        
        # finish all running instrument controller threads
        for instr_ctrl in self.instrument_controllers:
            if instr_ctrl.isRunning():
                instr_ctrl.quit()
                instr_ctrl.wait()
        
        # finish the data recorder thread if running
        if self.recorder.isRunning():
            self.log.debug("Closing data recorder...")
            self.recorder.quit()
            self.recorder.wait()
        
        # finish notifier thread
        if self.notifier.isRunning():
            self.log.debug("Closing notifier...")
            self.notifier.quit()
            self.notifier.wait()
        
        self.log.info("Goodbye!")
        QCoreApplication.quit()


class ControlServer(QObject):
    
    # Signal to inform that the quit command has been received and the system should exit
    quit_command_received = pyqtSignal()
    
    def __init__(self):
        QObject.__init__(self)
        
        # logging instance
        self.log = logging.getLogger('GDAIS.ControlServer')
        
        # TCP server to listen for control commands
        self.tcp_server = QTcpServer()
    
    def start(self):
        self.log.info("Starting TCP server...")
        if self.tcp_server.listen(port = 12345):
            txt = "Listening at http://localhost:{0} for commands"
            self.log.info(txt.format(self.tcp_server.serverPort()))
            self.tcp_server.newConnection.connect(self._accept_connection)
        else:
            self.log.warn("Unable to start: {0}".format(self.tcp_server.errorString()))

            # define a timer to auto-quit the app after 10 sec
            timeout = 10 # seconds
            self.log.warn("GDAIS will run for {0} seconds and then die.".format(timeout))
            self.timer = QTimer()
            self.timer.timeout.connect(self.quit)
            self.timer.start(timeout * 1000) # msec
    
    def quit(self):
        if self.tcp_server.isListening():
            self.tcp_server.close()
        self.quit_command_received.emit()
    
    def _accept_connection(self):
        self.tcp_connection = self.tcp_server.nextPendingConnection()
        self.tcp_connection.readyRead.connect(self._read_data)
        self.tcp_connection.error.connect(self._error_ocurred)
        
        self.log.debug("Accepted connection")
    
    def _read_data(self):
        tcp_data = self.tcp_connection.readAll()
        if tcp_data == 'quit':
            self.log.info("Received 'quit' command")
            self.quit()
        else:
            self.log.error("Received unknown command: {0}".format(tcp_data))
    
    def _error_ocurred(self, socket_error):
        self.log.error("TCP error occurred: {0}".format(self.tcp_connection.errorString()))


class Notifier(QThread):
    
    SERVER_URL = "http://127.0.0.1:6543"
    
    def __init__(self):
        QThread.__init__(self)
        
        # logging instance
        self.log = logging.getLogger('GDAIS.Notifier')
        
        # Network manager to send notifications
        self.manager = QNetworkAccessManager()
        self.manager.finished.connect(self._reply_finished)
        
        # Name of the equipment to notify (needs to be initialized before calling notify)
        self.equipment = ''
        
        # flag for when quit command is received
        self.exiting = False
    
    def quit(self):
        loop = QEventLoop()
        reply = self._make_request('quit')
        reply.finished.connect(loop.quit)
        loop.exec_()
        
        del self.manager
        QThread.quit(self)
    
    def notify(self, event):
        reply = self._make_request(event)
    
    def _make_request(self, event):
        url = QUrl("{0}/notify_{1}/{2}".format(self.SERVER_URL, event, self.equipment))
        self.log.debug("Sending notification for '{0}' event to {1}.".format(event, url.toString()))
        reply = self.manager.get(QNetworkRequest(url))
        reply.error.connect(self._reply_error)
        return reply
    
    def _reply_finished(self, network_reply):
        self.log.debug("Reply received: {0}".format(network_reply.readAll()))
    
    def _reply_error(self, network_error):
        self.log.error("Error receiving reply: {0}".format(network_error))


class InstrumentController(QThread):

    # Signal for new packet received event
    new_packet = pyqtSignal(ParsedPacket)

    # Signal for new command ready to send event
    new_command = pyqtSignal(Command)
    
    # Signal to inform that an error ocurred while controlling the instrument
    error_ocurred = pyqtSignal()
    
    @staticmethod
    def create(instrument_config, *args, **kwds):
        om = InstrumentConfig.OperationMode
        controller = {
            om.periodic: PeriodicInstrumentController,
            om.sequences: SequenceInstrumentController,
            om.blocking: BlockingInstrumentController
        }.get(instrument_config.operation_mode, None)

        if not controller:
            txt = "Instrument's operation mode {0} type not implemented"
            raise Exception(txt.format(instrument_config.operation_mode))

        return controller(instrument_config, *args, **kwds)

    def __init__(self, instrument_config):
        QThread.__init__(self)

        # logging instance
        self.log = logging.getLogger('GDAIS.'+instrument_config.instrument.short_name)

        # config of the instrument this controller is connected to
        self.instr_cfg = instrument_config
        
        self.log.debug("Creating connection and parser...")
        
        # parser thread
        self.parser = Parser()

        # connection thread
        self.connection = Connection.create(self.instr_cfg.instrument.connection)
        
        # wether quit() has been called, so we are exiting the thread
        self.exiting = False

        # how many errors have ocurred
        self.errors = 0

    def begin(self):
        self.log.info("Preparing parser...")
        # rx signal (parser -> self)
        self.parser.new_packet_parsed.connect(self.log_new_packet_parsed)
        self.parser.new_packet_parsed.connect(self.on_new_packet_parsed)
        # tx signal (self -> parser)
        self.new_command.connect(self.parser.on_new_command)
        
        self.parser.begin(self.instr_cfg.instrument)

        self.log.info("Preparing connection...")
        # rx signal (connection -> parser)
        self.connection.new_data_received.connect(self.parser.on_new_data_received)
        # tx signal (parser -> connection)
        self.parser.new_data_ready.connect(self.connection.send_data)
        # connection errors
        self.connection.error_occurred.connect(self.on_error)
        
        self.connection.begin(self.instr_cfg.instrument)

        if self.errors == 0 and not self.exiting:
            self.log.info("Starting!")
            self.start()
        else:
            self.log.info("Not starting as there has been an error")

    def quit(self):
        if not self.exiting:
            self.exiting = True
            
            if self.connection.isRunning():
                self.log.debug("Closing connection...")
                self.connection.quit()
                self.connection.wait()
            
            if self.parser.isRunning():
                self.log.debug("Closing parser...")
                self.parser.quit()
                self.parser.wait()
            
            self.log.debug("Ending InstrumentController thread")
            QThread.quit(self)
        
        else:
            self.log.error("quit() called twice!")

    def on_new_packet_parsed(self, packet):
        # inform new packet received to the listening classes (e.g.: Recorder)
        self.new_packet.emit(packet)

    def log_new_packet_parsed(self, packet):
        # log the event
        self.log.info("New '{0}' packet received".format(packet.instrument_packet.name))
        if packet.data:
            fields = [str(f.name) for f in packet.instrument_packet.fields]
            str_fields = ', '.join(["{0}: {1:g}".format(f, d) for f, d in zip(fields, packet.data)])
            self.log.debug("({0})".format(str_fields))
    
    def on_error(self):
        self.log.error("Error occurred!")
        self.error_ocurred.emit()
        self.errors += 1


class BlockingInstrumentController(InstrumentController):

    RX_TIMEOUT = 2000

    def __init__(self, instrument_config):
        InstrumentController.__init__(self, instrument_config)

        # circular list of operation commands
        self.commands = deque([command
            for command in instrument_config.operation_commands
                for i in xrange(command.param)])

        self.rx_timeout = QTimer()
        self.rx_timeout.setSingleShot(True)
    
    def run(self):
        # define a timeout, if response not received send the command again
        self.rx_timeout.timeout.connect(self.send_command_timeout)
        self.rx_timeout.start(self.RX_TIMEOUT)

        # send the first command
        self.send_next_command()

        InstrumentController.run(self)
    
    def quit(self):
        self.rx_timeout.stop()
        InstrumentController.quit(self)
    
    def on_new_packet_parsed(self, packet):
        InstrumentController.on_new_packet_parsed(self, packet)
        self.send_next_command()
    
    def send_next_command(self):
        self.new_command.emit(self.commands[0])

        # advance command list
        self.commands.rotate(-1)

        # restart reception timeout
        self.rx_timeout.start(self.RX_TIMEOUT)

    def send_command_timeout(self):
        self.log.warn("Timeout! response packet not received")

        # send next command
        self.send_next_command()


class InstrumentInitialization(BlockingInstrumentController):
    
    # Signal to inform that the instrument initialization has been completed correctly
    initialization_finished = pyqtSignal()

    def __init__(self, instrument_config):
        BlockingInstrumentController.__init__(self, instrument_config)
        self.log = logging.getLogger('GDAIS.'+instrument_config.instrument.short_name+'.Init')

        # list of init commands
        self.commands = deque(instrument_config.init_commands)
        self.current_command = None

    def begin(self):
        self.log.info("Starting instrument initialization")
        BlockingInstrumentController.begin(self)
    
    def quit(self):
        BlockingInstrumentController.quit(self)
        self.log.debug("Instrument initialization finished!")

    def on_new_packet_parsed(self, packet):
        if not self.exiting:
            # check init command reply
            # TODO: TEMP #
            self.log.debug("Received packet:")
            InstrumentController.log_new_packet_parsed(self, packet)
            self.log.debug("Expected reply:")
            fields = [str(f.name) for f in packet.instrument_packet.fields]
            str_fields = ', '.join(["{0}: {1}".format(f, d)
                                                    for f, d in zip(fields, self.current_command.reply.values)])
            self.log.debug("({0})".format(str_fields))
            # END TEMP #
            
            # if no reply received stop initialization
            if False:
                self.log.error("Wrong reply received")
                self.end_initialization(error=True)
            
            self.send_next_command()
            
        else:
            self.log.warn("Received packet while exiting initialization")
    
    def log_new_packet_parsed(self, packet):
        pass # TODO: really??

    def send_next_command(self):
        # check if there are more init commands to send
        if self.commands:
            # send next command
            self.current_command = self.commands.popleft()
            self.new_command.emit(self.current_command)

            # restart reception timeout
            self.rx_timeout.start(self.RX_TIMEOUT)
            
        else:
            self.end_initialization()

    def send_command_timeout(self):
        self.log.error("Timeout! init command reply not received")
        self.end_initialization(error=True)
    
    def end_initialization(self, error=False):
        if error:
            self.log.error("Ending initialization as there has been an error")
            self.error_ocurred.emit()
        else:
            self.log.info("All init commands sent correctly, ending initialization")
            self.initialization_finished.emit()
            self.quit()


class NonBlockingInstrumentController(InstrumentController):
    pass


class PeriodicInstrumentController(NonBlockingInstrumentController):

    def __init__(self, instrument_config):
        NonBlockingInstrumentController.__init__(self, instrument_config)
        
        self.mapper = QSignalMapper()
        self.timers = []
    
    def run(self):
        # create and start periodic timers for each command
        for i, command in enumerate(self.instr_cfg.operation_commands):
            self.log.debug("Creating timer for '{0}' command".format(command.name))
            timer = QTimer()
            timer.timeout.connect(self.mapper.map)
            self.mapper.setMapping(timer, i)
            timer.start(command.param)
            self.timers.append(timer)

        self.mapper.mapped.connect(self.send_command)
        
        NonBlockingInstrumentController.run(self)
    
    def quit(self):
        for timer in self.timers:
            timer.stop()
        NonBlockingInstrumentController.quit(self)

    def send_command(self, num):
        self.new_command.emit(self.instr_cfg.operation_commands[num])


class SequenceInstrumentController(NonBlockingInstrumentController):

    def __init__(self, instrument_config):
        NonBlockingInstrumentController.__init__(self, instrument_config)

        # circular list of command sequence
        self.commands = deque(instrument_config.operation_commands)

        self.tx_timer = QTimer()
        self.tx_timer.setSingleShot(True)

    def run(self):
        # define the timer used to wait for the next command
        self.tx_timer.timeout.connect(self.send_command)

        # send the first command
        self.send_command()

        NonBlockingInstrumentController.run(self)
    
    def quit(self):
        self.tx_timer.stop()
        NonBlockingInstrumentController.quit(self)

    def send_command(self):
        # send next command
        cmd = self.commands[0]
        self.new_command.emit(cmd)

        # wait for next command
        self.tx_timer.start(cmd.param)

        # advance command list
        self.commands.rotate(-1)



if __name__ == "__main__":
    
    gdais = GDAIS(sys.argv)
    sys.exit(gdais.exec_())
