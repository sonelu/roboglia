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
from .thread import BaseLoop
from .bus import SharedBus
from ..utils import check_key, check_type, check_options, check_not_empty

logger = logging.getLogger(__name__)


class BaseSync(BaseLoop):
    """Base processing for a sync loop.

    This class is intended to be subclassed to provide specific functionality.
    It only parses the common elements that a sync loop would need:
    the devices (provided by a group) and registers (provided by a list).
    It will check that the provided devices are on the same bus and that
    the provided registers exist in all devices.

    .. note:: Please note that this class does not actually perform any sync.
        Use the subclasses :py:class:`BaseReadSync` or
        :py:class:`BaseWriteSync` that implement read or write syncs.

    ``BaseSync`` inherits the parameters from :py:class:`BaseLoop`. In
    addition it includes the following parameters.

    Parameters
    ----------
    group: set
        The set with the devices used by sync; normally the robot
        constructor replaces the name of the group from YAML file with the
        actual set built earlier in the initialization.

    registers: list of str
        A list of register names (as strings) used by the sync

    auto: bool
        If the sync loop should start automatically when the robot
        starts; defaults to ``True``

    Raises
    ------
        KeyError: if mandatory parameters are not found
    """

    def __init__(self, group=None, registers=[], auto=True, **kwargs):
        super().__init__(**kwargs)
        check_not_empty(group, 'group', 'sync', self.name, logger)
        check_type(group, set, 'sync', self.name, logger)
        self.__devices = list(group)
        self.__bus = self.process_devices()
        check_type(self.__bus, SharedBus, 'sync', self.name, logger)
        check_not_empty(registers, 'registers', 'sync', self.name, logger)
        check_type(registers, list, 'sync', self.name, logger)
        self.__registers = registers
        check_options(auto, [True, False], 'sync', self.name, logger)
        self.__auto_start = auto
        self.process_registers()

    @property
    def auto_start(self):
        """Shows if the sync should be started automatically when the
        robot starts.
        """
        return self.__auto_start

    @property
    def bus(self):
        """The bus this sync works with."""
        return self.__bus

    @property
    def devices(self):
        """The devices used by the sync."""
        return self.__devices

    @property
    def registers(self):
        """The registers used buy the sync."""
        return self.__registers

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
        buses = set([device.bus for device in self.__devices])
        if len(buses) > 1:
            mess = f'Devices used for sync {self.name} should be ' + \
                   'connected to a single bus.'
            logger.critical(mess)
            raise ValueError(mess)
        elif len(buses) == 0:
            mess = f'You need at least one device for sync {self.name}.'
            logger.critical(mess)
            raise ValueError(mess)
        # there must be only one!
        one_bus = buses.pop()
        return one_bus

    def process_registers(self):
        """Checks that the supplied registers are available in all
        devices and sets the ``sync`` attribute to ``True`` if not already
        set."""
        for device in self.__devices:
            for register in self.__registers:
                check_key(register, device.registers, 'sync',
                          self.name, logger,
                          f'device {device.name} does not have a '
                          f'register {register}')
                # mark the register for sync
                reg_obj = getattr(device, register)
                if not reg_obj.sync:
                    reg_obj.sync = True
                    logger.debug(f'Setting register "{register}" of device '
                                 f'"{device.name}" sync=True')

    def get_register_range(self):
        """Determines the start address of the range of registers and the
        whole length. Registers do not need to be order, but be careful
        that not all communication protocols can support gaps in the
        bulk read of registers.
        """
        start_address = 65536
        last_address = 0
        last_length = 0
        length = 0
        # pick the first device; we expect all to have the same registers
        device = self.devices[0]
        for reg_name in self.registers:
            register = getattr(device, reg_name)
            if register.address < start_address:
                start_address = register.address
            if register.address > last_address:
                last_address = register.address
                last_length = register.size
        length = last_address + last_length - start_address
        return start_address, length

    def start(self):
        """Checks that the bus is open before calling the inherited
        ``start``."""
        if not self.bus.is_open:
            logger.error(f'sync {self.name}: attempt to start with a bus '
                         f'not open')
        else:
            super().start()


class BaseReadSync(BaseSync):
    """A SyncLoop that performs a naive read of the registers by sequentially
    calling the ``read`` on each of them.

    It wraps the processing between buses' ``can_use()`` and ``stop_using()``
    methods and uses ``naked_read`` instead of the ``read`` method.
    """
    def atomic(self):
        """Implements the read of the registers.

        This is a naive implementation that will simply loop over all
        devices and registers and ask them to refresh.
        """
        if self.bus.can_use():
            for device in self.devices:
                for reg_name in self.registers:
                    reg = getattr(device, reg_name)
                    value = self.bus.naked_read(reg)
                    logger.debug(f'Read {value} for device "{device.name}" '
                                 f'register "{reg_name}"')
                    if value is not None:
                        reg.int_value = value
                    else:
                        logger.warning(f'Sync "{self.name}": failed to read '
                                       f'register "{reg_name}" '
                                       f'of device "{device.name}"')
            self.bus.stop_using()
        else:
            logger.error(f'Failed to acquire bus "{self.bus.name}"')


class BaseWriteSync(BaseSync):
    """A SyncLoop that performs a naive write of the registers by sequentially
    calling the ``read`` on each of them.

    It wraps the processing between buses' ``can_use()`` and ``stop_using()``
    methods and uses ``naked_write`` instead of the ``write`` method.
    """
    def atomic(self):
        """Implements the writing of the registers.

        This is a naive implementation that will simply loop over all
        devices and registers and ask them to refresh.
        """
        if self.bus.can_use():
            for device in self.devices:
                for reg_name in self.registers:
                    reg = getattr(device, reg_name)
                    self.bus.naked_write(reg, reg.int_value)
                    logger.debug(f'Wrote {reg.int_value} for device '
                                 f'"{device.name}" register "{reg_name}"')
            self.bus.stop_using()
        else:
            logger.error(f'Failed to acquire bus "{self.bus.name}"')
