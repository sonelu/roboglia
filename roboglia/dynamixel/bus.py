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

from dynamixel_sdk import PacketHandler, PortHandler
from serial import rs485

from ..base import BaseBus, SharedBus
from ..utils import check_type, check_options, check_not_empty

logger = logging.getLogger(__name__)


class DynamixelBus(BaseBus):
    """A communication bus that supports Dynamixel protocol.

    Uses ``dynamixel_sdk``.

    .. note:: The parameters listed bellow are only the specific ones
        introduced by the ``DynamixelBus`` class. Since this is a subclass
        of :py:class:`~roboglia.base.BaseBus` and the constructor will
        call the ``super()`` constructor, all the paramters supported by
        :py:class:`~roboglia.base.BaseBus` are
        also supported and checked when creating a ``DynamixelBus``. For
        instance the `name`, `robot` and `port` are validated.

    Parameters
    ----------
    baudrate: int
        Communication speed for the bus

    protocol: float
        Communication protocol for the bus; must be 1.0 or 2.0

    rs485: bool
        If ``True``, ``DynamixelBus`` will configure the serial port with
        RS485 support. This might be required for certain interfaces that
        need this mode in order to control the semi-duplex protocol (one
        wire) implemented by Dynamixel devices or if you genuinely use RS485
        Dynamixel devices.

    mock: bool
        Indicates to use mock bus for testing purposes; this will make use
        of the :py:class:`MockPacketHandler` to simulate the communication
        on a Dynamixel bus and allow to test the software in CI testing.

    Raises
    ------
        KeyError: if any of the required keys are missing
        ValueError: if any of the required data is incorrect
    """
    def __init__(self, baudrate=1000000, protocol=2.0, rs485=False,
                 mock=False, **kwargs):
        super().__init__(**kwargs)
        check_type(baudrate, int, 'bus', self.name, logger)
        check_not_empty(baudrate, 'baudrate', 'bus', self.name, logger)
        self.__baudrate = baudrate
        check_options(protocol, [1.0, 2.0], 'bus', self.name, logger)
        self.__protocol = protocol
        check_options(rs485, [True, False], 'bus', self.name, logger)
        self.__rs485 = rs485
        self.__port_handler = None
        self.__packet_handler = None
        check_options(mock, [True, False], 'bus', self.name, logger)
        self.__mock = mock

    @property
    def port_handler(self):
        """The Dynamixel port handler for this bus."""
        return self.__port_handler

    @property
    def packet_handler(self):
        """The Dynamixel packet handler for this bus."""
        return self.__packet_handler

    @property
    def protocol(self):
        """Protocol supported by the bus."""
        return self.__protocol

    @property
    def baudrate(self):
        """Bus baudrate."""
        return self.__baudrate

    @property
    def rs485(self):
        """If the bus uses rs485."""
        return self.__rs485

    def open(self):
        """Allocates the port_handler and the packet_handler. If the
        attribute ``mock`` was ``True`` when setting up the bus, then
        uses MockPacketHandler.
        """
        if self.__mock:
            self.__port_handler = 'MockBus'
            self.__packet_handler = MockPacketHandler(self.protocol,
                                                      self.robot)
        else:
            self.__port_handler = PortHandler(self.port)
            self.__port_handler.openPort()
            self.__port_handler.setBaudRate(self.baudrate)
            if self.rs485:
                self.__port_handler.ser.rs485_mode = rs485.RS485Settings()
                logger.info(f'bus {self.name} set in rs485 mode')
            self.__packet_handler = PacketHandler(self.__protocol)
        logger.info(f'bus {self.name} opened')

    def close(self):
        """Closes the actual physical bus. Calls the ``super().close()`` to
        check if there is ok to close the bus and no other objects are
        using it."""
        if self.is_open:
            if super().close():
                self.__packet_handler = None
                if not self.__mock:
                    self.__port_handler.closePort()
                self.__port_handler = None
                logger.info(f'bus {self.name} closed')

    @property
    def is_open(self):
        """Returns `True` or `False` if the bus is open.
        """
        return self.__port_handler is not None

    def ping(self, dxl_id):
        """Performs a Dynamixel ``ping`` of a device.

        Parameters
        ----------
        dxl_id: int
            The Dynamixel device number to be pinged.

        Returns
        -------
        bool
            ``True`` if the device responded, ``False`` otherwise.
        """
        if not self.is_open:
            logger.error('ping invoked with a bus not opened')
        else:
            _, cerr, derr = self.__packet_handler.ping(self.__port_handler,
                                                       dxl_id)
            if cerr == 0 and derr == 0:
                return True
            else:
                return False

    def scan(self, range=range(254)):
        """Scans the devices on the bus.

        Parameters
        ----------
        range: range
            the range of devices to be cheked if they
            exist on the bus. The method will call :py:method:`~ping`
            for each ID in the list. By default the list is [0, 253].

        Returns:
        list of int
            The list of IDs that have been successfully
            identified on the bus. If none is found the list will be
            empty.
        """
        if not self.is_open:
            logger.error('scan invoked with a bus not opened')
        else:
            return [dxl_id for dxl_id in range if self.ping(dxl_id)]

    def read(self, reg):
        """Depending on the size of the register calls the corresponding
        TxRx function from the packet handler.
        If the result is ok (communication error and dynamixel error are both
        0) then the obtained value is returned. Communication and data
        errors are logged and no exceptions are raised.

        Parameters
        ----------
        reg: BaseRegister or subclass
            The register to be read

        Returns
        -------
        int:
            The value read by calling the device.
        """
        if not self.is_open:
            logger.error(f'attempt to use closed bus {self.name}')
        else:
            dev = reg.device
            # select the function by the size of register
            if reg.size == 1:
                function = self.__packet_handler.read1ByteTxRx
            elif reg.size == 2:
                function = self.__packet_handler.read2ByteTxRx
            elif reg.size == 4:
                function = self.__packet_handler.read4ByteTxRx
            else:
                raise NotImplementedError

            # call the function
            try:
                res, cerr, derr = function(self.__port_handler,
                                           dev.dev_id, reg.address)
            except Exception as e:
                logger.error(f'Exception raised while reading bus {self.name}'
                             f' device {dev.name} register {reg.name}')
                logger.error(str(e))
                return None

            # success call - log DEBUG
            logger.debug(f'[readXByteTxRx] dev={dev.dev_id} '
                         f'reg={reg.address}: '
                         f'{res} (cerr={cerr}, derr={derr})')
            # process result
            if cerr != 0:
                # communication error
                err_desc = self.__packet_handler.getTxRxResult(cerr)
                logger.error(f'[bus {self.name}] device {dev.name}, '
                             f'register {reg.name}: {err_desc}')
                return None
            else:
                if derr != 0:
                    # device error
                    err_desc = self.__packet_handler.getRxPacketError(derr)
                    logger.warning(f'device {dev.name} responded with a '
                                   f'return error: {err_desc}')
                else:
                    return res

    def write(self, reg, value):
        """Depending on the size of the register calls the corresponding
        TxRx function from the packet handler.
        Communication and data errors are logged and no exceptions are
        raised.

        Paramters
        ---------
        reg: BaseRegister or subclass
            The register to write to

        value: int
            The value to write to the register. Please note that this is
            in the internal format of the register and it is the
            responsibility of the register class to provide conversion
            between the internal and external format if they are different.
        """
        if not self.is_open:
            logger.error(f'attempt to use closed bus {self.name}')
        else:
            dev = reg.device
            # select function by register size
            if reg.size == 1:
                function = self.__packet_handler.write1ByteTxRx
            elif reg.size == 2:
                function = self.__packet_handler.write2ByteTxRx
            elif reg.size == 4:
                function = self.__packet_handler.write4ByteTxRx
            else:
                raise NotImplementedError

            # execute the function
            try:
                cerr, derr = function(self.__port_handler, dev.dev_id,
                                      reg.address, value)
            except Exception as e:
                logger.error(f'Exception raised while writing bus {self.name}'
                             f' device {dev.name} register {reg.name}')
                logger.error(str(e))
                return None

            # success call - log DEBUG
            logger.debug(f'[writeXByteTxRx] dev={dev.dev_id} '
                         f'reg={reg.address}: '
                         f'{value} (cerr={cerr}, derr={derr})')
            # process result
            if cerr != 0:
                # communication error
                err_desc = self.__packet_handler.getTxRxResult(cerr)
                logger.error(f'[bus {self.name}] device {dev.name}, '
                             f'register {reg.name}: {err_desc}')
            else:
                if derr != 0:
                    # device error
                    err_desc = self.__packet_handler.getRxPacketError(derr)
                    logger.warning(f'device {dev.name} responded with a '
                                   f'return error: {err_desc}')


class SharedDynamixelBus(SharedBus):
    """A DynamixelBus that can be used in multithreaded environment.

    Includes the functionality of a :py:class:`DynamixelBus` in a
    :py:class:`SharedBus`. The :py:method:`~write` and :py:method:`~read`
    methods are wrapped around in :py:method:`~can_use` and
    :py:method:`~stop_using` to provide the exclusive access.

    In addition, two methods :py:method:`~naked_write` and
    :py:method:`~naked_read` are provided so that classes that want sequence
    of read / writes can do that more efficiently without accessing the
    lock every time. They simply invoke the *unsafe* methods
    :py:method:DynamixelBus.`write` and :py:method:DynamixelBus.`read` from
    the :py:class:`DynamixelBus` class.

    .. see also: :py:class:`SharedBus` class.

    .. warning::

        If you are using :py:method:`~naked_write` and :py:method:`~naked_read`
        you **must** ensure that you wrap them in :py:method:`~can_use` and
        :py:method:`~stop_using` in the calling code.

    """
    def __init__(self, **kwargs):
        super().__init__(DynamixelBus, **kwargs)


class MockPacketHandler():
    """A class used to simulate the Dynamixel communication without actually
    using a real bus or devices. Used for testing in the CI environment.
    The class includes deterministic behavior, for instance it will use the
    existing values of the device to mock a response, as well as well as
    stochastic behavior where with a certain probability we generate
    communication errors in order to be able to test how the code deals with
    these situations. Also, for read of registers that are read only the
    class will introduce small random numbers to the numbers already in the
    registers so to simulate values that change over time (ex. current
    position).

    Parameters
    ----------
    protocol: float
        Dynamixel protocol to use. Should be 1.0 or 2.0

    robot: BaseRobot
        The robot for in order to *bootstrap* information.

    err: float
        A value that is used to generate random communication errors so that
        we can test the parts of the code that deal with this.
    """
    def __init__(self, protocol, robot, err=0.1):
        self.__robot = robot
        self.__err = err
        self.__protocol = protocol
        self.__sync_data_length = None

    def getProtocolVersion(self):
        """Returns the Dynamixel protocol used."""
        return self.__protocol

    def getTxRxResult(self, err):
        """Used to get a string representation of a communication error.
        Invokes the official function from ``PacketHandler`` in
        ``dynamixel_sdk``.

        Parameters
        ----------
        err: int
            An error code as reported by the communication medium

        Returns
        -------
        str:
            A string representation of this error.
        """
        ph = PacketHandler(self.__protocol)
        return ph.getTxRxResult(err)

    def getRxPacketError(self, err):
        """Used to get a string representation of a device response error.
        Invokes the official function from ``PacketHandler`` in
        ``dynamixel_sdk``.

        Parameters
        ----------
        err: int
            An error code as reported by the Dynamixel device

        Returns
        -------
        str:
            A string representation of this error.
        """
        ph = PacketHandler(self.__protocol)
        return ph.getRxPacketError(err)

    def __common_writeTxRx(self, ph, dev_id, address, value):
        if random.random() < self.__err:
            return -3001, 0
        else:
            # device = self.__robot.device_by_id(dev_id)
            # reg = device.register_by_address(address)
            # reg.int_value = value
            if random.random() < self.__err:
                return 0, 4         # overheat
            else:
                return 0, 0

    def write1ByteTxRx(self, ph, dev_id, address, value):
        """Mocks a write of 1 byte to a device. In ``err`` percentage
        time it will raise a communication error. From the remaning cases
        again an ``err`` percentage will be raised with device error
        (overheat).

        The paramters are copied from the ``PacketHadler`` in
        ``dynamixel_sdk``.

        You would rarely need to use this.
        """
        return self.__common_writeTxRx(ph, dev_id, address, value)

    def write2ByteTxRx(self, ph, dev_id, address, value):
        """Same as :py:meth:`write1ByteTxRx` but for 2 Bytes registers."""
        return self.__common_writeTxRx(ph, dev_id, address, value)

    def write4ByteTxRx(self, ph, dev_id, address, value):
        """Same as :py:meth:`write1ByteTxRx` but for 4 Bytes registers."""
        return self.__common_writeTxRx(ph, dev_id, address, value)

    def __common_readTxRx(self, ph, dev_id, address):
        if random.random() < self.__err:
            return 0, -3001, 0
        else:
            device = self.__robot.device_by_id(dev_id)
            reg = device.register_by_address(address)
            if random.random() < self.__err:
                return reg.int_value, 0, 4      # overheat
            else:
                return reg.int_value, 0, 0

    def read1ByteTxRx(self, ph, dev_id, address):
        """Same as :py:meth:`write1ByteTxRx` but for reading 1 Bytes
        registers."""
        return self.__common_readTxRx(ph, dev_id, address)

    def read2ByteTxRx(self, ph, dev_id, address):
        """Same as :py:meth:`write1ByteTxRx` but for reading 2 Bytes
        registers."""
        return self.__common_readTxRx(ph, dev_id, address)

    def read4ByteTxRx(self, ph, dev_id, address):
        """Same as :py:meth:`write1ByteTxRx` but for reading 4 Bytes
        registers."""
        return self.__common_readTxRx(ph, dev_id, address)

    def syncWriteTxOnly(self, port, start_address, data_length,
                        param, param_length):
        """Mocks a SyncWrite transmit package. We return randomly an error
        or success."""
        if random.random() < self.__err:
            return -3001
        else:
            return 0

    def syncReadTx(self, port, start_address, data_length, param,
                   param_length):
        """Mocks a SyncWrite transmit package. We return randomly an error
        or success."""
        if random.random() < self.__err:
            return -3001
        else:
            self.__sync_data_length = data_length
            self.__param = param
            self.__start_address = start_address
            self.__index = 0
            self.__mode = 'sync'
            return 0

    def readRx(self, port, dxl_id, length):
        """Mocks a read package received. Used by SyncRead and BulkRead.
        It will attempt to produce a response based on the data already
        exiting in the registers. If the register is a read-only one, we
        will add a random value between (-10, 10) to the exiting value and
        then trim it to the ``min`` and ``max`` limits of the register. When
        passing back the data, for registers that are more than 1 byte a
        *low endian* conversion is executed (see
        :py:meth:`DynamixelRegister.register_low_endian).
        """
        if random.random() < self.__err:
            return 0, -3001, 0

        # we're not going to check the device and register as we
        # expect both to be available since we checked them when
        # we setup the sync
        else:
            if self.__mode == 'sync':
                device = self.__robot.device_by_id(self.__param[self.__index])
                register = device.register_by_address(self.__start_address)

            elif self.__mode == 'bulk':
                idx = self.__index * 5
                dev_id = self.__param[idx]
                device = self.__robot.device_by_id(dev_id)
                assert dev_id == dxl_id
                address = self.__param[idx + 1] + self.__param[idx + 2] * 256
                register = device.register_by_address(address)
                assert register.size == length

            if register.access == 'R':
                value = register.int_value
            else:
                value = register.int_value + random.randint(-10, 10)
                value = max(register.min, min(register.max, value))
            self.__index += 1
            return device.register_low_endian(value, register.size), 0, 0

    def bulkWriteTxOnly(self, port, param, param_length):
        """Simulate a BulkWrite transmit package. We return randomly an error
        or success."""
        if random.random() < self.__err:
            return -3001
        else:
            return 0

    def bulkReadTx(self, port, param, param_length):
        """"Simulate a BulkWrite transmit of response request package. We
        return randomly an error or success."""
        if random.random() < self.__err:
            return -3001
        else:
            # self.__sync_data_length = data_length
            self.__param = param
            # self.__start_address = start_address
            self.__index = 0
            self.__mode = 'bulk'
            return 0

    def ping(self, ph, dxl_id):
        """Simulates a ``ping`` on the Dynamixel bus."""
        for device in self.__robot.devices.values():
            if device.dev_id == dxl_id:
                return device.model_number, 0, 0
        return 0, -3001, 0
