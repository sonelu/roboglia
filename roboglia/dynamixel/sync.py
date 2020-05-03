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

from ..base import BaseLoop

logger = logging.getLogger(__name__)


class DynamixelSyncLoop(BaseLoop):
    """Class with common processing between SyncRead and SyncWrite.

    Deals with the initialization of the list of devices and the registers
    and checks if the devices are all on the same bus while the registers
    are continuous.
    """
    def __init__(self, init_dict):
        super().__init__(init_dict)
        self.devices = list(init_dict['group'])
        # check that all devices are on the same bus
        self.bus = self.process_devices()
        self.registers = init_dict['registers']
        self.start_address, self.all_length = self.process_registers()

    def process_devices(self):
        """Processes the provided devices.

        The devices are exected as a set in the `init_dict`. This is
        normally performed by the robot class when reading the robot
        definition by replacing the name of the group with the actual
        content of the group.
        This method checks that all devices are assigned to the same bus
        otherwise raises an exception. It returns the single instance of the
        bus that manages all devices.
        """
        buses = set([device.bus for device in self.devices])
        if len(buses) > 1:
            mess = f'Devices used for SyncLoop {self.name} should be ' + \
                   f'connected to a single bus.'
            logger.critical(mess)
            raise ValueError(mess)
        return buses.pop()      # there must be only one!

    def process_registers(self):
        """Processes the provided registers.

        The registers are provided as a list of names and they need to be in
        the correct order while not having any gaps between them.
        """
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
        return start_address, all_length


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
        self.group_sync_read = GroupSyncRead(self.bus.port_handler,
                                             self.bus.packet_handler,
                                             self.start_address,
                                             self.all_length)
        for device in self.devices:
            result = self.group_sync_read.addParam(device.dev_id)
            if result is not True:
                mess = f'failed to setup SyncRead for loop {self.name} ' + \
                       f'for device {device.name}'
                logger.critical(mess)
                raise RuntimeError(mess)

    def atomic(self):
        """Executes a SyncRead."""
        # execute read
        result = self.group_sync_read.txRxPacket()
        if result != 0:
            mess = f'failed to execte SyncRead {self.name}, cerr={result}'
            logger.critical(mess)
            raise ConnectionError(mess)
        # retrieve data
        for device in self.devices:
            for reg_name in self.registers:
                register = getattr(device, reg_name)
            grs = self.group_sync_read      # for line length!
            result = grs.isAvailable(device.dev_id,
                                     register.address,
                                     register.size)
            if result != 0:
                mess = f'failed to retreive data in SyncRead {self.name} ' + \
                       f'for device {device.name} and register ' + \
                       f'{register.name}; cerr={result}'
                logger.critical(mess)
                raise RuntimeError(mess)
            else:
                gsr = self.group_sync_read      # line length!
                register.int_value = gsr.getData(device.dev_id,
                                                 register.address,
                                                 register.size)


class DynamixelSyncWriteLoop(DynamixelSyncLoop):
    """Implements SyncWrite as specified in the frequency parameter.

    The devices are provided in the `group` parameter and the registers
    in the `registers` as a list of register names. The registers need to
    be sequential and no gaps should exist.
    It will update from `int_value` of each register for every device.
    Will raise exceptions if the SyncRead cannot be setup or fails to
    execute.
    """
    def __init__(self, init_dict):
        super().__init__(init_dict)
        self.group_sync_write = GroupSyncWrite(self.bus.port_handler,
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
            result = self.group_sync_write.addParam(device.dev_id, data)
            if not result:
                mess = f'failed to setup SyncWrite for loop {self.name} ' + \
                       f'for device {device.name}'
                logger.critical(mess)
                raise RuntimeError(mess)
        # execute write
        result = self.group_sync_write.txPacket()
        if result != 0:
            mess = f'failed to execte SyncWrite {self.name}, cerr={result}'
            logging.critical(mess)
            raise ConnectionError(mess)
        # cleanup
        self.group_sync_write.clearParam()


class DynamixelBulkReadLoop(BaseLoop):

    def __init__(self, init_dict):
        pass


class DynamixelBulkWriteLoop(BaseLoop):

    def __init__(self, init_dict):
        pass
