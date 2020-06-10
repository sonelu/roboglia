# Copyright (C) 2020  Alex Sonea

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import logging
import random
from smbus2 import SMBus

from ..utils import check_options
from ..base import BaseBus, SharedBus

logger = logging.getLogger(__name__)


class I2CBus(BaseBus):
    """Implements a communication bus for I2C devices.

    ``I2CBus`` has the same paramters as :py:class:`BaseBus`. Please
    refer to this class for the details of the parameters.

    In addition there is an extra parameter `mock`.

    At this moment the ``I2CBus`` supports devices with byte and word
    registers and permits defining composed regsiters with ``size`` > 1
    that are treated as a single register.

    .. note:: A gyroscope sensor might have registers for the z, y and z
        axes reading that are stored as pairs of registers like this::

            gyro_x_l    #0x28
            gyro_x_h    #0x29
            gyro_y_l    #0x2A
            gyro_y_h    #0x2B
            gyro_z_l    #0x2C
            gyro_z_h    #0x2D

        For simplicity it is possible to define these registers like this
        in the device template::

            registers:
                gyro_x:
                    address: 0x28
                    size: 2
                gyro_y:
                    address: 0x2A
                    size: 2
                gyro_z:
                    address: 0x2C
                    size: 2

        By default the registers are ``Byte`` and the order of data is
        low-high as described in the :py:class:roboglia.base.`BaseRegister`.
        The bus will handle this by reading the two registers sequentially
        and computing the register's value using the size of the register
        and the order.

    Parameters
    ----------
    mock: bool
        Indicates if the I2C bus will use mock communication. It is
        provided for testing of functionality in CI environment. If ``True``
        the bus will use the :py:class:`MockSMBus` class for performing
        read and write operations.
    """
    def __init__(self, mock=False, err=0.1, **kwargs):
        super().__init__(**kwargs)
        check_options(mock, [True, False], 'bus', self.name, logger)
        if mock:
            self.__i2cbus = MockSMBus(self.robot, err=err)
        else:
            self.__i2cbus = SMBus()             # not opened

    @property
    def port_handler(self):
        return self.__i2cbus

    def open(self):
        """Opens the communication port."""
        # SMBus throws exceptions; we need to handle them
        try:
            # this will also attempt to open the bus
            self.port_handler.open(self.port)
        except Exception as e:
            logger.error(f'failed to open I2C bus {self.name}')
            logger.error(str(e))

    def close(self):
        """Closes the communication port, if the ``super().close()`` allows
        it. If the bus is used in any sync loops, the close request might
        fail.
        """
        if super().close():             # pragma: no branch
            try:
                self.port_handler.close()
            except Exception as e:
                logger.error(f'failed to close I2C bus {self.name}')
                logger.error(str(e))

    @property
    def is_open(self):
        """Returns `True` or `False` if the bus is open."""
        return self.port_handler.fd is not None

    def read(self, reg):
        """Depending on the size of the register is calls the corresponding
        function from the ``SMBus``.
        """
        if not self.is_open:
            logger.error(f'attempted to read from a closed bus: {self.name}')
            return None

        dev = reg.device
        if reg.word:
            function = self.__i2cbus.read_word_data
            base = 65536
        else:
            function = self.__i2cbus.read_byte_data
            base = 256

        values = [0] * reg.size
        for pos in range(reg.size):
            try:
                values[pos] = function(dev.dev_id, reg.address + pos)
            except Exception as e:
                logger.error(f'failed to execute read command on I2C bus '
                             f'{self.name} for device {dev.name} and '
                             f'register {reg.name}')
                logger.error(str(e))
                return None
        if reg.order == 'HL':
            values = values.reverse()
        value = 0
        for pos in range(reg.size):
            value = value * base + values[-pos-1]
        return value

    def write(self, reg, value):
        """Depending on the size of the register it calls the corresponding
        write function from ``SMBus``.
        """
        if not self.is_open:
            logger.error(f'attempted to write to a closed bus: {self.name}')

        dev = reg.device
        if reg.word:
            function = self.__i2cbus.write_word_data
            base = 65536
        else:
            function = self.__i2cbus.write_byte_data
            base = 256

        buffer = [0] * reg.size
        data = reg.int_value
        for pos in range(reg.size):
            buffer[pos] = data % base
            data = data // base
        if reg.order == 'HL':
            buffer = buffer.reverse()
        for pos, item in enumerate(buffer):
            try:
                function(dev.dev_id, reg.address + pos, item)
            except Exception as e:
                logger.error(f'Failed to execute write command on I2C bus '
                             f'{self.name} for device {dev.name} and '
                             f'register {reg.name}')
                logger.error(str(e))
                return None

    def read_block(self, device, start_address, length):
        """Reads a block of registers of given length.

        Parameters
        ----------
        device: I2CDevice or subclass
            The device on the I2C bus

        start_addr: int
            The start address to read from

        length: int
            Number of bytes to read from the device

        Returns
        -------
        list of int:
            A list of bytes of length ``length`` with the values from the
            device. It intercepts any exceptions and logs them, in that case
            the return will be ``None``.
        """
        if not self.is_open:
            logger.error(f'attempted to read from a closed bus: {self.name}')
            return None

        try:
            data = self.__i2cbus.read_i2c_block_data(
                device.dev_id, start_address, length)
        except Exception as e:
            logger.error(f'Failed to execute read block command on I2C bus '
                         f'{self.name} for device {device.name}')
            logger.error(str(e))
            return None
        return data

    def write_block(self, device, start_address, data):
        """Writes a block of registers of given length.

        Parameters
        ----------
        device: I2CDevice or subclass
            The device on the I2C bus

        start_addr: int
            The start address to read from

        data: list of int
            The bytes to write to the device

        Returns
        -------
        ``None``:
            It intercepts any exceptions and logs them.
        """
        if not self.is_open:
            logger.error(f'attempted to write to a closed bus: {self.name}')

        try:
            self.__i2cbus.write_i2c_block_data(
                device.dev_id, start_address, data)
        except Exception as e:
            logger.error(f'Failed to execute write block command on I2C bus '
                         f'{self.name} for device {device.name}')
            logger.error(str(e))


class SharedI2CBus(SharedBus):
    """An I2C bus that can be shared between threads in a multi-threaded
    environment.

    It inherits all the initialization paramters from :py:class:`SharedBus` and
    :py:class:`I2CBus`.
    """
    def __init__(self, **kwargs):
        super().__init__(I2CBus, **kwargs)


class MockSMBus(SMBus):
    """Class for testing. Overides the ``SMBus`` methods in order to
    simulate the data exchange. Intended for use in the CI testing.

    Parameters
    ----------
    robot: BaseRobot
        The robot (we need it to access the registers)

    err: float
        A small number that will be used for generating random communication
        errors so that we can perform testing of the code handling those.
    """
    def __init__(self, robot, err=0.1):
        self.__robot = robot
        self.__err = err
        self.fd = None

    def open(self, port):
        """mock opens the bus."""
        self.fd = port

    def close(self):
        """Mock closes the bus. It raises a OSError at the end so that
        the code can be checked for this behavior too.
        """
        self.fd = None
        # we do this so that the testing covers
        # the error part of the branch
        raise OSError('** auto generated: error closing the bus **')

    def __common_read(self, dev_id, address):
        if random.random() < self.__err:
            logger.error('*** random generated read error ***')
            raise OSError
        # non-error case
        device = self.__robot.device_by_id(dev_id)
        reg = device.register_by_address(address)
        if reg is None:
            # it's the higher digits of the register; we'll return
            # 0 and the lower digits will return the full register value
            return 0
        if reg.access == 'R':
            # we randomize the read
            plus = random.randint(-10, 10)
            value = max(reg.minim, min(reg.maxim, reg.int_value + plus))
        else:
            value = reg.int_value
        return value

    def read_byte_data(self, dev_id, address):
        """Simulates the read of 1 Byte."""
        logger.debug(f'reading BYTE from I2C bus {self.fd} '
                     f'device {dev_id} address {address}')
        return self.__common_read(dev_id, address)

    def read_word_data(self, dev_id, address):
        """Simulates the read of 1 Word."""
        logger.debug(f'reading WORD from I2C bus {self.fd} '
                     f'device {dev_id} address {address}')
        return self.__common_read(dev_id, address)

    def __common_write(self, dev_id, address, value):
        if random.random() < self.__err:
            logger.error('*** random generated write error ***')
            raise OSError('*** random generated write error ***')
        return None

    def write_byte_data(self, dev_id, address, value):
        """Simulates the write of one byte."""
        logger.debug(f'writting BYTE to I2C bus {self.fd} '
                     f'device {dev_id} address {address} value {value}')
        self.__common_write(dev_id, address, value)

    def write_word_data(self, dev_id, address, value):
        """Simulates the write of one word."""
        logger.debug(f'writting WORD to I2C bus {self.fd} '
                     f'device {dev_id} address {address} value {value}')
        self.__common_write(dev_id, address, value)

    def read_i2c_block_data(self, dev_id, address, length, force=None):
        """Simulates the read of one block of data."""
        if random.random() < self.__err:
            logger.error('*** random generated read-block error ***')
            raise OSError
        # we'll just return a random list of numbers
        return random.sample(range(0, 255), length)

    def write_i2c_block_data(self, dev_id, address, data):
        """Simulates the write of one block of data."""
        if random.random() < self.__err:
            logger.error('*** random generated write-block error ***')
            raise OSError
