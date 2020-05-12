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

    Args:
        init_dict (dict): a dictionary with the initialization information.
            The same keys are required as for the super class
            :py:class:`BaseBus`.
    """
    def __init__(self, init_dict):
        super().__init__(init_dict)
        mock = init_dict.get('mock', False)
        check_options(mock, [True, False], 'bus', self.name, logger)
        if mock:
            self.__i2cbus = MockSMBus(self.robot, err=0.1)
        else:
            self.__i2cbus = SMBus()             # not opened

    @property
    def port_handler(self):
        return self.__i2cbus

    def open(self):
        # SMBus throws exceptions; we need to handle them
        try:
            # this will also attempt to open the bus
            self.port_handler.open(self.port)
        except Exception as e:
            logger.error(f'failed to open I2C bus {self.name}')
            logger.error(str(e))

    def close(self):
        try:
            self.port_handler.close()
        except Exception as e:
            logger.error(f'failed to close I2C bus {self.name}')
            logger.error(str(e))

    @property
    def is_open(self):
        """Returns `True` or `False` if the bus is open. Must be overridden
        by the subclass.
        """
        return self.port_handler.fd is not None

    def read(self, dev, reg):
        """Depending on the size of the register is calls the corresponding
        function from the ``SMBus``.
        """
        if not self.is_open:
            logger.error(f'attempted to read from a closed bus: {self.name}')
            return None
        else:
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

    def write(self, dev, reg, value):
        """Depending on the size of the register it calls the corresponding
        write function from ``SMBus``.
        """
        if not self.is_open:
            logger.error(f'attempted to write to a closed bus: {self.name}')
        else:
            if reg.size == 1:
                function = self.__i2cbus.write_byte_data
            elif reg.size == 2:
                function = self.__i2cbus.write_word_data
            else:
                mess = f'unexpected size {reg.size} ' + \
                    f'for register {reg.name} ' + \
                    f'of device {dev.name}'
                raise ValueError(mess)
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

    Args:
        init_dict (dict): dictionary with the initialization parameters.
            The required and optional keys are the one inherited from
            :py:class:`I2CBus` (which inherits on it's own from
            :py:class:`BaseBus`) and :py:class:`SharedBus`.
    """
    def __init__(self, init_dict):
        super().__init__(I2CBus, init_dict)

    def read_block_data(self, dev, address, length):
        """Invokes the block read from SMBus.

        Args:
            dev (BaseDevice): the device for which the block read is performed
            address (int): the start address
            length (int): the length of data to read

        Returns:
            list of int: a list of length ``length``

        Does not raise any exceptions, but logs any errors.
        """
        if not self.is_open:
            logger.error(f'attempted to read form a closed bus: {self.name}')
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

        Args:
            dev (BaseDevice): the device for which the block read is performed
            address (int): the start address
            length (int): the length of data to read

        Returns:
            list of int: a list of length ``length``

        Does not raise any exceptions, but logs any errors.
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

    def __init__(self, robot, err=0.1):
        self.__robot = robot
        self.__err = err
        self.fd = None

    def open(self, port):
        self.fd = port

    def close(self):
        self.fd = None
        # we do this so that the testing covers the error part of the branch
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
                value = max(reg.min, min(reg.max, reg.int_value + plus))
                return value
            else:
                return reg.int_value

    def read_byte_data(self, dev_id, address):
        logger.debug(f'reading BYTE from I2C bus {self.fd} '
                     f'device {dev_id} address {address}')
        return self.__common_read(dev_id, address)

    def read_word_data(self, dev_id, address):
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
        logger.debug(f'writting BYTE to I2C bus {self.fd} '
                     f'device {dev_id} address {address} value {value}')
        self.__common_write(dev_id, address, value)

    def write_word_data(self, dev_id, address, value):
        logger.debug(f'writting WORD to I2C bus {self.fd} '
                     f'device {dev_id} address {address} value {value}')
        self.__common_write(dev_id, address, value)

    def read_i2c_block_data(self, dev_id, address, length, force=None):
        if random.random() < self.__err:
            logger.error('*** random generated read-block error ***')
            raise OSError
        else:
            # we'll just return a random list of numbers
            return random.sample(range(0, 255), length)

    def write_i2c_block_data(self, dev_id, address, length, data):
        if random.random() < self.__err:
            logger.error('*** random generated write-block error ***')
            raise OSError
