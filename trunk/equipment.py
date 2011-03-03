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
    
    def __init__(self):
        # TODO: not implemented yet
        raise NotImplementedError
    
    def __init__(self,  instr):
        if type(instr) is type(''): # str
            self.instrument = Instrument(instr)
            self.init_commands = []
            self.periodic_commands = []
        
        elif type(instr) is type({}): # dict
            self.instrument = Instrument(instr['filename'])
            
            self.init_commands = []
            if 'init_commands' in instr:
                for c in instr['init_commands']:
                    self.add_init_command(c)
            
            self.periodic_commands = []
            if 'periodic_commands' in instr:
                for c in instr['periodic_commands']:
                    self.add_periodic_command(c)
        
        else:
            print TAG, "Unknown parameter type, can't initialize InstrumentConfig"
    
    def add_init_command(self, c):
        cmd = Command(c)
        if (self._load_command_info(cmd)):
            self.init_commands.append(cmd)
    
    def delete_init_command(self, num):
        cmd = self._get_command(self.init_commands, num)
        self.init_commands.remove(cmd)
    
    def get_init_command(self, num):
        return self._get_command(self.init_commands, num)
    
    def add_periodic_command(self, c):
        cmd = PeriodicCommand(c)
        if (self._load_command_info(cmd)):
            self.periodic_commands.append(cmd)
    
    def delete_periodic_command(self, num):
        cmd = self._get_command(self.periodic_commands, num)
        self.periodic_commands.remove(cmd)
    
    def get_periodic_command(self, num):
        return self._get_command(self.periodic_commands, num)
    
    def _load_command_info(self, cmd):
        try:
            packet = self.instrument.tx_packets[cmd.id]
        except KeyError:
            txt = "Command {0} not in instrument {1} tx packets"
            print self.TAG, txt.format(cmd.id, self.instrument.name)
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
        import os
        filename = self.instrument.filename[len(os.getcwd())+1:]
        return {
                    'filename': self.instrument.filename,
                    'init_commands': [cmd.dump() for cmd in self.init_commands],
                    'periodic_commands': [cmd.dump() for cmd in self.periodic_commands]
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


class PeriodicCommand(Command):
    """
    Class documentation goes here.
    """
    DEFAULT_PERIOD = 1000
    
    def __init__(self,  periodic_command):
        if type(periodic_command) is type(0): # int
            Command.__init__(self, periodic_command)
            self.period = self.DEFAULT_PERIOD
        
        elif type(periodic_command) is type({}): #dict
            Command.__init__(self, periodic_command['command'])
            self.period = periodic_command['period']
    
    def dump(self):
        return {
                    'command': Command.dump(self), 
                    'period': self.period
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
