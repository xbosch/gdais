# -*- coding: utf-8 -*-

"""
Module implementing the instrument model.
"""
import json
from numpy import dtype
import os

class Instrument(object):
    
    RX_PACKET = "rx"
    TX_PACKET = "tx"
    
    BYTE_ORDER_CHAR = {
                        'big-endian': '>', 
                        'little-endian': '<'
                    }

    BASE_PATH = '/home/pau/feina/UPC/projecte/code/GDAIS/GDAIS-core'
    
    def __init__(self):
        self.filename = ""
        self.short_name = "new_instrument"
        self.name = "New Instrument"
        self.byte_order = "big-endian"
        
        self.connection = ConnectionCfg.create()
        self.packet_format = PacketFormat()
        self.rx_packets  = {}
        self.tx_packets = {}
    
    def __init__(self,  filename):
        self.filename = filename
        if not os.path.isabs(filename):
          self.filename = os.path.join(self.BASE_PATH, filename)
        with open(self.filename, "r") as fp:
            instr = json.load(fp)
        
        self.short_name = instr['short_name']
        self.name = instr['name']
        self.byte_order = instr['byte_order']
        
        self.connection = ConnectionCfg.create(instr['connection'])
        
        self.packet_format = PacketFormat(instr['packet_format'])
        
        self.rx_packets = {}
        for num, packet in instr['rx_packets'].iteritems():
            self.rx_packets[int(num)] = Packet(packet)
            
        self.tx_packets = {}
        for num, packet in instr['tx_packets'].iteritems():
            self.tx_packets[int(num)] = Packet(packet)
    
    @property
    def byte_order_char(self):
        if self.byte_order in self.BYTE_ORDER_CHAR:
            return self.BYTE_ORDER_CHAR[self.byte_order]
        else:
            return ''
    
    def set_conn_type(self, type):
        if self.connection.type != type:
            self.connection = ConnectionCfg.create(type)
    
    def add_packet(self, num, type):
        packet = Packet()
        if type == self.RX_PACKET and num not in self.rx_packets:
            self.rx_packets[int(num)] = packet
        elif type == self.TX_PACKET and num not in self.tx_packets:
            self.tx_packets[int(num)] = packet
        elif type != self.RX_PACKET and type != self.TX_PACKET:
            raise WrongPacketTypeError(type)
        else:
            raise PacketAlreadyExistsError(num)
    
    def delete_packet(self, num, type):
        if type == self.RX_PACKET:
            del self.rx_packets[num]
        elif type == self.TX_PACKET:
            del self.tx_packets[num]
        else:
            raise WrongPacketTypeError(type)
    
    def dump(self):
        rx_packets = {}
        for num,  packet in self.rx_packets.iteritems():
            rx_packets[num]  = packet.dump()
        
        tx_packets = {}
        for num,  packet in self.tx_packets.iteritems():
            tx_packets[num]  = packet.dump()
        
        return {
                    'name': self.name,
                    'short_name': self.short_name,
                    'byte_order': self.byte_order, 
                    'connection': self.connection.dump(), 
                    'packet_format': self.packet_format.dump(), 
                    'rx_packets': rx_packets, 
                    'tx_packets': tx_packets
                }
    
    def to_file(self, filename=""):
        if filename:
            with open(filename, "w") as fp:
                json.dump(self.dump(), fp, indent=True)
        else:
            # TODO: not implemented yet
            raise NotImplementedError
    

class ConnectionCfg(object):
    
    # Connection types
    class Type:
        serial = "Serial"
        file = "File"

    @staticmethod
    def create(conn=None, *args, **kwds):
        if conn:
            try:
                if type(conn) is dict:
                    conn_type = conn['type']
                elif type(conn) is str:
                    conn_type = conn
                else:
                    raise Exception('Unknown parameter type "{0}"'.format(type(conn)))
            except KeyError:
                raise Exception('No connection type supplied')
                
            else:
                connection = {
                    ConnectionCfg.Type.serial: SerialConnectionCfg,
                    ConnectionCfg.Type.file:     FileConnectionCfg
                }.get(conn_type, None)
                
                if not connection:
                    raise Exception('Connection type "{0}" not implemented'.format(conn_type))
        
        else:
            # serial connection as default type
            connection = SerialConnectionCfg
        
        return connection(conn, *args, **kwds)
    
    def __init__(self, conn=None):
        # ConnectionCfg can't be initialized, use factory method create()
        raise NotImplementedError


class SerialConnectionCfg(ConnectionCfg):
    
    def __init__(self, conn):
        self.type = ConnectionCfg.Type.serial
        if conn and type(conn) is dict:
            self.serial_port = conn['port']
            self.baudrate = conn['baudrate']
            self.data_bits = conn['data_bits']
            self.parity = conn['parity']
            self.stop_bits = conn['stop_bits']
        else:
            # load defaults
            self.serial_port = "/dev/ttyS0"
            self.baudrate = 9600
            self.data_bits = 8
            self.parity = 'N'
            self.stop_bits = 1
    
    def dump(self):
            return {
                    'type': self.type, 
                    'port': self.serial_port, 
                    'baudrate': self.baudrate, 
                    'data_bits': self.data_bits, 
                    'parity': self.parity, 
                    'stop_bits': self.stop_bits
                }


class FileConnectionCfg(ConnectionCfg):
    
    def __init__(self, conn):
        self.type = ConnectionCfg.Type.file
        if conn and type(conn) is dict:
            self.filename = conn['filename']
        else:
            self.filename = ''
    
    def dump(self):
        return {
                'type': self.type, 
                'filename': self.filename
            }


class PacketFormat(object):
    
    # Format fields
    class FormatField:
        empty = 'none'
        start_bytes = 'Start bytes'
        length = 'Length'
        packet_num = 'Packet num'
        packet_fields = 'Packet fields'
        checksum = 'Checksum'
        end_bytes = 'End bytes'
    
    def __init__(self,  packet_format=None):
        if packet_format:
            self.rx_format = packet_format['rx_format']
            self.tx_format = packet_format['tx_format']
            self.start_bytes = packet_format['start_bytes']
            self.end_bytes = packet_format['end_bytes']
        else:
            self.rx_format = []
            self.tx_format = []
            self.start_bytes = []
            self.end_bytes = []
    
    def dump(self):
        return {
                    'rx_format': self.rx_format, 
                    'tx_format': self.tx_format, 
                    'start_bytes': self.start_bytes, 
                    'end_bytes': self.end_bytes
                }


class Packet(object):
    
    def __init__(self,  packet=None):
        # Defaults
        self.name = ''     
        self.fields = []
        
        if packet:
            self.name = packet['name']
            if 'fields' in packet:
                self.fields = [Field(**f) for f in packet['fields']]
    
    def dump(self):
        fields = []
        for field in self.fields:
            fields.append(field.dump())
        
        return {
                    'name': self.name, 
                    'fields': fields
                }
    
    def struct_format(self):
        return "".join(f.struct_format() for f in self.fields)
    
    def types(self):
        types = []
        for f in self.fields:
            if f.name != Field.EMPTY_FIELD:
                types.append(f.type_desc())
        return types

class Field(object):
    
    EMPTY_FIELD = "EMPTY_FIELD"
    
    def __init__(self,  name,  type):
        self.name = name
        self.type = type
    
    def dump(self):
        return {
                    'name': self.name,
                    'type': self.type
                }
    
    def struct_format(self):
        if self.name == self.EMPTY_FIELD:
            return str(dtype(str(self.type)).itemsize) + 'x'
        else:
            return dtype(str(self.type)).char
    
    def type_desc(self):
        return (str(self.name.lower().replace(' ','_')), str(self.type))


class WrongPacketTypeError(Exception):
    """
    Exception raised when an unknown packet type is provided.
    
    Attributes:
        packet_type -- unknown packet type
    """
    
    def __init__(self, packet_type):
        self.packet_type = packet_type
    
    def __str__(self):
        return "Unknown packet type: " + repr(self.packet_type)

class PacketAlreadyExistsError(Exception):
    """
    Exception raised when trying to add a packet that already exists.
    
    Attributes:
        packet_num -- number of the packet
    """
    
    def __init__(self, packet_num):
        self.num = packet_num
    
    def __str__(self):
        return repr(self.num)
