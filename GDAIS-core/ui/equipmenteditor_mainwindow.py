# -*- coding: utf-8 -*-

"""
Module implementing EquipmentEditorMainWindow.
"""

from PyQt4.QtGui import QFileDialog, QInputDialog, QListWidgetItem, QMainWindow,  QMessageBox, QTreeWidgetItem
from PyQt4.QtCore import pyqtSignature, QString, Qt

import os

from Ui_equipmenteditor_mainwindow import Ui_EquipmentEditorMainWindow
from equipment import Equipment, OperationCommand, InstrumentConfigAlreadyExistsError
from instrument import Field

class EquipmentEditorMainWindow(QMainWindow, Ui_EquipmentEditorMainWindow):
    """
    Class documentation goes here.
    """
    CONF_PATH = '{0}/conf'.format(os.getcwd())
    EQUIPMENT_PATH = '{0}/equips'.format(CONF_PATH)
    INSTRUMENT_PATH = '{0}/instruments'.format(CONF_PATH)
    
    FILEDIALOG_FILTER = "Equipment configuration (*.json)"
    FILEDIALOG_FILTER_INSTRUMENT = "Instrument configuration (*.json)"
    
    def __init__(self, parent = None):
        """
        Constructor
        """
        QMainWindow.__init__(self, parent)
        self.setupUi(self)
        # TODO: temporally load always an instrument
        self._load_equipment(Equipment(self.EQUIPMENT_PATH + "/sidamon.json"))
        #self._load_equipment(Equipment())
    
    
    ### MENU ACTIONS ###
    
    @pyqtSignature("")
    def on_action_New_triggered(self):
        # TODO: not implemented yet
        raise NotImplementedError
#        self._load_equipment(Equipment())
    
    @pyqtSignature("")
    def on_action_Open_triggered(self):
        filename = QFileDialog.getOpenFileName(
                                            None,
                                            self.trUtf8("Select an equipment description file"),
                                            QString(self.EQUIPMENT_PATH),
                                            self.trUtf8(self.FILEDIALOG_FILTER),
                                            None)
        if filename:
            self._load_equipment(Equipment(str(filename)))
    
    @pyqtSignature("")
    def on_action_Save_triggered(self):
        filename = self.equipment.filename
        if not filename:
            filename = QFileDialog.getSaveFileName(
                                                None,
                                                self.trUtf8("Save equipment description file"),
                                                QString(self.EQUIPMENT_PATH),
                                                self.trUtf8(self.FILEDIALOG_FILTER),
                                                None)
        if filename:
            self._dump_equipment(str(filename))
            self.equipment.filename = str(filename)
    
    @pyqtSignature("")
    def on_action_Save_As_triggered(self):
        filename = QFileDialog.getSaveFileName(
                                            None,
                                            self.trUtf8("Save equipment description file"),
                                            QString(self.EQUIPMENT_PATH),
                                            self.trUtf8(self.FILEDIALOG_FILTER),
                                            None)
        if filename:
            self._dump_equipment(str(filename))
            self.equipment.filename = str(filename)
    
    @pyqtSignature("")
    def on_action_About_triggered(self):
        QMessageBox.information(self, "About", "GUI for editing Equipment descriptions in JSON.")
    
    
    ### INSTRUMENTS LIST ###
    
    @pyqtSignature("QListWidgetItem*, QListWidgetItem*")
    def on_instruments_list_currentItemChanged(self, current, previous):
        if previous:
            self._save_instrument()
        else:
            self.instruments_delete.setEnabled(True)
        
        if current:
            self._load_instrument(str(current.text()))
        else:
            self.instruments_delete.setEnabled(False)
    
    @pyqtSignature("")
    def on_instruments_add_clicked(self):
        filename = QFileDialog.getOpenFileName(
                                    None,
                                    self.trUtf8("Select an instrument description file"),
                                    QString(self.INSTRUMENT_PATH),
                                    self.trUtf8(self.FILEDIALOG_FILTER_INSTRUMENT),
                                    None)
        if filename:
            try:
                import os # save relative instrument file path
                rel_filename = os.path.relpath(str(filename))
                short_name = self.equipment.add_instrument_config(str(rel_filename))
            except InstrumentConfigAlreadyExistsError:
                QMessageBox.warning(None,
                    self.trUtf8("Instrument already configured"),
                    self.trUtf8("""The selected instrument file has already been loaded, click on it if you want to modify it."""),
                    QMessageBox.StandardButtons(\
                        QMessageBox.Close))
            else:
                item = QListWidgetItem(short_name)
                self.instruments_list.addItem(item)
                self.instruments_list.setCurrentItem(item)
    
    @pyqtSignature("")
    def on_instruments_delete_clicked(self):
        short_name = str(self.instruments_list.currentItem().text())
        self.instruments_list.takeItem(self.instruments_list.currentRow())
        self.equipment.delete_instrument_config(short_name)


    ### INIT COMMANDS ###
    
    @pyqtSignature("QListWidgetItem*, QListWidgetItem*")
    def on_init_commands_list_currentItemChanged(self, current, previous):
        if previous:
            self._save_init_command(previous.cmd)
        else:
            self.init_commands_delete.setEnabled(True)
            self.init_command_values.setEnabled(True)
            self.init_command_reply.setEnabled(True)
            self.init_command_reply_values.setEnabled(True)
        
        if current:
            self._load_init_command(current.cmd)
        else:
            self.init_commands_delete.setEnabled(False)
            self.init_command_values.setEnabled(False)
            self.init_command_reply.setEnabled(False)
            self.init_command_reply_values.setEnabled(False)
    
    @pyqtSignature("")
    def on_init_commands_add_clicked(self):
        tx_packets = dict([ (packet.name, num)
                            for num, packet in self.instr_cfg.instrument.tx_packets.iteritems() ])
        
        (text, ok) = QInputDialog.getItem(\
            self,
            self.trUtf8("Add init command"),
            self.trUtf8("Select command to send:"),
            tx_packets.keys(),
            0, False)
        
        if ok and text:
            cmd_num = tx_packets[str(text)]
            command = self.instr_cfg.add_init_command(cmd_num)
            item = QListWidgetItem(str(cmd_num))
            item.cmd = command
            self.init_commands_list.addItem(item)
            self.init_commands_list.setCurrentItem(item)
    
    @pyqtSignature("")
    def on_init_commands_delete_clicked(self):
        command = self.init_commands_list.currentItem().cmd
        self.init_commands_list.takeItem(self.init_commands_list.currentRow())
        self.instr_cfg.delete_init_command(command)

    @pyqtSignature("QString")
    def on_init_command_reply_currentIndexChanged(self, text):
        if self.init_commands_list.currentItem():
            current_init_cmd = self.init_commands_list.currentItem().cmd
            current_reply_name = current_init_cmd.reply.name
            
            if str(text) == current_reply_name:
                self._clear_init_command_reply()
                self._load_init_command_reply(current_init_cmd, str(text))
                
            else:
                reply = QMessageBox.warning(None,
                    self.trUtf8("Changing reply packet"),
                    self.trUtf8("""Selecting a different reply packet will delete all configured reply packet values. Are you sure you want to continue?"""),
                    QMessageBox.StandardButtons(\
                        QMessageBox.No | \
                        QMessageBox.Yes),
                    QMessageBox.No)
                
                if reply == QMessageBox.Yes:
                    self._clear_init_command_reply()
                    self._load_init_command_reply(current_init_cmd, str(text))
                else:
                    self.init_command_reply.setCurrentIndex(
                        self.init_command_reply.findText(current_reply_name))


    ### OPERATION COMMANDS ###
    
    @pyqtSignature("QString")
    def on_operation_mode_currentIndexChanged(self, text):
        if str(text) == self.instr_cfg.operation_mode:
            self._load_operation_mode(str(text))
            
        else:
            reply = QMessageBox.warning(None,
                self.trUtf8("Changing operation mode"),
                self.trUtf8("""Selecting a different operation mode will delete all configured operation commands. Are you sure you want to continue?"""),
                QMessageBox.StandardButtons(\
                    QMessageBox.No | \
                    QMessageBox.Yes),
                QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                self._load_operation_mode(str(text))
            else:
                self.operation_mode.setCurrentIndex(
                    self.operation_mode.findText(self.instr_cfg.operation_mode))

    @pyqtSignature("QListWidgetItem*, QListWidgetItem*")
    def on_operation_commands_list_currentItemChanged(self, current, previous):
        if previous:
            self._save_operation_command(previous.cmd)
        else:
            self.operation_commands_delete.setEnabled(True)
            self.operation_command_param.setEnabled(True)
            self.operation_command_values.setEnabled(True)
        
        if current:
            self._load_operation_command(current.cmd)
        else:
            self.operation_commands_delete.setEnabled(False)
            self.operation_command_param.setEnabled(False)
            self.operation_command_values.setEnabled(False)
    
    @pyqtSignature("")
    def on_operation_commands_add_clicked(self):
        tx_packets = dict([ (packet.name, num)
                            for num, packet in self.instr_cfg.instrument.tx_packets.iteritems() ])
        
        (text, ok) = QInputDialog.getItem(\
            self,
            self.trUtf8("Add operation command"),
            self.trUtf8("Select command to send:"),
            tx_packets.keys(),
            0, False)
        
        if ok and text:
            cmd_num = tx_packets[str(text)]
            command = self.instr_cfg.add_operation_command(cmd_num)
            item = QListWidgetItem(str(cmd_num))
            item.cmd = command
            self.operation_commands_list.addItem(item)
            self.operation_commands_list.setCurrentItem(item)

    @pyqtSignature("")
    def on_operation_commands_delete_clicked(self):
        command = self.operation_commands_list.currentItem().cmd
        self.operation_commands_list.takeItem(self.operation_commands_list.currentRow())
        self.instr_cfg.delete_operation_command(command)
    
    
    ### PRIVATE METHODS ###
    
    ## Equipment ##
    def _load_equipment(self, equipment):
        self._clear_equipment()
        
        self.equipment = equipment
        
        # base info
        self.equipment_name.setText(self.equipment.name)
        self.equipment_short_name.setText(self.equipment.short_name)
        
        # instruments
        for instr_cfg in self.equipment.instruments:
            self.instruments_list.addItem(instr_cfg.instrument.short_name)
        if self.instruments_list.count():
            self.instruments_list.setCurrentItem(self.instruments_list.item(0))
    
    def _clear_equipment(self):
        for i in xrange(self.instruments_list.count()):
            self.instruments_list.takeItem(0)
        self.instrument_name.setText('')

    def _dump_equipment(self, filename):
        # base info
        self.equipment.name = str(self.equipment_name.text())
        self.equipment.short_name = str(self.equipment_short_name.text())
        
        if self.instruments_list.count():
            short_name = str(self.instruments_list.currentItem().text())
            self._save_instrument()
            self._load_instrument(short_name) # TODO: needed to reload the instrument into the interface
        
        self.equipment.to_file(filename)
    
    ## Instrument ##
    def _load_instrument(self, short_name):
        self._clear_instrument()
        
        self.instr_cfg = self.equipment.get_instrument_config(short_name)
        self.instrument_name.setText(self.instr_cfg.instrument.name)
        
        # init commands
        self._load_init_commands()
        
        # operation commands
        self.operation_mode.setCurrentIndex(self.operation_mode.findText(self.instr_cfg.operation_mode))
        self._load_operation_mode()
    
    def _clear_instrument(self):
        self.instrument_name.setText('')
        self._clear_init_commands()
        self._clear_operation_mode()

    def _save_instrument(self):
        # init commands
        if self.init_commands_list.count():
            command = self.init_commands_list.currentItem().cmd
            self._save_init_command(command)
            self._load_init_command(command) # TODO: needed to reload the instrument into the interface
        
        # operation commands
        if self.operation_commands_list.count():
            command = self.operation_commands_list.currentItem().cmd
            self._save_operation_command(command)
            self._load_operation_command(command) # TODO: needed to reload the instrument into the interface

    ## Init commands ##
    def _load_init_commands(self):
        self.init_command_replies = dict([ (packet.name, num)
                            for num, packet in self.instr_cfg.instrument.rx_packets.iteritems() ])
        self.init_command_reply.addItems(self.init_command_replies.keys())
        
        self._load_commands(self.instr_cfg.init_commands, self.init_commands_list)
    
    def _clear_init_commands(self):
        self._clear_commands(self.init_commands_list)
        self.init_command_reply.clear()
    
    def _load_init_command(self, command):
        self.init_command_name.setText(command.name)
        self._load_command_values(command, self.init_command_values)
        
        self.init_command_reply.setCurrentIndex(
                                                self.init_command_reply.findText(command.reply.name))
        self._clear_init_command_reply()
        self._load_init_command_reply(command, command.reply.name)
    
    def _save_init_command(self, command):
        command.reply.values = self._get_command_values(self.init_command_reply_values)
        command.values = self._get_command_values(self.init_command_values)
        self.init_command_name.setText('')
    
    def _clear_init_command_reply(self):
        self._get_command_values(self.init_command_reply_values)
    
    def _load_init_command_reply(self, command, reply_name):
        reply_id = self.init_command_replies[reply_name]
        self.instr_cfg.set_command_reply(command, reply_id)
        self._load_command_values(command.reply, self.init_command_reply_values)
    
    ## Operation commands ##
    def _load_operation_mode(self, operation_mode=''):
        self._clear_operation_mode()
        
        if operation_mode:
            self.instr_cfg.operation_mode = operation_mode
        
        texts = OperationCommand.DEFAULTS[self.instr_cfg.operation_mode]
        self.operation_command_param_pre_txt.setText("{0}:".format(texts['pre_txt']))
        self.operation_command_param_post_txt.setText(texts['post_txt'])
        
        self._load_commands(self.instr_cfg.operation_commands, self.operation_commands_list)
    
    def _clear_operation_mode(self):
        self._clear_commands(self.operation_commands_list)
    
    def _load_operation_command(self, command):
        self.operation_command_name.setText(command.name)
        self.operation_command_param.setText(str(command.param))
        self._load_command_values(command, self.operation_command_values)
    
    def _save_operation_command(self, command):
        command.values = self._get_command_values(self.operation_command_values)
        command.param = int(self.operation_command_param.text())
        self.operation_command_name.setText('')
        self.operation_command_param.setText('')

    ## Commands aux methods ##
    def _load_commands(self, commands, commands_list_widget):
        for cmd in commands:
            item = QListWidgetItem(str(cmd.id))
            item.cmd = cmd
            commands_list_widget.addItem(item)
        if commands_list_widget.count():
            commands_list_widget.setCurrentItem(commands_list_widget.item(0))
    
    def _clear_commands(self, commands_list_widget):
        for i in xrange(commands_list_widget.count()):
            commands_list_widget.takeItem(0)
    
    def _load_command_values(self, command, values_widget):
        for field, value in zip(command.fields, command.values):
            item = QTreeWidgetItem([field.name, str(value)])
            if field.name != Field.EMPTY_FIELD:
                item.setFlags(item.flags() | Qt.ItemIsEditable)
            values_widget.addTopLevelItem(item)
    
    def _get_command_values(self, values_widget):
        values = []
        for i in xrange(values_widget.topLevelItemCount()):
            item = values_widget.takeTopLevelItem(0)
            values.append(str(item.text(1)))
        return values
