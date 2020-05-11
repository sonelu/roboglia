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
from dynamixel_sdk import GroupBulkWrite, GroupBulkRead

from ..base import BaseSync

logger = logging.getLogger(__name__)


class DynamixelSyncWriteLoop(BaseSync):
    """Implements SyncWrite as specified in the frequency parameter.

    The devices are provided in the `group` parameter and the registers
    in the `registers` as a list of register names.
    We will trigger as many SyncWrite packets as registers as Dynamixel
    does not support multiple registers in one go and you cannot include
    the same device twice in a SyncWrite.
    It will update from `int_value` of each register for every device.
    Will raise exceptions if the SyncWrite cannot be setup or fails to
    execute.
    """
    def setup(self):
        """This allocates the ``GroupSyncWrite``. It needs to be here and
        not in the constructor as this is part of the wrapped execution
        that is produced by :py:class:`BaseThread` class.
        """
        # determines the addresses and lengths for each SyncWrite
        # allocates the GroupSyncWrite objects for each one
        self.gsws = []
        for reg_name in self.registers:
            register = getattr(self.devices[0], reg_name)
            self.gsws.append(GroupSyncWrite(self.bus.port_handler,
                                            self.bus.packet_handler,
                                            register.address,
                                            register.size))

    def atomic(self):
        """Executes a SyncWrite."""
        for index, reg_name in enumerate(self.registers):
            sync_write = self.gsws[index]
            # add params to sync write
            for device in self.devices:
                register = getattr(device, reg_name)
                result = sync_write.addParam(
                    device.dev_id,
                    device.register_low_endian(register.int_value,
                                               register.size))
                if not result:
                    logger.error(f'failed to setup SyncWrite for loop '
                                 f'{self.name} for device {device.name}')
            # execute write
            if self.bus.can_use():
                result = sync_write.txPacket()
                self.bus.stop_using()       # !! as soon as possible
                error = sync_write.ph.getTxRxResult(result)
                logger.debug(f'[sync write {self.name}] for register '
                             f'{reg_name}, result: {error}')
                if result != 0:
                    logger.error(f'failed to execte SyncWrite {self.name}: '
                                 f'cerr={error}')
            else:
                logger.error(f'sync {self.name} '
                             f'failed to aquire buss {self.name}')
            # cleanup
            sync_write.clearParam()


class DynamixelSyncReadLoop(BaseSync):
    """Implements SyncRead as specified in the frequency parameter.

    The devices are provided in the `group` parameter and the registers
    in the `registers` as a list of register names.
    We will trigger as many SyncRead packets as registers as Dynamixel
    does not support multiple registers in one go and you cannot include
    the same device twice in a SyncRead.
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
        self.gsrs = []
        for reg_name in self.registers:
            register = getattr(self.devices[0], reg_name)
            gsr = GroupSyncRead(self.bus.port_handler,
                                self.bus.packet_handler,
                                register.address,
                                register.size)
            for device in self.devices:
                result = gsr.addParam(device.dev_id)
                if result is not True:
                    logger.error(f'failed to setup SyncRead for loop '
                                 f'{self.name} for device {device.name}')
            self.gsrs.append(gsr)

    def atomic(self):
        """Executes a SyncRead."""
        for index, reg_name in enumerate(self.registers):
            gsr = self.gsrs[index]
            # aquire the bus
            if not self.bus.can_use():
                logger.error(f'sync {self.name} '
                             f'failed to aquire buss {self.name}')
            # execute read
            result = gsr.txRxPacket()
            self.bus.stop_using()       # !! as soon as possible
            if result != 0:
                error = self.bus.packet_handler.getTxRxResult(result)
                logger.error(f'SyncRead {self.name}, cerr={error}')
                continue
            # retrieve data
            for device in self.devices:
                register = getattr(device, reg_name)
                if not gsr.isAvailable(device.dev_id, register.address,
                                       register.size):
                    logger.error(f'failed to retreve data in SyncRead '
                                 f'{self.name} for device {device.name} '
                                 f'and register {register.name}')
                else:
                    register.int_value = gsr.getData(
                        device.dev_id, register.address, register.size)


class DynamixelBulkWriteLoop(BaseSync):
    """Implements BulkWrite as specified in the frequency parameter.

    The devices are provided in the `group` parameter and the registers
    in the `registers` as a list of register names. The registers do not need
    tovbe sequential.
    We will trigger as many  BulkWrite packets as registers as Dynamixel
    does not support multiple registers in one go and you cannot include
    the same device twice in a SyncRead.
    It will update from `int_value` of each register for every device.
    Will raise exceptions if the BulkWrite cannot be setup or fails to
    execute.
    Only works with Protocol 2.0.
    """
    def __init__(self, init_dict):
        super().__init__(init_dict)
        if self.bus.protocol != 2.0:
            mess = f'BulkWrite only supported for Dynamixel Protocol 2.0.'
            logger.critical(mess)
            raise ValueError(mess)

    def setup(self):
        """This allocates the ``GroupBulkWrite``. It needs to be here and
        not in the constructor as this is part of the wrapped execution
        that is produced by :py:class:`BaseThread` class.
        """
        self.gbws = []
        for _ in self.registers:
            self.gbws.append(GroupBulkWrite(self.bus.port_handler,
                                            self.bus.packet_handler))

    def atomic(self):
        """Executes a SyncWrite."""
        for index, reg_name in enumerate(self.registers):
            gbw = self.gbws[index]
            # prepares the call
            for device in self.devices:
                # prepare the buffer data
                register = getattr(device, reg_name)
                data = device.register_low_endian(register.int_value,
                                                  register.size)
                result = gbw.addParam(device.dev_id, register.address,
                                      register.size,
                                      data)
                if not result:
                    logger.error(f'failed to setup BulkWrite for loop '
                                 f'{self.name} for device {device.name}')
            # execute write
            if self.bus.can_use():
                result = gbw.txPacket()
                self.bus.stop_using()       # !! as soon as possible
                error = gbw.ph.getTxRxResult(result)
                if result != 0:
                    logger.error(f'failed to execte BulkWrite {self.name}: '
                                 f'cerr={error}')
            else:
                logger.error(f'sync {self.name} '
                             f'failed to aquire buss {self.name}')
            # cleanup
            gbw.clearParam()


class DynamixelBulkReadLoop(BaseSync):
    """Implements BulkRead as specified in the frequency parameter.

    The devices are provided in the `group` parameter and the registers
    in the `registers` as a list of register names. The registers do not
    need to be sequential.
    It will update the `int_value` of each register in every device with
    the result of the call.
    Will raise exceptions if the BulkRead cannot be setup or fails to
    execute.
    With Protocol 1.0 officially works only with MX devices.
    """

    def setup(self):
        """Prepares to start the loop."""
        self.gbrs = []
        for reg_name in self.registers:
            gbr = GroupBulkRead(self.bus.port_handler,
                                self.bus.packet_handler)
            for device in self.devices:
                register = getattr(device, reg_name)
                result = gbr.addParam(device.dev_id, register.address,
                                      register.size)
                if result is not True:
                    logger.error(f'failed to setup BulkRead for loop '
                                 f'{self.name} for device {device.name}')
            self.gbrs.append(gbr)

    def atomic(self):
        """Executes a BulkRead."""
        # execute read
        for index, reg_name in enumerate(self.registers):
            gbr = self.gbrs[index]
            if not self.bus.can_use():
                logger.error(f'sync {self.name} '
                             f'failed to aquire buss {self.name}')
            else:
                result = gbr.txRxPacket()
                self.bus.stop_using()       # !! as soon as possible
                if result != 0:
                    error = gbr.ph.getTxRxResult(result)
                    logger.error(f'BulkRead {self.name}, cerr={error}')
                else:
                    # retrieve data
                    for device in self.devices:
                        register = getattr(device, reg_name)
                        if not gbr.isAvailable(device.dev_id,
                                               register.address,
                                               register.size):
                            logger.error(f'failed to retrieve data in '
                                         f'BulkRead {self.name} for '
                                         f'device {device.name} and '
                                         f'register {register.name}')
                    else:
                        register.int_value = gbr.getData(device.dev_id,
                                                         register.address,
                                                         register.size)
