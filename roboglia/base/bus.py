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
import threading

from ..utils import check_key, check_type, check_options


logger = logging.getLogger(__name__)


class BaseBus():
    """A base abstract class for handling an arbitrary bus.

    You will normally subclass ``BaseBus`` and define particular functionality
    specific to the bus by implementing the methods of the ``BaseBus``.
    This class only stores the name of the bus and the access to the
    physical object. Your subclass can add additional attributes and
    methods to deal with the particularities of the real bus represented.

    Args:
        init_dict (dict): The dictionary used to initialize the bus.

    The following keys are expected in the dictionary:

    - ``name``: the name of the bus
    - ``port``: the port used by the bus

    Optionally the following parameters can be provided:

    - ``auto``: the bus should be opened automatically when the robot
      starts; defaults to ``True``

    Raises:
        KeyError: if ``port`` not supplied
    """
    def __init__(self, init_dict):
        # already checked by robot
        self.__name = init_dict['name']
        self.__robot = init_dict['robot']
        check_key('port', init_dict, 'bus', self.__name, logger)
        self.__port = init_dict['port']
        self.__auto_open = init_dict.get('auto', True)
        check_options(self.__auto_open, [True, False], 'bus',
                      self.__name, logger)

    @property
    def name(self):
        """(read-only) the bus name."""
        return self.__name

    @property
    def robot(self):
        """The robot that owns the bus."""
        return self.__robot

    @property
    def port(self):
        """(read-only) the bus port."""
        return self.__port

    @property
    def auto_open(self):
        """Indicates if the bus should be opened by the robot when
        initializing."""
        return self.__auto_open

    def open(self):
        """Opens the actual physical bus. Must be overridden by the
        subclass.
        """
        raise NotImplementedError

    def close(self):
        """Closes the actual physical bus. Must be overridden by the
        subclass.
        """
        raise NotImplementedError

    @property
    def is_open(self):
        """Returns `True` or `False` if the bus is open. Must be overridden
        by the subclass.
        """
        raise NotImplementedError

    def read(self, dev, reg):
        """Reads one standard information from the bus. Must be overridden.
        """
        raise NotImplementedError

    def write(self, dev, reg, val):
        """Writes one standard information from the bus. Must be overridden.
        """
        raise NotImplementedError


class FileBus(BaseBus):
    """A bus that writes to a file with cache.

    Read returns the last written data. Provided for testing purposes.

    Args:
        init_dict (dict): the initialization dictionary. Same parameters
            required as for :py:class:`BaseBus`.

    Raises:
        same as :py:class:`BaseBus`.
    """
    def __init__(self, init_dict):
        super().__init__(init_dict)
        self.__fp = None
        self.__last = {}
        logger.debug(f'FileBus {self.name} initialized')

    def open(self):
        """Opens the file associated with the ``FileBus``."""
        self.__fp = open(self.port, 'w')
        logger.debug(f'FileBus {self.name} opened')

    def close(self):
        """Closes the file associated with the ``FileBus``."""
        if self.is_open:
            self.__fp.close()
            logger.debug(f'FileBus {self.name} closed')

    @property
    def is_open(self):
        """Returns ``True`` is the file is opened."""
        return False if not self.__fp else not self.__fp.closed

    def write(self, dev, reg, value):
        """Updates the values in the FileBus.

        Args:
            dev (obj): is the device that is writing
            reg (obj): is the register object that is written
            value (int): is the value beeing written.

        Raises:
            the method intercept the raise errors from writing to the
            physical file and converts them to errors in the log file
            so that the rest of the program can continue uninterrupted.

        The method will update the buffer with the value provided then
        will log the write on the file. A flush() is performed in case
        you want to inspect the content of the file while the robot
        is running.
        """
        if not self.is_open:
            logger.error(f'attempt to write to closed bus {self.name}')
        else:
            self.__last[(dev.dev_id, reg.address)] = value
            text = f'written {value} in register {reg.name} ' + \
                   f'({reg.address}) of device {dev.dev_id}'
            try:
                self.__fp.write(text + '\n')
                self.__fp.flush()
            except Exception:
                logger.error(f'error executing write and flush to file '
                             f'for bus: {self.name}')
            logger.debug(f'FileBus {self.name} {text}')

    def read(self, dev, reg):
        """Reads the value from the buffer of ``FileBus`` and logs it.

        Args:
            dev (obj): the device being read
            reg (obj): register object being read

        Returns:
            int : the value from the requested register

        Raises:
            the method intercept the raise errors from writing to the
            physical file and converts them to errors in the log file
            so that the rest of the program can continue uninterrupted.

        The method will try to read from the buffer the value. If there
        is no value in the buffer it will be defaulted from the register's
        default value. The method will log the read to the file and return
        the value.
        """
        if not self.is_open:
            logger.error(f'attempt to read from a closed bus {self.name}')
            return None
        else:
            if (dev.dev_id, reg.address) not in self.__last:
                self.__last[(dev.dev_id, reg.address)] = reg.default
            val = self.__last[(dev.dev_id, reg.address)]
            text = f'read {val} from register {reg.name} ){reg.address}) ' + \
                   f'of device {dev.dev_id}'
            try:
                self.__fp.write(text + '\n')
                self.__fp.flush()
            except Exception:
                logger.error(f'error executing write and flush to file '
                             f'for bus: {self.name}')
            logger.debug(f'FileBus {self.name} {text}')
            return val

    def __str__(self):
        result = ''
        for (dev_id, reg_address), value in self.__last.items():
            result += f'Device {dev_id}, Register ID {reg_address}: ' + \
                      f'VALUE {value}\n'
        return result


class SharedBus():

    def __init__(self, BusClass, init_dict):
        self.__main_bus = BusClass(init_dict)
        self.__timeout = init_dict.get('timeout', 0.5)
        check_type(self.__timeout, float, 'bus', init_dict['name'], logger)
        if self.__timeout > 0.5:
            logger.warning(f'timeout {self.__timeout} for shareable '
                           f'{init_dict["name"]} might be excessive.')
        self.__lock = threading.Lock()

    @property
    def timeout(self):
        """Returns the timeout for requesting access to lock."""
        return self.__timeout

    def can_use(self):
        """Tries to acquire the resource on behalf of the caller.

        Returns:
            bool: ``True`` if managed to acquire the resource, ``False`` if
                  not. It is the responsibility of the caller to decide what
                  to do in case there is a ``False`` return including
                  logging or Raising.
        """
        return self.__lock.acquire(timeout=self.__timeout)

    def stop_using(self):
        """Releases the resource."""
        self.__lock.release()

    def naked_read(self, dev, reg):
        """Calls the main bus without invoking the lock."""
        return self.__main_bus.read(dev, reg)

    def naked_write(self, dev, reg, value):
        """Calls the main bus without invoking the lock."""
        self.__main_bus.write(dev, reg, value)

    def read(self, dev, reg):
        """Wraps the main bus call in a request for lock."""
        if self.can_use():
            value = self.__main_bus.read(dev, reg)
            self.stop_using()
            return value
        else:
            logger.error(f'failed to acquire bus {self.__main_bus.name}')
            return None

    def write(self, dev, reg, value):
        """Wraps the main bus call in a request for lock."""
        if self.can_use():
            self.__main_bus.write(dev, reg, value)
            self.stop_using()
        else:
            logger.error(f'failed to acquire bus {self.__main_bus.name}')

    def __getattr__(self, name):
        return getattr(self.__main_bus, name)


class SharedFileBus(SharedBus):

    def __init__(self, init_dict):
        super().__init__(FileBus, init_dict)

    def __str__(self):
        return FileBus.__str__(self)
