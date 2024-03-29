# -*- coding: utf-8 -*-

"""
Module implementing InstrumentEditorMainWindow.
"""

from PyQt4.QtGui import QFileDialog, QInputDialog, QLineEdit, QListWidgetItem, QMainWindow,  QMessageBox, QTreeWidgetItem
from PyQt4.QtCore import pyqtSignature, QString, Qt

import os

from Ui_instrumenteditor_mainwindow import Ui_InstrumentEditorMainWindow
from instrument import ConnectionCfg, Field, Instrument, PacketFormat
from instrument import PacketAlreadyExistsError, WrongPacketTypeError

class InstrumentEditorMainWindow(QMainWindow, Ui_InstrumentEditorMainWindow):
    """
    Class documentation goes here.
    """
    CONF_PATH = '{0}/conf'.format(os.getcwd())
    INSTRUMENT_PATH = '{0}/instruments'.format(CONF_PATH)
    
    FILEDIALOG_FILTER = "Instrument configuration (*.json)"
    
    def __init__(self, parent = None):
        """
        Constructor
        """
        QMainWindow.__init__(self, parent)
        self.setupUi(self)
        # TODO: temporally load always an instrument
        self.load_instrument(Instrument(self.INSTRUMENT_PATH + "/gps.json"))
        #self.load_instrument(Instrument())
    
    @pyqtSignature("")
    def on_action_New_triggered(self):
        self.load_instrument(Instrument())
    
    @pyqtSignature("")
    def on_action_Open_triggered(self):
        filename = QFileDialog.getOpenFileName(
                                            None,
                                            self.trUtf8("Select an instrument description file"),
                                            QString(self.INSTRUMENT_PATH),
                                            self.trUtf8(self.FILEDIALOG_FILTER),
                                            None)
        if filename:
            self.load_instrument(Instrument(str(filename)))
    
    @pyqtSignature("")
    def on_action_Save_triggered(self):
        filename = self.instrument.filename
        if not filename:
            filename = QFileDialog.getSaveFileName(
                                                None,
                                                self.trUtf8("Save instrument description file"),
                                                QString(self.INSTRUMENT_PATH),
                                                self.trUtf8(self.FILEDIALOG_FILTER),
                                                None)
        if filename:
            self.dump_instrument(str(filename))
            self.instrument.filename = str(filename)
    
    @pyqtSignature("")
    def on_action_Save_As_triggered(self):
        filename = QFileDialog.getSaveFileName(
                                            None,
                                            self.trUtf8("Save instrument description file"),
                                            QString(self.INSTRUMENT_PATH),
                                            self.trUtf8(self.FILEDIALOG_FILTER),
                                            None)
        if filename:
            self.dump_instrument(str(filename))
            self.instrument.filename = str(filename)
    
    @pyqtSignature("")
    def on_action_About_triggered(self):
        QMessageBox.information(self, "About", "GUI for editing Instrument descriptions in JSON.")
    
    @pyqtSignature("QString")
    def on_conn_type_currentIndexChanged(self, type):
        self.instrument.set_conn_type(str(type))
        self.load_connection()
    
    @pyqtSignature("")
    def on_conn_file_name_btn_clicked(self):
        filename = QFileDialog.getOpenFileName(
                                            None,
                                            self.trUtf8("Instrument input data file"),
                                            self.conn_file_name.text(),
                                            self.trUtf8(''),
                                            None)
        self.conn_file_name.setText(filename)
    
    @pyqtSignature("")
    def on_pf_add_start_byte_clicked(self):
        (text, ok) = QInputDialog.getText(\
            self,
            self.trUtf8("Start byte"),
            self.trUtf8("Insert start byte in hex form:"),
            QLineEdit.Normal,
            self.trUtf8("0x00"))
        if ok and text: # TODO: check hex form with regexp
            item = QListWidgetItem(str(text))
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            self.pf_start_bytes.addItem(item)
    
    @pyqtSignature("")
    def on_pf_delete_start_byte_clicked(self):
        self.pf_start_bytes.takeItem(self.pf_start_bytes.currentRow())
        #TODO: consider deletion of last item
    
    @pyqtSignature("QListWidgetItem*, QListWidgetItem*")
    def on_pf_start_bytes_currentItemChanged(self, current, previous):
        if not previous:
            self.pf_delete_start_byte.setEnabled(True)
            # TODO: when the list area is clicked on no item delete is also enabled!
        if not current:
            self.pf_delete_start_byte.setEnabled(False)
    
    @pyqtSignature("")
    def on_pf_add_end_byte_clicked(self):
        (text, ok) = QInputDialog.getText(\
            self,
            self.trUtf8("End byte"),
            self.trUtf8("Insert end byte in hex form:"),
            QLineEdit.Normal,
            self.trUtf8("0x00"))
        if ok and text: # TODO: check hex or dec form with regexp
            item = QListWidgetItem(str(text))
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            self.pf_end_bytes.addItem(item)
    
    @pyqtSignature("")
    def on_pf_delete_end_byte_clicked(self):
        self.pf_end_bytes.takeItem(self.pf_end_bytes.currentRow())
        #TODO: consider deletion last item
    
    @pyqtSignature("QListWidgetItem*, QListWidgetItem*")
    def on_pf_end_bytes_currentItemChanged(self, current, previous):
        if not previous:
            self.pf_delete_end_byte.setEnabled(True)
            # TODO: when the list area is clicked on no item delete is also enabled!
        if not current:
            self.pf_delete_end_byte.setEnabled(False)
    
    @pyqtSignature("QListWidgetItem*, QListWidgetItem*")
    def on_rx_packets_list_currentItemChanged(self, current, previous):
        if previous:
            self.save_packet(str(previous.text()), self.instrument.RX_PACKET)
        else:
            self.rx_packets_delete.setEnabled(True)
        
        if current:
            self.load_packet(str(current.text()), self.instrument.RX_PACKET)
        else:
            self.rx_packets_delete.setEnabled(False)
    
    @pyqtSignature("")
    def on_rx_packets_add_clicked(self):
        (text, ok) = QInputDialog.getText(\
            self,
            self.trUtf8("New Rx Packet"),
            self.trUtf8("Insert packet number:"),
            QLineEdit.Normal,
            self.trUtf8(""))
        if ok and text: # TODO: check correct packet number
            num = str(text)
            try:
                self.instrument.add_packet(int(num), self.instrument.RX_PACKET)
            except PacketAlreadyExistsError:
                QMessageBox.warning(None,
                    self.trUtf8("Packet already exists"),
                    self.trUtf8("""The entered packet number already exists, click on the existing one if you want to modify it."""),
                    QMessageBox.StandardButtons(\
                        QMessageBox.Close))
            else:
                item = QListWidgetItem(num)
                self.rx_packets_list.addItem(item)
                self.rx_packets_list.setCurrentItem(item)
    
    @pyqtSignature("")
    def on_rx_packets_delete_clicked(self):
        num = str(self.rx_packets_list.currentItem().text())
        self.rx_packets_list.takeItem(self.rx_packets_list.currentRow())
        self.instrument.delete_packet(int(num), self.instrument.RX_PACKET)
    
    @pyqtSignature("QTreeWidgetItem*, QTreeWidgetItem*")
    def on_rx_packets_fields_currentItemChanged(self, current, previous):
        if not previous:
            self.rx_packets_delete_field.setEnabled(True)
            # TODO: when the list area is clicked on no item delete is also enabled!
        if not current:
            self.rx_packets_delete_field.setEnabled(False)
    
    @pyqtSignature("")
    def on_rx_packets_add_field_clicked(self):
        item = QTreeWidgetItem([Field.EMPTY_FIELD, "uint8"])
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        self.rx_packets_fields.addTopLevelItem(item)
    
    @pyqtSignature("")
    def on_rx_packets_delete_field_clicked(self):
        item = self.rx_packets_fields.currentItem()
        index = self.rx_packets_fields.indexOfTopLevelItem(item)
        self.rx_packets_fields.takeTopLevelItem(index)
        #TODO: consider deletion last item
    
    @pyqtSignature("QListWidgetItem*, QListWidgetItem*")
    def on_tx_packets_list_currentItemChanged(self, current, previous):
        if previous:
            self.save_packet(str(previous.text()), self.instrument.TX_PACKET)
        else:
            self.tx_packets_delete.setEnabled(True)
        
        if current:
            self.load_packet(str(current.text()), self.instrument.TX_PACKET)
        else:
            self.tx_packets_delete.setEnabled(False)
    
    @pyqtSignature("")
    def on_tx_packets_add_clicked(self):
        (text, ok) = QInputDialog.getText(\
            self,
            self.trUtf8("New Tx Packet"),
            self.trUtf8("Insert packet number:"),
            QLineEdit.Normal,
            self.trUtf8(""))
        if ok and text: # TODO: check correct packet number
            num = str(text)
            try:
                self.instrument.add_packet(int(num), self.instrument.TX_PACKET)
            except PacketAlreadyExistsError:
                QMessageBox.warning(None,
                    self.trUtf8("Packet already exists"),
                    self.trUtf8("""The entered packet number already exists, click on the existing one if you want to modify it."""),
                    QMessageBox.StandardButtons(\
                        QMessageBox.Close))
            else:
                item = QListWidgetItem(num)
                self.tx_packets_list.addItem(item)
                self.tx_packets_list.setCurrentItem(item)
    
    @pyqtSignature("")
    def on_tx_packets_delete_clicked(self):
        num = str(self.tx_packets_list.currentItem().text())
        self.tx_packets_list.takeItem(self.tx_packets_list.currentRow())
        self.instrument.delete_packet(int(num), self.instrument.TX_PACKET)
    
    @pyqtSignature("QTreeWidgetItem*, QTreeWidgetItem*")
    def on_tx_packets_fields_currentItemChanged(self, current, previous):
        if not previous:
            self.tx_packets_delete_field.setEnabled(True)
            # TODO: when the list area is clicked on no item delete is also enabled!
        if not current:
            self.tx_packets_delete_field.setEnabled(False)
    
    @pyqtSignature("")
    def on_tx_packets_add_field_clicked(self):
        item = QTreeWidgetItem([Field.EMPTY_FIELD, "uint8"])
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        self.tx_packets_fields.addTopLevelItem(item)
    
    @pyqtSignature("")
    def on_tx_packets_delete_field_clicked(self):
        item = self.tx_packets_fields.currentItem()
        index = self.tx_packets_fields.indexOfTopLevelItem(item)
        self.tx_packets_fields.takeTopLevelItem(index)
        #TODO: consider deletion last item

    def load_packet(self, num, type):
        if type == self.instrument.RX_PACKET:
            packet = self.instrument.rx_packets[int(num)]
            self.rx_packets_num.setText(num)
            self.rx_packets_name.setText(packet.name)
            for field in packet.fields:
                item = QTreeWidgetItem([field.name, field.type])
                item.setFlags(item.flags() | Qt.ItemIsEditable)
                self.rx_packets_fields.addTopLevelItem(item)
            
        elif type == self.instrument.TX_PACKET:
            packet = self.instrument.tx_packets[int(num)]
            self.tx_packets_num.setText(num)
            self.tx_packets_name.setText(packet.name)
            for field in packet.fields:
                item = QTreeWidgetItem([field.name, field.type])
                item.setFlags(item.flags() | Qt.ItemIsEditable)
                self.tx_packets_fields.addTopLevelItem(item)
            
        else:
            raise WrongPacketTypeError(type)

    def save_packet(self, num, type):
        if type == self.instrument.RX_PACKET:
            packet = self.instrument.rx_packets[int(num)]
            packet.name = str(self.rx_packets_name.text())
            packet.fields = []
            for i in xrange(self.rx_packets_fields.topLevelItemCount()):
                item = self.rx_packets_fields.takeTopLevelItem(0)
                field = Field(str(item.text(0)), str(item.text(1)))
                packet.fields.append(field)
            
        elif type == self.instrument.TX_PACKET:
            packet = self.instrument.tx_packets[int(num)]
            packet.name = str(self.tx_packets_name.text())
            packet.fields = []
            for i in xrange(self.tx_packets_fields.topLevelItemCount()):
                item = self.tx_packets_fields.takeTopLevelItem(0)
                field = Field(str(item.text(0)), str(item.text(1)))
                packet.fields.append(field)
            
        else:
            raise WrongPacketTypeError(type)

    def load_connection(self):
        self.clear_connection()
        
        conn = self.instrument.connection
            
        if conn.type == ConnectionCfg.Type.file:
            self.conn_file_group.setEnabled(True)
            self.conn_file_name.setText(conn.filename)
        
        elif conn.type == ConnectionCfg.Type.serial:
            self.conn_serial_group.setEnabled(True)
            self.conn_serial_port.setText(conn.serial_port)
            self.conn_serial_baudrate.setText(str(conn.baudrate))
            self.conn_serial_data_bits.setText(str(conn.data_bits))
            self.conn_serial_parity.setText(conn.parity)
            self.conn_serial_stop_bits.setText(str(conn.stop_bits))
        
        elif conn.type == ConnectionCfg.Type.tcp:
            self.conn_tcp_group.setEnabled(True)
            self.conn_tcp_host.setText(conn.tcp_host)
            self.conn_tcp_port.setText(str(conn.tcp_port))
    
    def clear_connection(self):
        
        self.conn_file_group.setEnabled(False)
        self.conn_file_name.setText('')
        
        self.conn_serial_group.setEnabled(False)
        self.conn_serial_port.setText('')
        self.conn_serial_baudrate.setText('')
        self.conn_serial_data_bits.setText('')
        self.conn_serial_parity.setText('')
        self.conn_serial_stop_bits.setText('')
        
        self.conn_tcp_group.setEnabled(False)
        self.conn_tcp_host.setText('')
        self.conn_tcp_port.setText('')
    
    def save_connection(self):
        conn = self.instrument.connection
            
        if conn.type == ConnectionCfg.Type.file:
            conn.filename = str(self.conn_file_name.text())
        
        elif conn.type == ConnectionCfg.Type.serial:
            conn.serial_port = str(self.conn_serial_port.text())
            conn.baudrate = int(self.conn_serial_baudrate.text())
            conn.data_bits = int(self.conn_serial_data_bits.text())
            conn.parity = str(self.conn_serial_parity.text())
            conn.stop_bits = int(self.conn_serial_stop_bits.text())
        
        elif conn.type == ConnectionCfg.Type.tcp:
            conn.tcp_host = str(self.conn_tcp_host.text())
            conn.tcp_port = int(self.conn_tcp_port.text())

    def load_instrument(self, instrument):
        self.clear_instrument()
        
        self.instrument = instrument
        
        # base info
        self.instrument_name.setText(self.instrument.name)
        self.instrument_short_name.setText(self.instrument.short_name)
        self.byte_order.setCurrentIndex(self.byte_order.findText(self.instrument.byte_order))
        
        # connection
        self.conn_type.setCurrentIndex(self.conn_type.findText(self.instrument.connection.type))
        self.load_connection()
        
        # packet format
        for i, field in enumerate(self.instrument.packet_format.rx_format):
            combo_box = getattr(self, 'pf_rx_format_{0}'.format(i))
            combo_box.setCurrentIndex(combo_box.findText(field))
        
        for i, field in enumerate(self.instrument.packet_format.tx_format):
            combo_box = getattr(self, 'pf_tx_format_{0}'.format(i))
            combo_box.setCurrentIndex(combo_box.findText(field))
        
        for start_byte in self.instrument.packet_format.start_bytes:
            item = QListWidgetItem(hex(start_byte))
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            self.pf_start_bytes.addItem(item)
        
        for end_byte in self.instrument.packet_format.end_bytes:
            item = QListWidgetItem(hex(end_byte))
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            self.pf_end_bytes.addItem(item)
        
        # rx packets
        for num in self.instrument.rx_packets:
            self.rx_packets_list.addItem(str(num))
        if self.rx_packets_list.count():
            self.rx_packets_list.setCurrentItem(self.rx_packets_list.item(0))
        
        # tx packets
        for num in self.instrument.tx_packets:
            self.tx_packets_list.addItem(str(num))
        if self.tx_packets_list.count():
            self.tx_packets_list.setCurrentItem(self.tx_packets_list.item(0))
    
    def clear_instrument(self):
        self.clear_connection()
        
        none_index = 4 # TODO: improve
        for i in range(4):
            getattr(self, 'pf_rx_format_{0}'.format(i)).setCurrentIndex(none_index)
            getattr(self, 'pf_tx_format_{0}'.format(i)).setCurrentIndex(none_index)
        
        for byte in xrange(self.pf_start_bytes.count()):
            self.pf_start_bytes.takeItem(0)
        for byte in xrange(self.pf_end_bytes.count()):
            self.pf_end_bytes.takeItem(0)
            
        for packet in xrange(self.rx_packets_list.count()):
            self.rx_packets_list.takeItem(0)
        self.rx_packets_name.setText("")
        self.rx_packets_num.setText("")
        for packet in xrange(self.tx_packets_list.count()):
            self.tx_packets_list.takeItem(0)
        self.tx_packets_name.setText("")
        self.tx_packets_num.setText("")

    def dump_instrument(self, filename):
        # base info
        self.instrument.name = str(self.instrument_name.text())
        self.instrument.short_name = str(self.instrument_short_name.text())
        self.instrument.byte_order = str(self.byte_order.currentText())
        
        #connection
        self.save_connection()
        
        # packet format
        self.instrument.packet_format.rx_format = []
        for i in range(4):
            combo_box = getattr(self, 'pf_rx_format_{0}'.format(i))
            field = str(combo_box.currentText())
            if field != PacketFormat.FormatField.empty:
                self.instrument.packet_format.rx_format.append(field)
        
        self.instrument.packet_format.tx_format = []
        for i in range(4):
            combo_box = getattr(self, 'pf_tx_format_{0}'.format(i))
            field = str(combo_box.currentText())
            if field != PacketFormat.FormatField.empty:
                self.instrument.packet_format.tx_format.append(field)
        
        self.instrument.packet_format.start_bytes = []
        for i in xrange(self.pf_start_bytes.count()):
            self.instrument.packet_format.start_bytes.append(int(str(self.pf_start_bytes.item(i).text()), 0))
        
        self.instrument.packet_format.end_bytes = []
        for i in xrange(self.pf_end_bytes.count()):
            self.instrument.packet_format.end_bytes.append(int(str(self.pf_end_bytes.item(i).text()), 0))
        
        # rx packets
        if self.rx_packets_list.count():
            num = str(self.rx_packets_list.currentItem().text())
            self.save_packet(num, self.instrument.RX_PACKET)
            self.load_packet(num, self.instrument.RX_PACKET) # TODO: needed to reload the packet into the interface

        # tx packets
        if self.tx_packets_list.count():
            num = str(self.tx_packets_list.currentItem().text())
            self.save_packet(num, self.instrument.TX_PACKET)
            self.load_packet(num, self.instrument.TX_PACKET) # TODO: needed to reload the packet into the interface
        
        self.instrument.to_file(filename)
