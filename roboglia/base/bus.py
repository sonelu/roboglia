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

from ..utils import check_type, check_options, check_not_empty


logger = logging.getLogger(__name__)


class BaseBus():
    """A base abstract class for handling an arbitrary bus.

    You will normally subclass ``BaseBus`` and define particular functionality
    specific to the bus by implementing the methods of the ``BaseBus``.
    This class only stores the name of the bus and the access to the
    physical object. Your subclass can add additional attributes and
    methods to deal with the particularities of the real bus represented.

    Parameters
    ----------
    name: str
        The name of the bus

    robot: BaseRobot
        A reference to the robot using the bus

    port: any
        An identification for the physical bus access. Some busses have
        string description like ``/dev/ttySC0`` while others could be just
        integers (like in the case of I2C or SPI buses)

    auto: Bool
        If ``True`` the bus will be opened when the robot is started by
        calling :py:meth:`BaseRobot.start`. If ``False`` the bus will be
        left closed during robot initialization and needs to be opened
        by the programmer.

    Raises:
        KeyError: if ``port`` not supplied
    """
    def __init__(self, name='BUS', robot=None, port='', auto=True, **kwargs):
        # already checked by robot
        check_not_empty(robot, 'robot', 'bus', name, logger)
        check_not_empty(port, 'port', 'bus', name, logger)
        self.__name = name
        self.__robot = robot
        self.__port = port
        self.__auto_open = auto
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
        subclass, but the implementation in the subclass should first check
        for the return from this method before actually closing the bus as
        dependent object on this bus might be affected::

            def close(self):
                if super().close()
                    ... do the close activities
                # optional; the handling in the ``BaseBus.close()`` will
                # issue error message to log
                else:
                    logger.<level>('message')
        """
        for sync in self.robot.syncs.values():
            # we need to compare by names and not by object ids because
            # sync.bus == self will not work:
            # sync.bus could be a SharedBus and
            # self will be the base bus (ex. FileBus or Dynamixel Bus)
            if sync.bus.name == self.name and sync.started:
                logger.error(f'attempted to close bus {self.name} that is '
                             f'used by running syncs')
                return False
        return True

    def __repr__(self):
        """Returrns a representation of a BaseBus that includes the name of
        the class, the port and the status (open or closed)."""
        return f'<{self.__class__.__name__} port={self.port} ' + \
               f'open={self.is_open}>'

    @property
    def is_open(self):
        """Returns `True` or `False` if the bus is open. Must be overridden
        by the subclass.
        """
        raise NotImplementedError

    def read(self, reg):
        """Reads one register information from the bus. Must be overridden.

        Parameters
        ----------
        reg: BaseRegister or subclass
            The register object that needs to be read. Keep in mind that
            the register object also contains a reference to the device
            in the ``device`` attribute and it is up to the subclass to
            determine the way the information must be processed before
            providing it to the caller.

        Returns
        -------
        int
            Typically it would return an ``int`` that will have to be
            handled by the caller.
        """
        raise NotImplementedError

    def write(self, reg, val):
        """Writes one register information from the bus. Must be overridden.

        Parameters
        ----------
        reg: BaseRegister or subclass
            The register object that needs to be written. Keep in mind that
            the register object also contains a reference to the device
            in the ``device`` attribute and it is up to the subclass to
            determine the way the information must be processed before
            providing it actual device.

        val: int
            The value needed to the written to the device.
        """
        raise NotImplementedError


class FileBus(BaseBus):
    """A bus that writes to a file with cache provided for testing purposes.

    Writes by this class are send to a file stream and also buffered in a
    local memory. Reads use this buffer to return values or use the default
    values from the register defintion.

    Same parameters as :py:class:`BaseBus`.
    """
    def __init__(self, name='FILEBUS', robot=None, port='', auto=True,
                 **kwargs):
        super().__init__(name=name,
                         robot=robot,
                         port=port,
                         auto=auto,
                         **kwargs)
        self.__fp = None
        self.__last = {}
        logger.debug(f'FileBus "{self.name}" initialized')

    def open(self):
        """Opens the file associated with the ``FileBus``."""
        if self.is_open:
            logger.warning(f'bus {self.name} already open')
        else:
            self.__fp = open(self.port, 'w')
            logger.debug(f'FileBus {self.name} opened')

    def close(self):
        """Closes the file associated with the ``FileBus``."""
        if self.is_open:
            if super().close():
                self.__fp.close()
                logger.debug(f'FileBus {self.name} closed')

    @property
    def is_open(self):
        """Returns ``True`` is the file is opened."""
        return False if not self.__fp else not self.__fp.closed

    def write(self, reg, value):
        """Updates the values in the FileBus.

        The method will update the buffer with the value provided then
        will log the write on the file. A flush() is performed in case
        you want to inspect the content of the file while the robot
        is running.

        File writing errors are intercepted and logged but no Exception is
        raised.

        Parameters
        ----------
        reg: BaseRegister or subclass
            The register object that needs to be written. Keep in mind that
            the register object also contains a reference to the device
            in the ``device`` attribute and it is up to the subclass to
            determine the way the information must be processed before
            providing it actual device.

        value: int
            The value needed to the written to the device.
        """
        if not self.is_open:
            logger.error(f'attempt to write to closed bus {self.name}')
        else:
            self.__last[(reg.device.dev_id, reg.address)] = value
            text = f'written {value} in register "{reg.name}"" ' + \
                   f'({reg.address}) of device "{reg.device.name}" ' + \
                   f'({reg.device.dev_id})'
            try:
                self.__fp.write(text + '\n')
                self.__fp.flush()
            except Exception:
                logger.error(f'error executing write and flush to file '
                             f'for bus: {self.name}')
            logger.debug(f'FileBus "{self.name}" {text}')

    def read(self, reg):
        """Reads the value from the buffer of ``FileBus`` and logs it.

        The method intercepts the ``raise`` errors from writing to the
        physical file and converts them to errors in the log file
        so that the rest of the program can continue uninterrupted.

        The method will try to read from the buffer the value. If there
        is no value in the buffer it will be defaulted from the register's
        default value. The method will log the read to the file and return
        the value.

        Parameters
        ----------
        reg: BaseRegister or subclass
            The register object that needs to be read. Keep in mind that
            the register object also contains a reference to the device
            in the ``device`` attribute and it is up to the subclass to
            determine the way the information must be processed before
            providing it to the caller.

        Returns
        -------
        int
            Typically it would return an ``int`` that will have to be
            handled by the caller.
        """
        if not self.is_open:
            logger.error(f'attempt to read from closed bus {self.name}')
            return None
        # normal processing
        if (reg.device.dev_id, reg.address) not in self.__last:
            self.__last[(reg.device.dev_id, reg.address)] = reg.default
        val = self.__last[(reg.device.dev_id, reg.address)]
        text = f'read {val} from register "{reg.name}" ({reg.address}) ' +\
               f'of device "{reg.device.name}" ({reg.device.dev_id})'
        try:
            self.__fp.write(text+'\n')
            self.__fp.flush()
        except Exception:
            logger.error(f'error executing write and flush to file '
                         f'for bus: {self.name}')
        logger.debug(f'FileBus "{self.name}" {text}')
        return val

    def __str__(self):
        """The string representation of the ``FileBus`` is a dump of the
        internal buffer.
        """
        result = ''
        for (dev_id, reg_address), value in self.__last.items():
            result += f'Device {dev_id}, Register ID {reg_address}: ' + \
                      f'VALUE {value}\n'
        return result


class SharedBus():
    """Implements a bus that provides a locking mechanism for the access to
    the underlying hardware, aimed specifically for use in multi-threaded
    environments where multiple jobs could compete for access to one single
    bus.

    .. note:: This class implements ``__getattr__`` so that any calls to
        an instance of this class that are not already implemented bellow will
        be passed to the internal instance of ``BusClass`` that was created
        at instantiation. This way you can access all the attributes and
        methods of the ``BusClass`` instance transparently, as long as they
        are not already overridden by this class.

    Parameters
    ----------
    BusClass: BaseBus subclass
        The class that will be wrapped by the ``SharedBus``

    timeout: float
        A timeout for acquiring the lock that controls the access to the bus

    **kwargs:
        keyword arguments that are passed to the BusClass for
        instantiation
    """
    def __init__(self, BusClass, timeout=0.5, **kwargs):
        self.__main_bus = BusClass(**kwargs)
        self.__timeout = timeout
        check_type(self.__timeout, float, 'bus', self.__main_bus.name, logger)
        if self.__timeout > 0.5:
            logger.warning(f'timeout {self.__timeout} for shareable '
                           f'{self.__main_bus.name} might be excessive.')
        self.__lock = threading.Lock()

    @property
    def lock(self):
        return self.__lock

    @property
    def timeout(self):
        """Returns the timeout for requesting access to lock."""
        return self.__timeout

    def can_use(self):
        """Tries to acquire the resource on behalf of the caller.

        This method should be called every time a user of the bus wants to
        perform an operation. If the result is ``False`` the user does not
        have exclusive use of the bus and the actions are not guaranteed.

        .. warning:: It is the responsibility of the user to call
            :py:meth:`~SharedBus.stop_using` as soon as possible after
            preforming the intended work with the bus if this method
            grants it access. Failing to do so will result in the bus
            being blocked by this user and prohibiting other users to
            access it.

        Returns
        -------
        bool
            ``True`` if managed to acquire the resource, ``False`` if
            not. It is the responsibility of the caller to decide what
            to do in case there is a ``False`` return including
            logging or Raising.
        """
        return self.__lock.acquire(timeout=self.__timeout)

    def stop_using(self):
        """Releases the resource."""
        self.__lock.release()

    def naked_read(self, reg):
        """Calls the main bus read without invoking the lock. This is
        intended for those users that plan to use a series of read operations
        and they do not want to lock and release the bus every time, as this
        adds some overhead. Since the original bus' ``read`` method is
        overridden (see below), any calls to ``read`` from a user will
        result in using the wrapped version defined in this class. Therefore
        in the scenario that the user wants to execute a series of quick
        reads the ``naked_read`` can be used as long as the user wraps the
        calls correctly for obtaining exclusive access::

            if bus.can_use():
                val1 = bus.naked_read(reg1)
                val2 = bus.naked_read(reg2)
                val3 = bus.naked_read(reg3)
                ...
                bus.stop_using()
            else:
                logger.warning('some warning')

        Parameters
        ----------
        reg: BaseRegister or subclass
            The register object that needs to be read. Keep in mind that
            the register object also contains a reference to the device
            in the ``device`` attribute and it is up to the subclass to
            determine the way the information must be processed before
            providing it to the caller.

        Returns
        -------
        int
            Typically it would return an ``int`` that will have to be
            handled by the caller.
        """
        return self.__main_bus.read(reg)

    def naked_write(self, reg, value):
        """Calls the main bus write without invoking the lock. This is
        intended for those users that plan to use a series of write operations
        and they do not want to lock and release the bus every time, as this
        adds some overhead. Since the original bus' ``write`` method is
        overridden (see below), any calls to ``write`` from a user will
        result in using the wrapped version defined in this class. Therefore
        in the scenario that the user wants to execute a series of quick
        writes the ``naked_write`` can be used as long as the user wraps the
        calls correctly for obtaining exclusive access::

            if bus.can_use():
                val1 = bus.naked_write(reg1, val1)
                val2 = bus.naked_write(reg2, val2)
                val3 = bus.naked_write(reg3, val3)
                ...
                bus.stop_using()
            else:
                logger.warning('some warning')

        Parameters
        ----------
        reg: BaseRegister or subclass
            The register object that needs to be read. Keep in mind that
            the register object also contains a reference to the device
            in the ``device`` attribute and it is up to the subclass to
            determine the way the information must be processed before
            providing it to the caller.

        value: int
            The value needed to the written to the device.
        """
        self.__main_bus.write(reg, value)

    def read(self, reg):
        """Overrides the main bus' :py:meth:`~roboglia.base.BaseBus.read`
        method and performs a **safe** read by wrapping the read call
        in a request to acquire the bus.

        If the method is not able to acquire the bus in time (times out)
        it will log an error and return ``None``.

        Parameters
        ----------
        reg: BaseRegister or subclass
            The register object that needs to be read. Keep in mind that
            the register object also contains a reference to the device
            in the ``device`` attribute and it is up to the subclass to
            determine the way the information must be processed before
            providing it to the caller.

        Returns
        -------
        int:
            The value read for this register or ``None`` is the call failed
            to secure with bus within the ``timeout``.

        """
        if self.can_use():
            value = self.__main_bus.read(reg)
            self.stop_using()
            return value
        # couldn't acquire
        logger.error(f'failed to acquire bus {self.__main_bus.name}')
        return None

    def write(self, reg, value):
        """Overrides the main bus' `~roboglia.base.BaseBus.write` method and
        performs a **safe** write by wrapping the main bus write call
        in a request to acquire the bus.

        If the method is not able to acquire the bus in time (times out)
        it will log an error.

        Parameters
        ----------
        reg: BaseRegister or subclass
            The register object that needs to be read. Keep in mind that
            the register object also contains a reference to the device
            in the ``device`` attribute and it is up to the subclass to
            determine the way the information must be processed before
            providing it to the caller.

        value: int
            The value to be written to the device.
        """
        if self.can_use():
            self.__main_bus.write(reg, value)
            self.stop_using()
        else:
            logger.error(f'failed to acquire bus {self.__main_bus.name}')

    def __repr__(self):
        """Invokes the main bus representation but changes the class name
        with the "Shared" class name to show a more accurate picture of the
        object."""
        ans = self.__main_bus.__repr__()
        ans = ans.replace(self.__main_bus.__class__.__name__,
                          self.__class__.__name__)
        return ans

    def __getattr__(self, name):
        """Forwards all unanswered calls to the main bus instance."""
        return getattr(self.__main_bus, name)


class SharedFileBus(SharedBus):
    """This is a :py:class:`FileBus` class that was wrapped for access
    to a shared resource.

    All :py:class:`FileBus` methods and attributes are accessible
    transparently but please be aware that the methods ``read`` and ``write``
    are now **safe**, wrapped around calls to :py:meth:`SharedBus.can_use`
    and :py:meth:`SharedBus.stop_using`. Additionally the two new access
    methods :py:meth:`~SharedBus.naked_read` and
    :py:meth:`~SharedBus.naked_write` are available.

    .. note:: You should always use a ``SharedFileBus`` class if you plan
        to use sync loops that run in separate threads and they will have
        access to the same bus.

    ``SharedFileBus`` inherits all the paramters from :py:class:`FileBus`
    as well as the ones from the meta-class :py:class:`SharedBus`. Please
    refer to these for a detail documentation of the parameters.
    """
    def __init__(self, **kwargs):
        super().__init__(FileBus, **kwargs)

    def __str__(self):
        return FileBus.__str__(self)
