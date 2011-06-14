# -*- coding: utf-8 -*-

"""
Module implementing the instrument model.
"""
import json, logging

from instrument import Instrument

class Equipment(object):
    
    def __init__(self,  filename=None):
        self.log = logging.getLogger('GDAIS.Equipment')
        
        if filename:
            self.filename = filename
            with open(self.filename, "r") as fp:
                equip = json.load(fp)
            
            self.short_name = equip['short_name']
            self.name = equip['name']
            
            self.instruments = []
            for instr in equip['instruments']:
                self.instruments.append(InstrumentConfig(instr))
        
        else:
            self.filename = ""
            self.short_name = "new_equipment"
            self.name = "New Equipment"
            self.instruments = []
    
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
    
    def to_file(self, filename):
        with open(filename, "w") as fp:
            json.dump(self.dump(), fp, indent=True)


class InstrumentConfig(object):
    
    # Operation modes
    class OperationMode:
        periodic = "Periodic Commands"
        sequences = "Time Sequences"
        blocking = "Blocking Sequences"
    
    DEFAULT_OPERATION_MODE = OperationMode.periodic
    
    def __init__(self,  instr):
        self.log = logging.getLogger('GDAIS.InstrumentConfig')
        
        if type(instr) is str:
            self.instrument = Instrument(instr)
            self.init_commands = []
            self._operation_mode = self.DEFAULT_OPERATION_MODE
            self.operation_commands = []
        
        elif type(instr) is dict:
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
            self.log.error("Unknown parameter type, can't initialize InstrumentConfig")
    
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
        # create new InitCommand with first rx packet as default reply
        cmd = InitCommand(c, self.instrument.rx_packets.keys()[0])
        if self._load_command_info(cmd):
            self._load_command_info(cmd.reply, Instrument.RX_PACKET)
            self.init_commands.append(cmd)
        return cmd # TODO: what to do if info cannot be loaded?
    
    def delete_init_command(self, cmd):
        self.init_commands.remove(cmd)
    
    def set_command_reply(self, cmd, reply_id):
        if reply_id != cmd.reply.id:
            cmd.reply.id = reply_id
            self._load_command_info(cmd.reply, Instrument.RX_PACKET)
    
    def add_operation_command(self, c):
        cmd = OperationCommand(c, self.operation_mode)
        if self._load_command_info(cmd):
            self.operation_commands.append(cmd)
        return cmd # TODO: what to do if info cannot be loaded?
    
    def delete_operation_command(self, cmd):
        self.operation_commands.remove(cmd)
    
    def _load_command_info(self, cmd, type=Instrument.TX_PACKET):
        try:
            if type == Instrument.TX_PACKET:
                packet = self.instrument.tx_packets[cmd.id]
            else:
                packet = self.instrument.rx_packets[cmd.id]
        
        except KeyError:
            txt = "Command '{0}' not in instrument '{1}' {2} packets"
            self.log.error(txt.format(cmd.id, self.instrument.name, type))
            return False
        
        else:
            cmd.name = packet.name
            cmd.fields = packet.fields
            if not cmd.values: # TODO: values initialization, best solution?
                cmd.values = [0] * len(cmd.fields)
            return True
    
    def dump(self):
        return {
                    'filename': self.instrument.filename,
                    'init_commands': [c.dump() for c in self.init_commands],
                    'operation_mode': self.operation_mode, 
                    'operation_commands': [c.dump() for c in self.operation_commands]
                }


class Command(object):
    
    def __init__(self,  cmd):
        self.name = ''
        
        if type(cmd) is int:
            self.id = cmd
            self.values = []
        
        elif type(cmd) is dict:
            self.id = cmd['id']
            self.values = cmd['values']
    
    def dump(self):
        return {
                    'id': self.id,
                    'name': self.name,
                    'values': self.values
                }


class InitCommand(Command):
    
    def __init__(self, init_command, reply=None):
        if type(init_command) is int:
            Command.__init__(self, init_command)
            self.reply = Command(reply)
        
        elif type(init_command) is dict:
            Command.__init__(self, init_command['command'])
            self.reply = Command(init_command['reply'])
    
    def dump(self):
        return {
                    'command': Command.dump(self), 
                    'reply': self.reply.dump()
                }


class OperationCommand(Command):
    
    DEFAULTS = {
        InstrumentConfig.OperationMode.periodic: {
                                'pre_txt': 'Period', 
                                'param': 1000, 
                                'post_txt': 'ms'
                            },
        InstrumentConfig.OperationMode.sequences: {
                                'pre_txt': 'Duration', 
                                'param': 1000, 
                                'post_txt': 'ms'
                            },
        InstrumentConfig.OperationMode.blocking: {
                                'pre_txt': 'Repeat',
                                'param': 1,  
                                'post_txt': 'time(s)'
                            }
                }
    
    def __init__(self,  operation_command, operation_mode):
        if type(operation_command) is int:
            Command.__init__(self, operation_command)
            self.param = self.DEFAULTS[operation_mode]['param']
        
        elif type(operation_command) is dict:
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
