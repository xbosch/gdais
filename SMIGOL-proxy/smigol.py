#!/usr/bin/env python
from PyQt4.QtCore import pyqtSignal, QCoreApplication, QEventLoop, QObject, QString, QTimer
from PyQt4.QtNetwork import QTcpServer, QTcpSocket

import logging
import serial
import sys
import time

# constants
SERIAL_PORT = "/dev/ttyUSB0"
DL_END_MARK = "Fin DL"
BUFFER_SIZE = 10

# classes
class TCPServer(QObject):
    
    def __init__(self, port):
        QObject.__init__(self)
        
        # logging instance
        self.log = logging.getLogger('SMIGOL.TCPServer.{0}'.format(port))
        
        # TCP server to listen for control commands
        self.tcp_server = QTcpServer()
        
        # TCP server listenning port
        self.tcp_port = port
        
        # TCP socket connection
        self.tcp_connection = None
        
    def start(self):
        self.log.info("Starting TCP server...")
        if self.tcp_server.listen(port = self.tcp_port):
            txt = "Listening at http://localhost:{0} for a connection"
            self.log.info(txt.format(self.tcp_server.serverPort()))
            self.tcp_server.newConnection.connect(self._accept_connection)
        else:
            self.log.critical("Unable to start: {0}".format(self.tcp_server.errorString()))
    
    def disconnect(self):
        if self.tcp_connection and self.tcp_connection.state() == QTcpSocket.ConnectedState:
            loop = QEventLoop()
            self.tcp_connection.disconnected.connect(loop.quit)
            self.tcp_connection.disconnectFromHost()
            self.log.debug("Entering disconnect state...")
            if self.tcp_connection.state() == QTcpSocket.ConnectedState:
                loop.exec_()
            self.log.debug("Done waiting, closing server...")
        if self.tcp_server.isListening():
            self.tcp_server.close()
        self.log.info("Server closed")
    
    def _accept_connection(self):
        if not self.tcp_connection:
            self.tcp_connection = self.tcp_server.nextPendingConnection()
            self.tcp_connection.error.connect(self._error_occurred)
            
            txt = "Accepted connection"
            self.log.debug(txt.format(self.tcp_server.serverPort()))
            
        else:
            self.log.warning("Received a second connection, ignoring it...")
            self.tcp_server.nextPendingConnection()
    
    def _error_occurred(self, socket_error):
        if socket_error == QTcpSocket.RemoteHostClosedError:
            self.log.info(self.tcp_connection.errorString())
        else:
            self.log.error(self.tcp_connection.errorString())


class ProxyServer(TCPServer):
    
    # Signal to inform that all data from the datalogger has been received
    reception_finished = pyqtSignal()
    
    def __init__(self, dl_num):
        port = 20000 + dl_num
        TCPServer.__init__(self, port=port)
        
        # logging instance
        self.log = logging.getLogger('SMIGOL.ProxyServer.{0}'.format(self.tcp_port))
        
        # number of the datalogger being read
        self.dl = dl_num
        
        # whether the server has started acquiring
        self.started = False
    
        # whether the server has started acquiring
        self.finished = False
    
    def begin_acquiring(self):
        if self.tcp_connection:
            self.log.info("Starting acquisition")
            self.started = True
            
            if False: # READING FROM FILE, FOR DEBUGGING
                txt = "Acquiring SMIGOL data! (by {0})\n"
                self.tcp_connection.write(txt.format(self.tcp_port))
                
                with open('test.bin', 'r') as fp:
                    # read first bytes
                    data = fp.read(10)
                    while data:
                        # write
                        self.tcp_connection.write(data)
                        
                        # wait
                        loop = QEventLoop()
                        QTimer.singleShot(2, loop.quit)
                        loop.exec_()

                        # read more
                        data = fp.read(10)
                
                self.tcp_connection.write("Finished!\n".format(self.tcp_port))
            # END DEBUGGING CODE

            ser = serial.Serial(SERIAL_PORT, timeout=1)
            self.log.debug("Serial port open: {0}".format(ser.portstr))
            datalogger = "DL{0}".format(self.dl)
            self.log.debug("Sending '{0}' through serial port".format(datalogger))
            ser.write(datalogger)
            
            # DEBUG
            #txt = "Acquiring SMIGOL data! (by {0})\n"
            #self.tcp_connection.write(txt.format(self.tcp_port))
                
            buff = ''
            while not buff.endswith(DL_END_MARK):
                data = ser.read(BUFFER_SIZE)
                if data:
                    #self.log.debug("Rx: {0}".format([c for c in data]))
                    self.tcp_connection.write(data)
                    buff = buff[-BUFFER_SIZE:] + data

                    # wait
                    loop = QEventLoop()
                    QTimer.singleShot(0, loop.quit)
                    loop.exec_()
            
            self.log.info("Acquisition finished")

            # DEBUG
            #self.tcp_connection.write("Finished!\n".format(self.tcp_port))
            
        else:
            self.log.error("Tried to start acquiring before establishing a connection")
        self.reception_finished.emit()


class ControlServer(TCPServer):

    # Signal to inform that start command has been received
    start_received = pyqtSignal()
    
    # Signal to inform that quit command has been received
    quit_app = pyqtSignal()

    def __init__(self):
        TCPServer.__init__(self, port=20000)
        
        # logging instance
        self.log = logging.getLogger('SMIGOL.ControlServer.{0}'.format(self.tcp_port))

        # whether all proxies have finished sending data
        self.all_finished = False

        # whether quit command has been received
        self.quit_received = False
        
    def last_finished(self):
        self.all_finished = True
        if self.quit_received:
            self.quit_app.emit()
    
    def _accept_connection(self):
        TCPServer._accept_connection(self)
        self.tcp_connection.readyRead.connect(self._read_data)
    
    def _read_data(self):
        tcp_data = self.tcp_connection.readAll()
        if tcp_data == 's':
            self.log.info("Received 'start' command")
            self.start_received.emit()
        elif tcp_data == 'q':
            self.log.info("Received 'quit' command")
            self.quit_received = True
            if self.all_finished:
                self.quit_app.emit()
            else:
                self.log.warning("Command received before acquisition completed, scheduling quit")
        else:
            self.log.warning("Received unknown command: {0}".format(tcp_data))
    
    def _error_occurred(self, socket_error):
        TCPServer._error_occurred(self, socket_error)
        
        # exit app when a TCP error occurs
        self.quit_app.emit()



if __name__ == "__main__":
    
    # output logging
    logging.basicConfig(
                        level=logging.DEBUG,
                        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
    log = logging.getLogger("SMIGOL")    

    # application
    app = QCoreApplication(sys.argv)

    control_server = ControlServer()
    control_server.quit_app.connect(app.quit)
    app.aboutToQuit.connect(control_server.disconnect)
    QTimer.singleShot(0, control_server.start)
    
    proxies = [None] * 4
    for i in range(4):
        proxy = ProxyServer(dl_num=i+1)
        if i >0:
            proxies[i-1].reception_finished.connect(proxy.begin_acquiring)
        QTimer.singleShot(0, proxy.start)
        app.aboutToQuit.connect(proxy.disconnect)
        proxies[i] = proxy
    
    control_server.start_received.connect(proxies[0].begin_acquiring)
    proxies[3].reception_finished.connect(control_server.last_finished)

    # run!
    log.info('starting event loop...')
    r = app.exec_()
    log.info('exiting event loop...')
    sys.exit(r)
