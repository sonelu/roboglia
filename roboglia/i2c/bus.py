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

    Parameters
    ----------
    mock: bool
        Indicates if the I2C bus will use mock communication. It is
        provided for testing of functionality in CI environment. If ``True``
        the bus will use the :py:class:`MockSMBus` class for performing
        read and write operations.
    """
    def __init__(self, mock=False, **kwargs):
        super().__init__(**kwargs)
        check_options(mock, [True, False], 'bus', self.name, logger)
        if mock:
            self.__i2cbus = MockSMBus(self.robot, err=0.1)
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
        else:
            dev = reg.device
            if reg.size == 1:
                function = self.__i2cbus.read_byte_data
            elif reg.size == 2:
                function = self.__i2cbus.read_word_data
            else:
                raise NotImplementedError
            try:
                return function(dev.dev_id, reg.address)
            except Exception as e:
                logger.error(f'failed to execute read command on I2C bus '
                             f'{self.name} for device {dev.name} and '
                             f'register {reg.name}')
                logger.error(str(e))
                return None

    def write(self, reg, value):
        """Depending on the size of the register it calls the corresponding
        write function from ``SMBus``.
        """
        if not self.is_open:
            logger.error(f'attempted to write to a closed bus: {self.name}')
        else:
            dev = reg.device
            if reg.size == 1:
                function = self.__i2cbus.write_byte_data
            elif reg.size == 2:
                function = self.__i2cbus.write_word_data
            else:
                raise NotImplementedError
            try:
                function(dev.dev_id, reg.address, value)
            except Exception as e:
                logger.error(f'failed to execute write command on I2C bus '
                             f'{self.name} for device {dev.name} and '
                             f'register {reg.name}')
                logger.error(str(e))


class SharedI2CBus(SharedBus):
    """An I2C bus that can be shared between threads in a multi-threaded
    environment.

    It inherits all the initialization paramters from :py:class:`SharedBus` and
    :py:class:`I2CBus`.
    """
    def __init__(self, **kwargs):
        super().__init__(I2CBus, **kwargs)

    def read_block_data(self, dev, address, length):
        """Invokes the block read from SMBus.

        Does not raise any exceptions, but logs any errors.

        Paramters
        ---------
        dev: BaseDevice or subclass
            The device for which the block read is performed

        address: int
            The start address

        length: int
            The length of data to read

        Returns
        -------
        list of int:
            a list of length ``length``
        """
        if not self.is_open:
            logger.error(f'attempted to read from a closed bus: {self.name}')
            return None

        if not self.can_use():
            logger.error(f'{self.name} failed to acquire bus')
            return None

        try:
            data = self.port_handler.read_i2c_block_data(dev.dev_id,
                                                         address,
                                                         length)
        except Exception as e:
            logger.error(f'{self.name} failed to read block data '
                         f'for device {dev.name}')
            logger.error(str(e))
            self.stop_using()
            return None

        self.stop_using()
        return data

    def write_block_data(self, dev, address, length, data):
        """Invokes the block read from SMBus.

        Does not raise any exceptions, but logs any errors.

        Parameters
        ----------
        dev: BaseDevice or subclass
            The device for which the block read is performed

        address: int
            The start address

        length: int
            The length of data to read

        data: list of int
            The data to be written
        """
        if not self.is_open:
            logger.error(f'attempted to write to a closed bus: {self.name}')
            return None

        if not self.can_use():
            logger.error(f'{self.name} failed to acquire bus')
            return None

        try:
            data = self.port_handler.write_i2c_block_data(dev.dev_id,
                                                          address,
                                                          length,
                                                          data)
        except Exception as e:
            logger.error(f'{self.name} failed to write block data '
                         f'for device {dev.name}')
            logger.error(str(e))

        self.stop_using()


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
        raise OSError('error closing the bus')

    def __common_read(self, dev_id, address):
        if random.random() < self.__err:
            logger.error('*** random generated read error ***')
            raise OSError
        else:
            device = self.__robot.device_by_id(dev_id)
            reg = device.register_by_address(address)
            if reg.access == 'R':
                # we randomize the read
                plus = random.randint(-10, 10)
                value = max(reg.minim, min(reg.maxim, reg.int_value + plus))
                return value
            else:
                return reg.int_value

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
            raise OSError
        else:
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
        else:
            # we'll just return a random list of numbers
            return random.sample(range(0, 255), length)

    def write_i2c_block_data(self, dev_id, address, length, data):
        """Simulates the write of one block of data."""
        if random.random() < self.__err:
            logger.error('*** random generated write-block error ***')
            raise OSError
