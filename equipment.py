# -*- coding: utf-8 -*-

"""
Module implementing the instrument model.
"""
import json

from instrument import Instrument

class Equipment(object):
    """
    Class documentation goes here.
    """
    TAG = "[Equipment]"
    
    def __init__(self):
        self.filename = ""
        self.short_name = "new_equipment"
        self.name = "New Equipment"
        self.instruments = []
    
    def __init__(self,  filename):
        self.filename = filename
        with open(self.filename, "r") as fp:
            equip = json.load(fp)
        
        self.short_name = equip['short_name']
        self.name = equip['name']
        
        self.instruments = []
        for instr in equip['instruments']:
            self.instruments.append(InstrumentConfig(instr))
    
    def add_instrument_config(self, filename):
        instr_cfg = InstrumentConfig(filename)
        short_name = instr_cfg.instrument.short_name
        if not self.get_instrument_config(short_name):
            self.instruments.append(instr_cfg)
        else:
            raise InstrumentConfigAlreadyExistsError(short_name)
        return short_name
    
    def delete_instrument_config(self, short_name):
        instr_cfg = self.get_instrument_config(short_name)
        self.instruments.remove(instr_cfg)
    
    def get_instrument_config(self, short_name):
        for instr_cfg in self.instruments:
            if instr_cfg.instrument.short_name == short_name:
                return instr_cfg
        return None
    
    def dump(self):
        return {
                    'name': self.name,
                    'short_name': self.short_name,
                    'instruments': [instr.dump() for instr in self.instruments]
                }
    
    def to_file(self, filename=""):
        if filename:
            with open(filename, "w") as fp:
                json.dump(self.dump(), fp, indent=True)
        else:
            # TODO: not implemented yet
            raise NotImplementedError


class InstrumentConfig(object):
    """
    Class documentation goes here.
    """
    TAG = "[InstrumentConfig]"
    
    DEFAULT_OPERATION_MODE = "Periodic Commands"
    
    def __init__(self):
        # TODO: not implemented yet
        raise NotImplementedError
    
    def __init__(self,  instr):
        if type(instr) is type(''): # str
            self.instrument = Instrument(instr)
            self.init_commands = []
            self._operation_mode = self.DEFAULT_OPERATION_MODE
            self.operation_commands = []
        
        elif type(instr) is type({}): # dict
            self.instrument = Instrument(instr['filename'])
            
            self.init_commands = []
            if 'init_commands' in instr:
                for c in instr['init_commands']:
                    self.add_init_command(c)
            
            self._operation_mode = instr['operation_mode']
            
            self.operation_commands = []
            if 'operation_commands' in instr:
                for c in instr['operation_commands']:
                    self.add_operation_command(c)
        
        else:
            print TAG, "Unknown parameter type, can't initialize InstrumentConfig"
    
    @property
    def operation_mode(self):
        """Operation mode of the instrument in this configuration."""
        return self._operation_mode
    
    @operation_mode.setter
    def operation_mode(self, value):
        if value != self._operation_mode:
            self._operation_mode = value
            self.operation_commands = []
    
    def add_init_command(self, c):
        cmd = Command(c)
        if (self._load_command_info(cmd)):
            self.init_commands.append(cmd)
    
    def delete_init_command(self, num):
        cmd = self._get_command(self.init_commands, num)
        self.init_commands.remove(cmd)
    
    def get_init_command(self, num):
        return self._get_command(self.init_commands, num)
    
    def add_operation_command(self, c):
        cmd = OperationCommand(c, self.operation_mode)
        if (self._load_command_info(cmd)):
            self.operation_commands.append(cmd)
    
    def delete_operation_command(self, num):
        cmd = self._get_command(self.operation_commands, num)
        self.operation_commands.remove(cmd)
    
    def get_operation_command(self, num):
        return self._get_command(self.operation_commands, num)
    
    def _load_command_info(self, cmd):
        try:
            packet = self.instrument.tx_packets[cmd.id]
        except KeyError:
            print self.TAG, "Command %s not in instrument %s tx packets" % (cmd.id, self.instrument.name)
            return False
        else:
            cmd.name = packet.name
            cmd.fields = packet.fields
            if not cmd.values: # TODO: values initialization, best solution?
                cmd.values = [0] * len(cmd.fields)
            return True
    
    def _get_command(self, commands, id):
        for cmd in commands:
            if cmd.id == id:
                return cmd
        return None
    
    def dump(self):
        return {
                    'filename': self.instrument.filename,
                    'init_commands': [c.dump() for c in self.init_commands],
                    'operation_mode': self.operation_mode, 
                    'operation_commands': [c.dump() for c in self.operation_commands]
                }


class Command(object):
    """
    Class documentation goes here.
    """
    
    def __init__(self,  cmd):
        self.name = ''
        if type(cmd) is type(0): # int
            self.id = cmd
            self.values = []
        
        elif type(cmd) is type({}): #dict
            self.id = cmd['id']
            self.values = cmd['values']
    
    def dump(self):
        return {
                    'id': self.id,
                    'name': self.name,
                    'values': self.values
                }


class OperationCommand(Command):
    """
    Class documentation goes here.
    """
    DEFAULTS = {
        'Periodic Commands': {
                                'param': 1000, 
                                'pre_txt': 'Period', 
                                'post_txt': 'ms'
                            },
        'Time Sequences': {
                                'param': 1000, 
                                'pre_txt': 'Duration', 
                                'post_txt': 'ms'
                            },
        'Blocking Sequences': {
                                'param': 5, 
                                'pre_txt': 'Repeat', 
                                'post_txt': 'times'
                            }
                }
    
    def __init__(self,  operation_command, operation_mode):
        if type(operation_command) is type(0): # int
            Command.__init__(self, operation_command)
            self.param = self.DEFAULTS[operation_mode]['param']
        
        elif type(operation_command) is type({}): #dict
            Command.__init__(self, operation_command['command'])
            self.param = operation_command['param']
    
    def dump(self):
        return {
                    'command': Command.dump(self), 
                    'param': self.param
                }


class InstrumentConfigAlreadyExistsError(Exception):
    """
    Exception raised when trying to add an instrument that already exists.
    
    Attributes:
        short_name -- short name of the instrument
    """
    
    def __init__(self, short_name):
        self.name = short_name
    
    def __str__(self):
        return repr(self.name)
