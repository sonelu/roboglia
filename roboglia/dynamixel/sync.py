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
from dynamixel_sdk import GroupSyncWrite, GroupSyncRead
#    GroupBulkWrite, GroupBulkRead

from ..base import BaseSync

logger = logging.getLogger(__name__)


class DynamixelSyncLoop(BaseSync):
    """Class with common processing between SyncRead and SyncWrite.

    Deals with the initialization of the list of devices and the registers
    and checks if the devices are all on the same bus while the registers
    are continuous.
    """
    def process_registers(self):
        """Calls the inherited method and then checks that the regosters
        are in order and without gaps.
        """
        super().process_registers()
        if len(self.registers) == 0:
            mess = f'You have to specify at least one register for ' + \
                   f'sync loop {self.name}.'
            logger.critical(mess)
            raise ValueError(mess)
        # check that registers are in sequence and no gaps
        device = self.devices[0]         # pick first device
        reg_name = self.registers[0]     # pick first register
        register = getattr(device, reg_name)
        start_address = register.address
        all_length = register.size
        # if more than one register
        if len(self.registers) > 1:
            for reg_name in self.registers[1:]:
                address = getattr(device, reg_name).address
                length = getattr(device, reg_name).size
                if address != start_address + all_length:
                    mess = f'Registers for sync loop {self.name} must be ' + \
                           f'in order without gaps.'
                    logger.critical(mess)
                    raise ValueError(mess)
                all_length += length
        self.__start_address = start_address
        self.__all_length = all_length

    @property
    def start_address(self):
        """Start of address."""
        return self.__start_address

    @property
    def all_length(self):
        """The length of the address sequence."""
        return self.__all_length


class DynamixelSyncReadLoop(DynamixelSyncLoop):
    """Implements SyncRead as specified in the frequency parameter.

    The devices are provided in the `group` parameter and the registers
    in the `registers` as a list of register names. The registers need to
    be sequential and no gaps should exist.
    It will update the `int_value` of each register in every device with
    the result of the call.
    Will raise exceptions if the SyncRead cannot be setup or fails to
    execute.
    Only works with Protocol 2.0.
    """
    def __init__(self, init_dict):
        super().__init__(init_dict)
        if self.bus.protocol != 2.0:
            mess = f'SyncRead only supported for Dynamixel Protocol 2.0.'
            logger.critical(mess)
            raise ValueError(mess)

    def setup(self):
        """Prepares to start the loop."""
        self.gsr = GroupSyncRead(self.bus.port_handler,
                                 self.bus.packet_handler,
                                 self.start_address,
                                 self.all_length)
        for device in self.devices:
            result = self.gsr.addParam(device.dev_id)
            if result is not True:
                logger.error(f'failed to setup SyncRead for loop {self.name} '
                             f'for device {device.name}')

    def atomic(self):
        """Executes a SyncRead."""
        # execute read
        if not self.bus.can_use():
            logger.error(f'sync {self.name} '
                         f'failed to aquire buss {self.name}')
        else:
            result = self.gsr.txRxPacket()
            self.bus.stop_using()       # !! as soon as possible
            if result != 0:
                error = self.bus.packetHandler.getTxRxResult(result)
                logger.error(f'SyncRead {self.name}, cerr={error}')
            else:
                # retrieve data
                for device in self.devices:
                    for reg_name in self.registers:
                        register = getattr(device, reg_name)
                    result = self.gsr.isAvailable(
                        device.dev_id, register.address, register.size)
                    if result != 0:
                        error = self.bus.packet_handler.getTxRxResult(result)
                        logger.error(f'failed to retreive data in '
                                     f'SyncRead {self.name} for '
                                     f'device {device.name} and register '
                                     f'{register.name}; cerr={error}')
                    else:
                        register.int_value = self.gsr.getData(
                            device.dev_id, register.address, register.size)


class DynamixelSyncWriteLoop(DynamixelSyncLoop):
    """Implements SyncWrite as specified in the frequency parameter.

    The devices are provided in the `group` parameter and the registers
    in the `registers` as a list of register names. The registers need to
    be sequential and no gaps should exist.
    It will update from `int_value` of each register for every device.
    Will raise exceptions if the SyncRead cannot be setup or fails to
    execute.
    """
    def setup(self):
        """This allocates the ``GroupSyncWrite``. It needs to be here and
        not in the constructor as this is part of the wrapped execution
        that is produced by :py:class:`BaseThread` class.
        """
        self.gsw = GroupSyncWrite(self.bus.port_handler,
                                  self.bus.packet_handler,
                                  self.start_address,
                                  self.all_length)

    def atomic(self):
        """Executes a SyncWrite."""
        # prepares the call
        for device in self.devices:
            # prepare the buffer data
            data = bytes()
            for reg_name in self.registers:
                register = getattr(device, reg_name)
                data += register.int_value.to_bytes(register.size,
                                                    byteorder='little')
            result = self.gsw.addParam(device.dev_id, data)
            if not result:
                mess = f'failed to setup SyncWrite for loop {self.name} ' + \
                       f'for device {device.name}'
                logger.error(mess)
        # execute write
        if self.bus.can_use():
            result = self.gsw.txPacket()
            self.bus.stop_using()       # !! as soon as possible
            error = self.gsw.ph.getTxRxResult(result)
            logger.debug(f'[sync write {self.name}] data: {data.hex()}, '
                         f'result: {error}')
            if result != 0:
                logger.error(f'failed to execte SyncWrite {self.name}: '
                             f'cerr={error}')
        else:
            logger.error(f'sync {self.name} '
                         f'failed to aquire buss {self.name}')
        # cleanup
        self.gsw.clearParam()


class DynamixelBulkReadLoop(BaseSync):

    def __init__(self, init_dict):
        pass


class DynamixelBulkWriteLoop(BaseSync):

    def __init__(self, init_dict):
        pass
