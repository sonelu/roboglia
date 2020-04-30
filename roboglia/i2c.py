import smbus2
import os
from roboglia.base import BaseBus, RegisterWithExternalRepresentation, BaseDevice


class I2CBus(BaseBus):
    """Implements the base communication I2C using SMBus.
    """
    def __init__(self, parent, dictInfo):
        super().__init__(parent, dictInfo)
        self.porthandler = smbus2.SMBus(None)

    def open(self):
        """Opens the SMBus.
        """
        self.porthandler = smbus2.SMBus(self.port)

    def close(self):
        """Closes the SMBus port.
        """
        self.porthandler.close()
        
    def isOpen(self):
        """Returns `True` if we have a port open.
        """
        return self.porthandler.fd != None

    def read1Byte(self, dev_address, reg_address):
        """Reads one byte from a device.
        """
        return self.porthandler.read_byte_data(dev_address, reg_address)

    def read2Byte(self, dev_address, reg_address):
        """Reads two consecutive bytes from a device and returns one value
        assuming the first one is the low byte and the second is the high
        byte.
        """
        d0 = self.porthandler.read_byte_data(dev_address, reg_address)
        d1 = self.porthandler.read_byte_data(dev_address, reg_address+1)
        return d1*256 + d0

    def write1Byte(self, dev_address, reg_address, value):
        """Writes one byte to the device.
        """
        self.porthandler.write_byte_data(dev_address, reg_address, value)

    def write2Byte(self, dev_address, reg_address, value):
        """Writes two consecutive bytes to a device assuming lower byte
        of the value goes to the indicated address and higher byte to the next
        address.
        """
        self.porthandler.write_byte_data(dev_address, reg_address, value % 256)
        self.porthandler.write_byte_data(dev_address, reg_address+1, value //256)

    def swap(self, val):
        """Used to swap the bytes in a word.
        """
        return (( val & 0xFF) << 8) | ((val & 0xFF00) >> 8)

    def read1Word(self, dev_address, reg_address):
        """Reads a word from the device (used for devices that have word
        registers)
        .. note: SMBus read_word_data processes the bytes in the wrong 
                 order and they need to be swapped.
        """
        raw = self.porthandler.read_word_data(dev_address, reg_address)
        return self.swap(raw)

    def write1Word(self, dev_address, reg_address, value):
        """Writes a word to the device (used for devices that have word
        registers)
        .. note: SMBus write_word_data processes the bytes in the wrong 
                 order and they need to be swapped.
        """
        raw = self.swap(value)
        self.porthandler.write_word_data(dev_address, reg_address, raw)


class I2CRegister(RegisterWithExternalRepresentation):
    """Representation of a register in an I2C device.
    """
    def read(self):
        """Reads a register from the device.

        Read is done directly in the ``_int_value`` as we assume the device
        provides corect values for the register and the validations provided
        by the setter method are not necessarry.
        """
        device = self.parent
        bus = device.parent
        if self.type == 'B':
            if self.size == 1:
                self._int_value = bus.read1Byte(device.dev_id, self.address)
                return True
            elif self.size == 2:
                self._int_value = bus.read2Byte(device.dev_id, self.address)
                return True
        elif self.type == 'W':
            if self.size == 1:
                self._int_value = bus.read1Word(device.dev_id, self.address)
                return True
        # combination not implemented
        msg = "No read() implementation for type B and size {} for register {} of {}"
        raise ValueError(msg.format(self.size, self.name, self.parent.name))

    def write(self):
        """Writes a register to a divice.
        """
        device = self.parent
        bus = device.parent
        if self.type == 'B':
            if self.size == 1:
                bus.write1Byte(device.dev_id, self.address, self._int_value)
                return True
            elif self.size == 2:
                bus.write2Byte(device.dev_id, self.address, self._int_value)
                return True
        elif self.type == 'W':
            if self.size == 1:
                bus.write1Word(device.dev_id, self.address, self._int_value)
                return True
        # combination not implemented
        msg = "No write() implementation for type B and size {} for register {} of {}"
        raise ValueError(msg.format(self.size, self.name, self.parent.name))


class I2CDevice(BaseDevice):

    def __init__(self, parent, dictInfo):
        super().__init__(parent, dictInfo)

    def getModelPath(self, model):
        return os.path.join(os.path.dirname(__file__), 'devices/sensor', model+'.device')

    def initRegister(self, reginfo):
        """Default processing method for setting up a register.

        Does nothhing in the case of a BaseDevice and subclasses need to
        define their own internal format for the registers. This method
        should return a fully initialized register class based on the 
        information included in `reginfo`.

        Parameters
        ----------
        reginfo : dict
            A dictionry with the register attributes and values.

        Returns
        -------
        object
            An allocated registered which normally should be a
            `namedtuple` class with the attributes of the regiter 
            initialized from the `reginfo` dictionary.
        """
        if reginfo['Class'] == 'I2CRegister':
            return I2CRegister(parent=self, dictInfo = reginfo)
        else:
            return super.initRegister(reginfo)

