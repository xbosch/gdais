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
    
    instruments = []
    command_sequences = []
    
    def __init__(self):
        self.filename = ""
        self.short_name = "new_equipment"
        self.name = "New Equipment"
    
    def __init__(self,  filename):
        self.filename = filename
        with open(self.filename, "r") as fp:
            equip = json.load(fp)
        
        self.short_name = equip['short_name']
        self.name = equip['name']
        
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
        if type(instr) is type(''):
            self.instrument = Instrument(instr)
            self.init_commands = []
            self.periodic_commands = []
        
        elif type(instr) is type({}):
            self.instrument = Instrument(instr['filename'])
            
            self.init_commands = []
            if 'init_commands' in instr:
                for c in instr['init_commands']:
                    cmd = Command(c)
                    try:
                        packet = self.instrument.tx_packets[cmd.id]
                    except KeyError:
                        print self.TAG, "Command %s not in instrument %s tx packets" % (cmd.id, self.instrument.name)
                    else:
                        cmd.fields = packet.fields
                        #cmd.name = packet.name
                        self.init_commands.append(cmd)
            
            self.periodic_commands = []
            if 'periodic_commands' in instr:
                for c in instr['periodic_commands']:
                    cmd = PeriodicCommand(c)
                    try:
                        packet = self.instrument.tx_packets[cmd.id]
                    except KeyError:
                        print self.TAG, "Command %s not in instrument %s tx packets" % (cmd.id, self.instrument.name)
                    else:
                        cmd.fields = packet.fields
                        #cmd.name = packet.name
                        self.periodic_commands.append(cmd)
    
    def get_init_command(self, num):
        for cmd in self.init_commands:
            if cmd.id == num:
                return cmd
        return None
    
    def get_periodic_command(self, num):
        for cmd in self.periodic_commands:
            if cmd.id == num:
                return cmd
        return None
    
    def dump(self):
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
        self.id = cmd['id']
        self.name = cmd['name']
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
    
    def __init__(self,  periodic_command):
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
