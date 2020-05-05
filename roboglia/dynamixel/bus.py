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

import dynamixel_sdk
from serial import rs485
import logging
from ..base import BaseBus, ShareableBus
from ..utils import check_key, check_type, check_options

logger = logging.getLogger(__name__)


class DynamixelBus(BaseBus):
    """A communication bus that supports Dynamixel protocol.

    Uses ``dynamixel_sdk``.

    Args:
        init_dict (dict): The dictionary used to initialize the bus.

    In addition to the keys that are required by the :py:class:BaseBus the
    following key must by provided:

    - ``baudrate``: communication speed for the bus (int)
    - ``protocol``: communication protocol for the bus; must be 1.0 or 2.0
    - ``rs485``: activates RS485 protocol on the serial bus (bool)

    Raises:
        KeyError: if any of the required keys are missing
        ValueError: if any of the required data is incorrect
    """
    def __init__(self, init_dict):
        super().__init__(init_dict)
        check_key('baudrate', init_dict, 'bus', self.name, logger)
        self.__baudrate = init_dict['baudrate']
        check_type(self.__baudrate, int, 'bus', self.name, logger)
        check_key('protocol', init_dict, 'bus', self.name, logger)
        self.__protocol = init_dict['protocol']
        check_options(self.__protocol, [1.0, 2.0], 'bus', self.name, logger)
        self.__rs485 = init_dict.get('rs485', False)
        check_options(self.__rs485, [True, False], 'bus', self.name, logger)
        self.__port_handler = None
        self.__packet_handler = None

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

    def open(self):
        """Opens the actual physical bus. Must be overriden by the
        subclass.
        """
        self.__port_handler = dynamixel_sdk.PortHandler(self.port)
        self.__port_handler.openPort()
        self.__port_handler.setBaudRate(self.__baudrate)
        if self.__rs485:
            self.__port_handler.ser.rs485_mode = rs485.RS485Settings()
            logger.info(f'bus {self.name} set in rs485 mode')
        self.__packet_handler = dynamixel_sdk.PacketHandler(self.__protocol)

    def close(self):
        """Closes the actual physical bus. Must be overriden by the
        subclass.
        """
        if self.is_open:
            self.__packet_handler = None
            self.__port_handler.closePort()
            self.__port_handler = None

    @property
    def is_open(self):
        """Returns `True` or `False` if the bus is open. Must be overriden
        by the subclass.
        """
        return self.__port_handler is not None

    def ping(self, dxl_id):
        _, cerr, derr = self.__packet_handler.ping(self.__port_handler, dxl_id)
        if cerr == 0 and derr == 0:
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
        if not self.is_open:
            logger.error(f'attempt to use closed bus {self.name}')
        else:
            # select the function by the size of register
            if reg.size == 1:
                function = self.__packet_handler.read1ByteTxRx
            elif reg.size == 2:
                function = self.__packet_handler.read2ByteTxRx
            elif reg.size == 4:
                function = self.__packet_handler.read4ByteTxRx
            else:
                raise ValueError(f'unexpected size {reg.size} for register '
                                 f'{reg.name} of device {dev.name}')
            # call the function
            res, cerr, derr = function(self.__port_handler,
                                       dev.dev_id, reg.address)
            logger.debug(f'[readXByteTxRx] dev={dev.dev_id} '
                         f'reg={reg.address}: '
                         f'{res} (cerr={cerr}, derr={derr})')
            # process result
            if cerr != 0:
                # communication error
                err_descr = self.__packet_handler.getTxRxResult(cerr)
                logger.error(f'[bus {self.name}] device {dev.name}, '
                             f'register {reg.name}: {err_descr}')
                return None
            else:
                if derr != 0:
                    # device error
                    err_descr = self.__packet_handler.getRxPacketError(derr)
                    logger.warning(f'device {dev.name} responded with a '
                                   f'return error: {err_descr}')
                else:
                    return res

    def write(self, dev, reg, value):
        """Depending on the size of the register is calls the corresponding
        TxRx function from the packet handler.
        If the result is not ok (communication error or dynamixel error are not
        both 0) it will throw a ConnectionError. Callers shoud intercept the
        exception if they want to control it.
        """
        if not self.is_open:
            logger.error(f'attempt to use closed bus {self.name}')
        else:
            # select function by register size
            if reg.size == 1:
                function = self.__packet_handler.write1ByteTxRx
            elif reg.size == 2:
                function = self.__packet_handler.write2ByteTxRx
            elif reg.size == 4:
                function = self.__packet_handler.write4ByteTxRx
            else:
                raise ValueError(f'unexpected size {reg.size} for register '
                                 f'{reg.name} of device {dev.name}')
            # execute the function
            cerr, derr = function(self.__port_handler, dev.dev_id,
                                  reg.address, value)
            logger.debug(f'[writeXByteTxRx] dev={dev.dev_id} '
                         f'reg={reg.address}: '
                         f'{value} (cerr={cerr}, derr={derr})')
            # process result
            if cerr != 0:
                # communication error
                err_descr = self.__packet_handler.getTxRxResult(cerr)
                logger.error(f'[bus {self.name}] device {dev.name}, '
                             f'register {reg.name}: {err_descr}')
            else:
                if derr != 0:
                    # device error
                    err_descr = self.__packet_handler.getRxPacketError(derr)
                    logger.warning(f'device {dev.name} responded with a '
                                   f'return error: {err_descr}')


class ShareableDynamixelBus(DynamixelBus, ShareableBus):
    """A DynamixelBus that can be used in multithreaded environment.

    Includes the functionality of a :py:class:`ShareableBus` in a
    :py:class:`DynamixelBus`. The :py:method:`write` and :py:method:`read`
    methods are wrapped around in :py:method:`can_use` and
    :py:method:`stop_using` to provide the exclusive access.

    In addition, two methods :py:method:`naked_write` and
    :py:method:`naked_read` are provided so that classes that want sequence
    of read / writes can do that more efficiently without accessing the
    lock every time. They simply invoke the *unsafe* methods
    :py:method:Filebus.`write` and :py:method:Filebus.`read` from the
    :py:class:`DynamixelBus` class.

    .. warning::

        If you are using :py:method:`naked_write` and :py:method:`naked_read`
        you **must** ensure that you wrap them in :py:method:`can_use` and
        :py:method:`stop_using` in the calling code.

    """
    def __init__(self, init_dict):
        DynamixelBus.__init__(self, init_dict)
        ShareableBus.__init__(self, init_dict)

    def write(self, dev, reg, value):
        """Write to file in a sharead environment.
        If the method fails to aquire the lock it will log as an error
        but will not raise an Exception.
        """
        if self.can_use():
            super().write(dev, reg, value)
            self.stop_using()
        else:
            logger.error(f'failed to aquire bus {self.name}')

    def naked_write(self, dev, reg, value):
        """Provided for efficient sequence write.
        Simply calls the :py:method:DynamixelBus.`write` method.
        """
        super().write(dev, reg, value)

    def read(self, dev, reg):
        """Read from file in a sharead environment.
        If the method fails to aquire the lock it will log as an error
        but will not raise an Exception. Will return None in this case.

        Returns:
            (int) the value from file or None is failing to read or
            aquire the lock.

        """
        if self.can_use():
            value = super().read(dev, reg)
            self.stop_using()
            return value
        else:
            logger.error(f'failed to aquire buss {self.name}')
            return None

    def naked_read(self, dev, reg):
        """Provided for efficient sequence read.
        Simply calls the :py:method:DynamixelBus.`read` method.
        """
        return super().read(dev, reg)
