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

from ..utils import check_key


logger = logging.getLogger(__name__)


class BaseBus():
    """A base abstract class for handling an arbitrary bus.

    You will normally subclass ``BaseBus`` and define particular functionality
    specific to the bus by impementing the methods of the ``BaseBus``.
    This class only stores the name of the bus and the access to the
    physical object. Your subclass can add additional attributes and
    methods to deal with the particularities of the real bus represented.

    Args:
        init_dict (dict): The dictionary used to initialize the bus.

    The following keys are exepcted in the dictionary:

    - ``name``: the name of the bus
    - ``port``: the port used by the bus

    Raises:
        KeyError: if ``port`` not supplied
    """
    def __init__(self, init_dict):
        # alredy checked by robot
        self._name = init_dict['name']
        check_key('port', init_dict, 'bus', self._name, logger)
        self._port = init_dict['port']

    @property
    def name(self):
        """(read-only) the bus name."""
        return self._name

    @property
    def port(self):
        """(read-only) the bus port."""
        return self._port

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

    @property
    def isOpen(self):
        """Returns `True` or `False` if the bus is open. Must be overriden
        by the subclass.
        """
        return False

    def read(self, dev, reg):
        """Reads one standrd information from the bus. Must be overwriden.
        """
        pass

    def write(self, dev, reg, val):
        """Writes one standrd information from the bus. Must be overwriden.
        """
        pass


class FileBus(BaseBus):
    """A bus that writes to a file with cache.

    Read returns the last writen data. Provided for testing purposes.

    Args:
        init_dict (dict): the initialization dictionary. Same parameters
            required as for :py:class:BaseBus.

    Raises:
        same as :py:class:BaseBus
    """
    def __init__(self, init_dict):
        super().__init__(init_dict)
        self.__fp = None
        self.__last = {}
        logger.debug(f'FileBus {self._name} initialized')

    def open(self):
        """Opens the file associated with the ``FileBus``."""
        self.__fp = open(self._port, 'w')
        logger.debug(f'FileBus {self._name} opened')

    def close(self):
        """Closes the file associated with the ``FileBus``."""
        self.__fp.close()
        logger.debug(f'FileBus {self._name} closed')

    @property
    def isOpen(self):
        """Returns ``True`` is the file is opened."""
        return False if not self.__fp else not self.__fp.closed

    def write(self, dev, reg, value):
        """Updates the values in the FileBus.

        Args:
            dev (obj): is the device that is writing
            reg (obj): is the regoster object that is written
            value (int): is the value beein written.

        The method will update the buffer with the value provided then
        will log the write on the file. A flush() is performed in case
        you want to inspect the content of the file while the robot
        is running.
        """
        if not self.isOpen:
            logger.error(f'attempt to write to closed bus {self.name}')
        else:
            self.__last[(dev.dev_id, reg.address)] = value
            text = f'written {value} in register {reg.name} ' + \
                   f'({reg.address}) of device {dev.dev_id}'
            self.__fp.write(text + '\n')
            self.__fp.flush()
            logger.debug(f'FileBus {self._name} {text}')

    def read(self, dev, reg):
        """Reads the value from the buffer of FileBus and logs it.

        Args:
            dev (obj): the device being read
            reg (obj): register obhject being read

        Returns:
            int : the value from the requested register

        The method will try to read from the buffer the value. If there
        is no value in the buffer it will be defaulted from the register's
        default value. The method will log the read to the file and return
        the value.
        """
        if not self.isOpen:
            logger.error(f'attempt to write to closed bus {self.name}')
            return None
        else:
            if (dev.dev_id, reg.address) not in self.__last:
                self.__last[(dev.dev_id, reg.address)] = reg.default
            val = self.__last[(dev.dev_id, reg.address)]
            text = f'read {val} from register {reg.name} ){reg.address}) ' + \
                   f'of device {dev.dev_id}'
            self.__fp.write(text + '\n')
            self.__fp.flush()
            logger.debug(f'FileBus {self._name} {text}')
            return val

    def __str__(self):
        result = ''
        for (dev_id, reg_address), value in self.__last.items():
            result += f'Device {dev_id}, Register ID {reg_address}: ' + \
                      f'VALUE {value}\n'
        return result
