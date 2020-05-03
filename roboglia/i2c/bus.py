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

from ..base.bus import BaseBus
from smbus2 import SMBus


class I2CBus(BaseBus):

    def __init__(self, init_dict):
        super().__init__(init_dict)
        self.i2cbus = None

    def open(self):
        self.i2cbus = SMBus(self.port)

    def close(self):
        self.i2cbus.close()
        self.i2cbus = None

    def isOpen(self):
        """Returns `True` or `False` if the bus is open. Must be overriden
        by the subclass.
        """
        return self.i2cbus is not None

    def read(self, dev, reg):
        """Depending on the size of the register is calls the corresponding
        function from the smbus.
        If the result is ok (communication error and dynamixel error are both
        0) then the obtained value is returned. Otherwise it will throw a
        ConnectionError. Callers shoud intercept the exception if they
        want to control it.
        """
        if reg.size == 1:
            function = self.i2cbus.read_byte_data
        elif reg.size == 2:
            function = self.i2cbus.read_word_data
        else:
            mess = f'unexpected size {reg.size} ' + \
                   f'for register {reg.name} ' + \
                   f'of device {dev.name}'
            raise ValueError(mess)
        return function(dev.dev_id, reg.address)

    def write(self, dev, reg, value):
        """Depending on the size of the register is calls the corresponding
        TxRx function from the packet handler.
        If the result is not ok (communication error or dynamixel error are not
        both 0) it will throw a ConnectionError. Callers shoud intercept the
        exception if they want to control it.
        """
        if reg.size == 1:
            function = self.i2cbus.write_byte_data
        elif reg.size == 2:
            function = self.i2cbus.write_word_data
        else:
            mess = f'unexpected size {reg.size} ' + \
                   f'for register {reg.name} ' + \
                   f'of device {dev.name}'
            raise ValueError(mess)
        function(dev.dev_id, reg.address, value)
