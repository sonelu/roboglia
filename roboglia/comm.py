from dynamixel_sdk import PortHandler, PacketHandler
from serial import rs485
#from smbus2 import SMBus


class BaseBus():
    """A base abstract class for handling an arbitrary bus.

    You will normally subclass `BaseBus` and define particular functionality
    specific to the bus by impementing the methods of the `BaseBus`.
    This class only stores the name of the bus and the access to the
    physical object. Your subclass can add additional attributes and 
    methods to deal with the particularities of the real bus represented.

    Parameters
    ---------
    name
        A string used to identify the bus.

    port
        A string that indentifies technically the bus. For instance a
        serial bus would be `/dev/ttyUSB0` while an SPI bus might be
        represented as `0` only (indicating the SPI 0 bus).

    """
    def __init__(self, name, port):
        """Initializes the bus information.


        """
        self.name = name
        self.port = port

    def open(self):
        """Opens the actual physical bus. Must be overriden by the
        subclass.

        """
        pass

    def close(self):
        """Closes the actual physical bus. Must be overriden by the
        subclass.

        """
        pass

    def isOpen(self):
        """Returns `True` or `False` if the bus is open. Must be overriden 
        by the subclass.

        """
        return False


class DynamixelBus(BaseBus):
    """A class for handling the communication on a Dynamixel bus.

    Parameters
    ----------

    name : str
        Identifier of the bus. Ex. `lower_body`.

    port : str
        The port name for communication. Ex. `/dev/ttyUB0`.

    protocol : (1.0, 2.0)
        Could be `1.0` or `2.0` indicating the two possible protocls 
        supported by the `dynamixel_sdk` communincation.

    baudrate : int
        Desired baudrate for the port.

    rs485 : bool
        Set to `True` if you need the port to be configured (software) in
        RS485 mode.
    """
    def __init__(self, name, port, 
                protocol=2.0, baudrate=1000000, rs485=False):
        super().__init__(name, port)
        self.protocol = protocol
        self.baudrate = baudrate
        self.rs485 = rs485
        self.portHandler = None
        self.packetHandler = None

        # assigned devices
        self.devices = []

    def open(self):
        self.portHandler = PortHandler(self.port)
        self.portHandler.setBaudRate(self.baudrate)
        if self.rs485:
            self.portHandler.ser.rs485_mode = rs485.RS485Settings()
        self.portHandler.openPort()

        self.packetHandler = PacketHandler(self.protocol)


    def close(self):
        self.packetHandler = None
        self.portHandler.closePort()
        self.portHandler = None

    def isOpen(self):
        return self.packetHandler != None

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