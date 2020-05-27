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

import os
import yaml
import logging

from ..utils import get_registered_class, check_not_empty, \
                    check_type, check_key

from .bus import BaseBus, SharedBus

logger = logging.getLogger(__name__)


class BaseDevice():
    """A base virtual class for all devices.

    A ``BaseDevice`` is a surrogate representation of an actual device,
    characterized by a number of internal registers that can be read or
    written to by the means of a comunication bus.
    Any device is based on a ``model`` that identifies the ``.yml`` file
    describing the structure of the device (the registers).

    .. note: Device defintion files are searched in a path provided by
        the method :py:meth:`get_model_path` unless a specific path is
        provided in the `path` parameter. This way, if no `path` is provided
        the specific device class can use different locations to place the
        files. For instance `BaseDevice` will provide the location
        ``roboglia/base/devices/``, ``DynamixelDevice`` will provide
        ``roboglia/dynamixel/devices/``, ``I2CDevice`` will provide
        ``roboglia/i2c/devices/``, etc. If you want to use a device that does
        not exist in ``roboglia`` and for which you have created a YAML file
        you can indicate the directory where the file is located with the
        `path` paramters and the name of the file in the `model` parameter.

    .. warning: If you plan to use ``auto`` in the device or have
        initializations in `init` parameter you have to make sure that the
        associated bus is also marked with ``auto: True``, otherwise the reads
        and writes during the opening of the device will fail with ``attempt
        to read(write) from(to) a closed bus.

    Parameters
    ----------
    name: str
        The name of the device

    bus: BaseBus or subclass
        The bus object where the device is attached to

    id: int
        The device ID on the bus. Typically it is an ``int`` but some buses
        may use a different identifier. The processing should still work
        fine.

    model: str
        A string used to identify the device description. Please see the
        note bellow regarding the position of the device description files.

    path: str
        A path to the model file in case you want to use custom defined
        devices that are not available in the ``roboglia`` repository.
        Please see the note bellow regarding the position of the device
        description files.

    inits: list
        A list of init templates to be applied to the device's registers
        when the :py:meth:`~open` method is called,
        where template names were defined earier in the robot definition in the
        ``inits`` section. Please note
        the initialization values should be provided in the **external**
        format of the register as they will be used as::

            register.value = dict_value

        As no syncs are currently implemented this will automatically
        trigger a ``write`` call to store that value in the device.

    Raises
    ------
        KeyError
            if mandatory parameters are not found or unexpected values
            are used (ex. for boolean)
    """

    cache = {}
    """A chache of device models that is updated when a new model is
    encountered and reused when the same model is requested during
    device creation.
    """

    def __init__(self, name='DEVICE', bus=None, dev_id=None, model=None,
                 path=None, inits=[], **kwargs):
        # these are already checked by robot
        self.__name = name
        check_not_empty(bus, 'bus', 'device', name, logger)
        check_type(bus, [SharedBus, BaseBus], 'device', name, logger)
        self.__bus = bus
        check_not_empty(dev_id, 'dev_id', 'device', name, logger)
        self.__dev_id = dev_id
        check_not_empty(model, 'model', 'device', name, logger)
        check_type(model, str, 'device', name, logger)
        self.__model = model
        # registers
        if not path:
            path = self.get_model_path()
        model_file = os.path.join(path, model + '.yml')
        if model_file not in BaseDevice.cache:
            with open(model_file, 'r') as f:
                model_ini = yaml.load(f, Loader=yaml.FullLoader)
            BaseDevice.cache[model_file] = model_ini
        else:
            model_ini = BaseDevice.cache[model_file]
        self.__registers = {}
        self.__reg_by_addr = {}
        clones = []
        for reg_name, reg_info in model_ini['registers'].items():
            # add name to the dictionary
            reg_info['name'] = reg_name
            reg_info['device'] = self
            if reg_info.get('clone', False):
                # we register clones at the end after we have the main
                # registers so that we can refer to them
                clones.append(reg_info)
            else:
                reg_class_name = reg_info.get('class', self.default_register())
                reg_class = get_registered_class(reg_class_name)
                new_register = reg_class(**reg_info)
                # we add as an attribute of the register too
                self.__dict__[reg_name] = new_register
                self.__registers[reg_name] = new_register
                self.__reg_by_addr[reg_info['address']] = new_register
        # now the clones
        for reg_info in clones:
            # check that the register address is covered by a main register
            check_key('address', reg_info, 'register', reg_info['name'],
                      logger)
            check_key(reg_info['address'], self.__reg_by_addr, 'register',
                      reg_info['name'], logger,
                      f'no main register with address {reg_info["address"]} '
                      'defined')
            reg_info['clone'] = self.register_by_address(reg_info['address'])
            reg_name = reg_info['name']
            reg_class_name = reg_info.get('class', self.default_register())
            reg_class = get_registered_class(reg_class_name)
            new_register = reg_class(**reg_info)
            # we add as an attribute of the register too
            self.__dict__[reg_name] = new_register
            self.__registers[reg_name] = new_register
        self.__inits = inits

    @property
    def name(self):
        """Device name.

        Returns
        -------
        str:
            The name of the device
        """
        return self.__name

    @property
    def registers(self):
        """Device registers as dict.

        Returns
        -------
        dict:
            The dictionary of registers with the register name as key.
        """
        return self.__registers

    def register_by_address(self, address):
        """Returns the register identified by the given address. If the
        address is not available in the device it will return ``None``.

        Returns
        -------
        BaseDevice or subclass or ``None``:
            The device at `address` or ``None`` if no register with that
            address exits.
        """
        return self.__reg_by_addr.get(address, None)

    @property
    def dev_id(self):
        """The device number.

        Returns
        -------
        int:
            The device number
        """
        return self.__dev_id

    @property
    def bus(self):
        """The bus where the device is connected to.

        Returns
        -------
        BaseBus or SharedBus or subclass:
            The bus object using this device.
        """
        return self.__bus

    def get_model_path(self):
        """Builds the path to the device description documents.

        By default it will return the path to the `roboglia/base/devices/`
        directory.

        Returns
        -------
        str
            A full document path.
        """
        return os.path.join(os.path.dirname(__file__), 'devices')

    def default_register(self):
        """Default register for the device in case is not explicitly
        provided in the device definition file.

        Subclasses of ``BaseDevice`` can overide the method to derive their
        own class.

        ``BaseDevice`` suggests as default register :py:class:`BaseRegister`.
        """
        return 'BaseRegister'

    def read_register(self, register):
        """Implements the read of a register using the associated bus.
        More complex devices should overwrite the method to provide
        specific functionality.

        ``BaseDevice`` simply calls the bus's ``read`` function and returns
        the value received.
        """
        return self.bus.read(register)

    def write_register(self, register, value):
        """Implements the write of a register using the associated bus.
        More complex devices should overwrite the method to provide
        specific functionality.

        ``BaseDevice`` simply calls the bus's ``write`` function and returns
        the value received.
        """
        self.bus.write(register, value)

    def open(self):
        """Performs initialization of the device by reading all registers
        that are not flagged for ``sync`` replication and, if ``init``
        parameter provided initializes the indicated
        registers with the values from the ``init`` paramters.
        """
        if self.__inits:
            logger.info(f'Initializing device "{self.name}"')
        for init in self.__inits:
            for reg_name, value in init.items():
                if reg_name not in self.registers:
                    logger.warning(f'Register "{reg_name}" does not exist in '
                                   f'device "{self.name}"; '
                                   'skipping initialization')
                else:
                    register = self.registers[reg_name]
                    if value is None:
                        register.read()
                        logger.debug(f'Register "{reg_name}" read')
                    else:
                        register.value = value
                        logger.debug(
                            f'Register "{reg_name}" updated to {value} '
                            f'(int_value: {register.int_value})')

    def close(self):
        """Perform device closure. ``BaseDevice`` implementation does
        nothing."""
        pass

    def __str__(self):
        result = f'Device: {self.name}, ID: {self.dev_id} ' + \
                 f'on bus: {self.bus.name}:\n'
        for reg in self.registers.values():
            result += f'\t{reg}\n'
        return result
