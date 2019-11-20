from dynamixel_sdk import PortHandler, PacketHandler
from serial import rs485
#from smbus2 import SMBus

class DynamixelBus():

    def __init__(self, params):
        assert params['Class'] == 'DynamixelBus'
        self.name = params['Name']
        self.port = params['Port']
        self.protocol = float(params['Protocol'])
        self.baudrate = int(params['Baudrate'])
        self.rs485 = params['RS485'] == 'Y'

        self.portHandler = PortHandler(self.port)
        self.portHandler.setBaudRate(self.baudrate)
        if params['RS485'] == 'Y':
            self.portHandler.ser.rs485_mode = rs485.RS485Settings()
        self.portHandler.openPort()

        self.packetHandler = PacketHandler(self.protocol)

    def ping(self, dxl_id):
        return self.packetHandler.ping(self.portHandler, dxl_id)

    def broadcastPing(self):
        return self.packetHandler.broadcastPing(self.portHandler)

    def read1Byte(self, dxl_id, address, value):
        return self.packetHandler.read1ByteTxRx(self.portHandler, dxl_id, address, value)

    def read2Byte(self, dxl_id, address, value):
        return self.packetHandler.read2ByteTxRx(self.portHandler, dxl_id, address, value)

    def read4Byte(self, dxl_id, address, value):
        return self.packetHandler.read4ByteTxRx(self.portHandler, dxl_id, address, value)

    def write1Byte(self, dxl_id, address, value):
        return self.packetHandler.write1ByteTxRx(self.portHandler, dxl_id, address, value)

    def write2Byte(self, dxl_id, address, value):
        return self.packetHandler.write2ByteTxRx(self.portHandler, dxl_id, address, value)

    def write4Byte(self, dxl_id, address, value):
        return self.packetHandler.write4ByteTxRx(self.portHandler, dxl_id, address, value)

"""
class I2CBus():

    def __init__(self, params):
        assert params['Class'] == 'I2CBus'
        self.name = params['Name']
        self.port = params['Port']

        self.porthandler = SMBus(self.port)

    def read1byte(self, dev_address, reg_address):
        return self.porthandler.read_byte_data(dev_address, reg_address)

    def read2bytes(self, dev_address, reg_address):
        d0 = self.porthandler.read_byte_data(dev_address, reg_address)
        d1 = self.porthandler.read_byte_data(dev_address, reg_address+1)
        return d1*256 + d0
"""