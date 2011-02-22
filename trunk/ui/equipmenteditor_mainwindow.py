# -*- coding: utf-8 -*-

"""
Module implementing EquipmentEditorMainWindow.
"""

from PyQt4.QtGui import QFileDialog, QListWidgetItem, QMainWindow,  QMessageBox, QTreeWidgetItem
from PyQt4.QtCore import pyqtSignature, QString, Qt

from Ui_equipmenteditor_mainwindow import Ui_EquipmentEditorMainWindow
from equipment import Equipment, InstrumentConfigAlreadyExistsError

class EquipmentEditorMainWindow(QMainWindow, Ui_EquipmentEditorMainWindow):
    """
    Class documentation goes here.
    """
    CONF_PATH = 'conf/'
    EQUIPMENT_PATH = CONF_PATH + 'equips/'
    INSTRUMENT_PATH = CONF_PATH + 'instruments/'
    
    def __init__(self, parent = None):
        """
        Constructor
        """
        QMainWindow.__init__(self, parent)
        self.setupUi(self)
        # TODO: temporally load always an instrument
        self.load_equipment(Equipment("conf/equips/equip2.json"))
        #self.load_equipment(Equipment())
    
    @pyqtSignature("")
    def on_action_New_triggered(self):
        """
        Slot documentation goes here.
        """
        # TODO: not implemented yet
        raise NotImplementedError
#        self.load_instrument(Instrument())
    
    @pyqtSignature("")
    def on_action_Open_triggered(self):
        """
        Slot documentation goes here.
        """
        filename = QFileDialog.getOpenFileName(
                                            None,
                                            self.trUtf8("Select an equipment description file"),
                                            QString(self.EQUIPMENT_PATH),
                                            self.trUtf8("*.json"),
                                            None)
        if filename:
            self.load_equipment(Equipment(filename))
    
    @pyqtSignature("")
    def on_action_Save_triggered(self):
        """
        Slot documentation goes here.
        """
        filename = self.equipment.filename
        if not filename:
            filename = QFileDialog.getOpenFileName(
                                                None,
                                                self.trUtf8("Save equipment description file"),
                                                QString(self.EQUIPMENT_PATH),
                                                self.trUtf8("*.json"),
                                                None)
        if filename:
            self.dump_equipment(filename)
            self.equipment.filename = filename
    
    @pyqtSignature("")
    def on_action_Save_As_triggered(self):
        """
        Slot documentation goes here.
        """
        filename = QFileDialog.getOpenFileName(
                                            None,
                                            self.trUtf8("Save equipment description file"),
                                            QString(self.EQUIPMENT_PATH),
                                            self.trUtf8("*.json"),
                                            None)
        if filename:
            self.dump_equipment(filename)
            self.equipment.filename = filename
    
    @pyqtSignature("")
    def on_action_About_triggered(self):
        """
        Slot documentation goes here.
        """
        QMessageBox.information(self, "About", "GUI for editing Equipment descriptions in JSON.")
    
    @pyqtSignature("QListWidgetItem*, QListWidgetItem*")
    def on_instruments_list_currentItemChanged(self, current, previous):
        """
        Slot documentation goes here.
        """
        if previous:
            self.save_instrument()
        else:
            self.instruments_delete.setEnabled(True)
        
        if current:
            self.load_instrument(str(current.text()))
        else:
            self.instruments_delete.setEnabled(False)
    
    @pyqtSignature("")
    def on_instruments_add_clicked(self):
        """
        Slot documentation goes here.
        """
        filename = QFileDialog.getOpenFileName(
                                    None,
                                    self.trUtf8("Select an instrument description file"),
                                    QString(self.INSTRUMENT_PATH),
                                    self.trUtf8("*.json"),
                                    None)
        if filename:
            try:
                short_name = self.equipment.add_instrument_config(str(filename))
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
        """
        Slot documentation goes here.
        """
        short_name = str(self.instruments_list.currentItem().text())
        self.instruments_list.takeItem(self.instruments_list.currentRow())
        self.equipment.delete_instrument_config(short_name)

    @pyqtSignature("QListWidgetItem*, QListWidgetItem*")
    def on_init_commands_list_currentItemChanged(self, current, previous):
        """
        Slot documentation goes here.
        """
        if previous:
            self.save_init_command(str(previous.text()))
#        else:
#            self.init_commands_delete.setEnabled(True)
        
        if current:
            self.load_init_command(str(current.text()))
#        else:
#            self.init_commands_delete.setEnabled(False)

    @pyqtSignature("QListWidgetItem*, QListWidgetItem*")
    def on_periodic_commands_list_currentItemChanged(self, current, previous):
        """
        Slot documentation goes here.
        """
        if previous:
            self.save_periodic_command(str(previous.text()))
#        else:
#            self.periodic_commands_delete.setEnabled(True)
        
        if current:
            self.load_periodic_command(str(current.text()))
#        else:
#            self.periodic_commands_delete.setEnabled(False)
    
    def load_instrument(self, short_name):
        self.clear_instrument()
        
        self.instr_cfg = self.equipment.get_instrument_config(short_name)
        self.instrument_name.setText(self.instr_cfg.instrument.name)
        
        # init commands
        for cmd in self.instr_cfg.init_commands:
            self.init_commands_list.addItem(str(cmd.id))
        if self.init_commands_list.count():
            self.init_commands_list.setCurrentItem(self.init_commands_list.item(0))
        
        # periodic commands
        for cmd in self.instr_cfg.periodic_commands:
            self.periodic_commands_list.addItem(str(cmd.id))
        if self.periodic_commands_list.count():
            self.periodic_commands_list.setCurrentItem(self.periodic_commands_list.item(0))
    
    def clear_instrument(self):
        self.instrument_name.setText('')
        
        for i in xrange(self.init_commands_list.count()):
            self.init_commands_list.takeItem(0)
        self.init_command_name.setText('')
        
        for i in xrange(self.periodic_commands_list.count()):
            self.periodic_commands_list.takeItem(0)
        self.periodic_command_name.setText('')
        self.periodic_command_period.setText('')

    def save_instrument(self):
        # init commands
        if self.init_commands_list.count():
            cmd_num = str(self.init_commands_list.currentItem().text())
            self.save_init_command(cmd_num)
            self.load_init_command(cmd_num) # TODO: needed to reload the instrument into the interface
        
        # periodic commands
        if self.periodic_commands_list.count():
            cmd_num = str(self.periodic_commands_list.currentItem().text())
            self.save_periodic_command(cmd_num)
            self.load_periodic_command(cmd_num) # TODO: needed to reload the instrument into the interface

    def load_init_command(self, cmd_num):
        command = self.instr_cfg.get_init_command(int(cmd_num))
        self.init_command_name.setText(command.name)
        for field, value in zip(command.fields, command.values):
            item = QTreeWidgetItem([field.name, str(value)])
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            self.init_command_values.addTopLevelItem(item)
    
    def save_init_command(self, cmd_num):
        values = []
        for i in xrange(self.init_command_values.topLevelItemCount()):
            item = self.init_command_values.takeTopLevelItem(0)
            values.append(str(item.text(1)))
        
        command = self.instr_cfg.get_init_command(int(cmd_num))
        command.values = values

    def load_periodic_command(self, cmd_num):
        command = self.instr_cfg.get_periodic_command(int(cmd_num))
        self.periodic_command_name.setText(command.name)
        self.periodic_command_period.setText(str(command.period))
        for field, value in zip(command.fields, command.values):
            item = QTreeWidgetItem([field, value])
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            self.periodic_command_values.addTopLevelItem(item)
    
    def save_periodic_command(self, cmd_num):
        values = []
        for i in xrange(self.periodic_command_values.topLevelItemCount()):
            item = self.periodic_command_values.takeTopLevelItem(0)
            values.append(str(item.text(1)))
        
        command = self.instr_cfg.get_periodic_command(int(cmd_num))
        command.values = values
        command.period = int(self.periodic_command_period.text())

    def load_equipment(self, equipment):
        self.clear_equipment()
        
        self.equipment = equipment
        
        # base info
        self.equipment_name.setText(self.equipment.name)
        self.equipment_short_name.setText(self.equipment.short_name)
        
        # instruments
        for instr_cfg in self.equipment.instruments:
            self.instruments_list.addItem(instr_cfg.instrument.short_name)
        if self.instruments_list.count():
            self.instruments_list.setCurrentItem(self.instruments_list.item(0))
    
    def clear_equipment(self):
        for i in xrange(self.instruments_list.count()):
            self.instruments_list.takeItem(0)
        self.instrument_name.setText('')

    def dump_equipment(self, filename):
        # base info
        self.equipment.name = str(self.equipment_name.text())
        self.equipment.short_name = str(self.equipment_short_name.text())
        
        if self.instruments_list.count():
            short_name = str(self.instruments_list.currentItem().text())
            self.save_instrument(short_name)
            self.load_instrument(short_name) # TODO: needed to reload the instrument into the interface
        
        self.equipment.to_file(filename)
