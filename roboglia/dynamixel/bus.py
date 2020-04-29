import dynamixel_sdk
from serial import rs485
from ..base.bus import BaseBus


class DynamixelBus(BaseBus):

    def __init__(self, init_dict):
        super().__init__(init_dict)
        self.baudrate = init_dict['baudrate']
        self.protocol = init_dict['protocol']
        self.rs485 = init_dict.get('rs485', False)
        self.port_handler = None
        self.packet_handler = None

    def open(self):
        """Opens the actual physical bus. Must be overriden by the
        subclass.
        """
        self.port_handler = dynamixel_sdk.PortHandler(self.port)
        self.port_handler.setBaudRate(self.baudrate)
        if self.rs485:
            self.port_handler.ser.rs485_mode = rs485.RS485Settings()
        self.port_handler.openPort()

        self.packet_handler = dynamixel_sdk.PacketHandler(self.protocol)
        
    def close(self):
        """Closes the actual physical bus. Must be overriden by the
        subclass.
        """
        self.packet_handler = None
        self.port_handler.closePort()
        self.port_handler = None

    def isOpen(self):
        """Returns `True` or `False` if the bus is open. Must be overriden 
        by the subclass.
        """
        return self.port_handler != None

    def ping(self, dxl_id):
        _, cerr, derr =  self.packet_handler.ping(self.port_handler, dxl_id)
        if cerr  == 0 and derr == 0:
            return True
        else:
            return False

    def read(self, dev, reg):
        """Depending on the size of the register is calls the corresponding
        TxRx function from the packet handler.
        If the result is ok (communication error and dynamixel error are both
        0) then the obtained value is returned. Otherwise it will throw a
        ConnectionError. Callers shoud intercept the exception if they 
        want to control it.
        """
        if reg.size == 1:
            function = self.packet_handler.read1ByteTxRx
        elif reg.size == 2:
            function = self.packet_handler.read2ByteTxRx
        elif reg.size == 4:
            function = self.packet_handler.read4ByteTxRx
        else:
            raise ValueError(f'unexpected size {reg.size} for register {reg.name} of device {dev.name}')
        res, cerr, derr = function(self.port_handler, dev.dev_id, reg.address)
        if cerr == 0 and derr == 0:
            return res
        else:
            raise ConnectionError(f'failed to communicte wtih bus {self.name}, cerr={cerr}, derr={derr}')

    def write(self, dev, reg, value):
        """Depending on the size of the register is calls the corresponding
        TxRx function from the packet handler.
        If the result is not ok (communication error or dynamixel error are not 
        both 0) it will throw a ConnectionError. Callers shoud intercept the 
        exception if they want to control it.
        """
        if reg.size == 1:
            function = self.packet_handler.write1ByteTxRx
        elif reg.size == 2:
            function = self.packet_handler.write2ByteTxRx
        elif reg.size == 4:
            function = self.packet_handler.write4ByteTxRx
        else:
            raise ValueError(f'unexpected size {reg.size} for register {reg.name} of device {dev.name}')
        cerr, derr = function(self.port_handler, dev.dev_id, reg.address, value)
        if cerr != 0 or derr != 0:
            raise ConnectionError(f'failed to communicte wtih bus {self.name}, cerr={cerr}, derr={derr}')
           
    
