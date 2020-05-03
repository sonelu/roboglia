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
from ..base import BaseBus
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
        self._baudrate = init_dict['baudrate']
        check_type(self._baudrate, int, 'bus', self.name, logger)
        check_key('protocol', init_dict, 'bus', self.name, logger)
        self._protocol = init_dict['protocol']
        check_options(self._protocol, [1.0, 2.0], 'bus', self.name, logger)
        self._rs485 = init_dict.get('rs485', False)
        check_options(self._rs485, [True, False], 'bus', self.name, logger)
        self._port_handler = None
        self._packet_handler = None

    def open(self):
        """Opens the actual physical bus. Must be overriden by the
        subclass.
        """
        self._port_handler = dynamixel_sdk.PortHandler(self._port)
        self._port_handler.openPort()
        self._port_handler.setBaudRate(self._baudrate)
        if self._rs485:
            self._port_handler.ser.rs485_mode = rs485.RS485Settings()
        self._packet_handler = dynamixel_sdk.PacketHandler(self._protocol)

    def close(self):
        """Closes the actual physical bus. Must be overriden by the
        subclass.
        """
        self._packet_handler = None
        self._port_handler.closePort()
        self._port_handler = None

    def isOpen(self):
        """Returns `True` or `False` if the bus is open. Must be overriden
        by the subclass.
        """
        return self._port_handler is not None

    def ping(self, dxl_id):
        _, cerr, derr = self._packet_handler.ping(self._port_handler, dxl_id)
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
        if reg.size == 1:
            function = self._packet_handler.read1ByteTxRx
        elif reg.size == 2:
            function = self._packet_handler.read2ByteTxRx
        elif reg.size == 4:
            function = self._packet_handler.read4ByteTxRx
        else:
            raise ValueError(f'unexpected size {reg.size} for register '
                             f'{reg.name} of device {dev.name}')
        res, cerr, derr = function(self._port_handler, dev.dev_id, reg.address)
        if cerr == 0:
            if derr != 0:
                logger.warning(f'device {dev.name} responded with a return '
                               f'error: {derr}')
            return res
        else:
            logger.error(f'failed to communicate wtih bus {self.name}, '
                         f'cerr={cerr}, derr={derr}')
            return None

    def write(self, dev, reg, value):
        """Depending on the size of the register is calls the corresponding
        TxRx function from the packet handler.
        If the result is not ok (communication error or dynamixel error are not
        both 0) it will throw a ConnectionError. Callers shoud intercept the
        exception if they want to control it.
        """
        if reg.size == 1:
            function = self._packet_handler.write1ByteTxRx
        elif reg.size == 2:
            function = self._packet_handler.write2ByteTxRx
        elif reg.size == 4:
            function = self._packet_handler.write4ByteTxRx
        else:
            raise ValueError(f'unexpected size {reg.size} for register '
                             f'{reg.name} of device {dev.name}')
        cerr, derr = function(self._port_handler, dev.dev_id,
                              reg.address, value)
        if cerr != 0:
            logger.error(f'failed to communicte wtih bus {self.name}, '
                         f'cerr={cerr}, derr={derr}')
        if cerr == 0 and derr != 0:
            mess = f'device {dev.name} responded with a return error: {derr}'
            logger.warning(mess)
