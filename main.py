from PyQt4.QtCore import pyqtSignal, QCoreApplication, QSignalMapper, QString, QThread, QTimer
from PyQt4.QtNetwork import QTcpServer

import logging, sys
from collections import deque

from connection import Connection
from equipment import Equipment, InstrumentConfig, Command
from parser import Parser, ParsedPacket
from recorder import Recorder

class GDAIS(object):

    def __init__(self):
        logging.basicConfig(
                            level=logging.DEBUG,
                            format="[%(name)s] %(levelname)s: %(message)s", 
                            stream=sys.stdout)
        self.log = logging.getLogger("GDAIS")
        self.log.info("Welcome to GDAIS!")

    def start(self, filename):
        equipment = Equipment(filename)

        self.recorder = Recorder()
        self.recorder.begin(equipment)

        for instrument_config in equipment.instruments:
            # create instrument controller
            self.instr_ctrl = InstrumentController.create(instrument_config)
            self.instr_ctrl.new_packet.connect(self.recorder.on_new_packet)

            # initialize instrument if needed --> TODO: enable
            if False and instrument_config.init_commands:
                self.instr_init = InstrumentInitialization(instrument_config)
                self.instr_init.finished.connect(self.instr_ctrl.begin)
                self.instr_init.begin()
            else:
                self.instr_ctrl.begin()

        self.start_tcp_server()

    def start_tcp_server(self):
        self.log.info("TCP server: Starting...")
        self.tcp_server = QTcpServer()
        if self.tcp_server.listen(port = 12345):
            txt = "TCP server: open a connection to http://localhost:{0} to quit GDAIS"
            self.log.info(txt.format(self.tcp_server.serverPort()))
            self.tcp_server.newConnection.connect(app.quit)
        else:
            self.log.warn("Unable to start TCP server: {0}".format(self.tcp_server.errorString()))

            # define a timer to auto-quit the app after 10 sec
            timeout = 10*1000
            self.log.info("GDAIS will run for {0} seconds and then die.".format(timeout/1000))
            self.timer = QTimer()
            self.timer.timeout.connect(app.quit)
            self.timer.start(timeout)


class InstrumentController(QThread):

    # Signal for new packet received event
    new_packet = pyqtSignal(ParsedPacket)

    # Signal for new command ready to send event
    new_command = pyqtSignal(Command)

    def __init__(self, instrument_config):
        QThread.__init__(self)
        self.log = logging.getLogger('GDAIS.'+instrument_config.instrument.short_name)
        self.instr_cfg = instrument_config

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

    def begin(self):
        self.log.info("Creating parser...")
        self.parser = Parser()
        # rx signal (parser -> self)
        self.parser.new_packet_parsed.connect(self.on_new_packet_parsed)
        # tx signal (self -> parser)
        self.new_command.connect(self.parser.on_new_command)
        self.parser.begin(self.instr_cfg.instrument)

        self.log.info("Creating connection...")
        self.connection = Connection.create(self.instr_cfg.instrument.connection)
        # rx signal (connection -> parser)
        self.connection.new_data_received.connect(self.parser.on_new_data_received)
        # tx signal (parser -> connection)
        self.parser.new_data_ready.connect(self.connection.send_data)
        self.connection.begin(self.instr_cfg.instrument)

        self.log.info("Starting!")

        self.start()

    def run(self):
        self.exec_()

    def on_new_packet_parsed(self, packet):
        # inform new packet received to the listening classes (e.g.: Recorder)
        self.new_packet.emit(packet)

        # log the event
        self.log.info("New '{0}' packet received".format(packet.instrument_packet.name))
        if packet.data:
            fields = [str(f.name) for f in packet.instrument_packet.fields]
            str_fields = ', '.join(["{0}: {1:g}".format(f, d) for f, d in zip(fields, packet.data)])
            self.log.info("({0})".format(str_fields))


class InstrumentInitialization(InstrumentController):

    def __init__(self, instrument_config):
        InstrumentController.__init__(self, instrument_config)
        self.log = logging.getLogger('GDAIS.'+instrument_config.instrument.short_name+'.Init')

    def on_new_packet_parsed(self, packet):
        InstrumentController.on_new_packet_parsed(self, packet)


class BlockingInstrumentController(InstrumentController):

    RX_TIMEOUT = 5000

    def __init__(self, instrument_config):
        InstrumentController.__init__(self, instrument_config)

        # circular list of commands
        self.commands = deque([command
            for command in instrument_config.operation_commands
                for i in xrange(command.param)])

        self.rx_timeout = QTimer()
        self.rx_timeout.setSingleShot(True)

    def run(self):
        # send command after receiving a response packet
        self.parser.new_packet_parsed.connect(self.send_command)

        # define a timeout, if response not received send the command again
        self.rx_timeout.timeout.connect(self.send_command_timeout)
        self.rx_timeout.start(self.RX_TIMEOUT)

        # send the first command
        self.send_command()

        InstrumentController.run(self)

    def send_command(self):
        # send next command
        self.new_command.emit(self.commands[0])

        # advance command list
        self.commands.rotate(-1)

        # restart reception timeout
        self.rx_timeout.start(self.RX_TIMEOUT)

    def send_command_timeout(self):
        self.log.info("Timeout! response packet not received")

        # send again last command
        self.commands.rotate(1)
        self.send_command()


class NonBlockingInstrumentController(InstrumentController):
    pass


class PeriodicInstrumentController(NonBlockingInstrumentController):

    def __init__(self, instrument_config):
        NonBlockingInstrumentController.__init__(self, instrument_config)

        self.mapper = QSignalMapper()
        self.timers = []

        for i, command in enumerate(instrument_config.operation_commands):
            self.log.debug("Creating timer for '{0}' command".format(command.name))
            timer = QTimer()
            timer.timeout.connect(self.mapper.map)
            self.mapper.setMapping(timer, i)
            timer.start(command.param)
            self.timers.append(timer)

        self.mapper.mapped.connect(self.send_command)

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

    def send_command(self):
        # send next command
        cmd = self.commands[0]
        self.new_command.emit(cmd)

        # wait for next command
        self.tx_timer.start(cmd.param)

        # advance command list
        self.commands.rotate(-1)



if __name__ == "__main__":

    app = QCoreApplication(sys.argv)
    gdais = GDAIS()
    gdais.start("conf/equips/prova3.json")
    sys.exit(app.exec_())
