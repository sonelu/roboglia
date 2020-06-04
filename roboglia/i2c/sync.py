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

from ..base import BaseSync

logger = logging.getLogger(__name__)


class I2CWriteLoop(BaseSync):
    """Implements a write loop that is leveraging the ability to write a
    range of registers in one go.

    The devices are provided in the `group` parameter and the registers
    in the `registers` as a list of register names.
    It will update from `int_value` of each register for every device.
    Will log errors and not raise any exceptions.
    """
    def setup(self):
        """ Determines the start address and lengths for each bulk write.
        Previously the constructor checked that all registers are
        available in all devices.
        """
        self.start_address, self.length = self.get_register_range()

    def atomic(self):
        """Executes a SyncWrite."""
        for device in self.devices:
            # prepare data
            data = [0] * self.length
            for reg_name in self.register_names:
                register = getattr(device, reg_name)
                pos = register.address - self.start_address
                if register.size == 1:
                    data[pos] = register.int_value
                elif register.size == 2:
                    data[pos] = register.int_value % 256
                    data[pos + 1] = register.int_value // 256
                else:
                    raise NotImplementedError

            # write
            # I2CSharedBus does to handling of exceptions
            self.bus.write_block(device,
                                 self.start_address,
                                 data)
            logger.debug(f'{self.name} written block data {data}')


class I2CReadLoop(BaseSync):
    """Implements a read loop that is leveraging the ability to read a
    range of registers in one go.

    The devices are provided in the `group` parameter and the registers
    in the `registers` as a list of register names.
    It will update the `int_value` of each register for every device.
    Will log errors and not raise any exceptions.
    """
    def setup(self):
        """ Determines the start address and lengths for each bulk write.
        Previously the constructor checked that all registers are
        available in all devices.
        """
        self.start_address, self.length = self.get_register_range()

    def atomic(self):
        """Executes a SyncRead."""
        for device in self.devices:
            # read one device
            # I2CSharedBus does to handling of exceptions
            data = self.bus.read_block(device,
                                       self.start_address,
                                       self.length)
            logger.debug(f'{self.name} read block data {data}')
            if data is not None:
                for reg_name in self.register_names:
                    register = getattr(device, reg_name)
                    pos = register.address - self.start_address
                    if register.size == 1:
                        register.int_value = data[pos]
                    elif register.size == 2:
                        register.int_value = data[pos] + data[pos + 1] * 256
                    else:
                        raise NotImplementedError
