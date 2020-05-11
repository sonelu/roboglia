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

from ..utils import get_registered_class, check_key, check_options

logger = logging.getLogger(__name__)


class BaseDevice():
    """A base virtual class for all devices.

    A BaseDevice is a surrogate representation of an actual device,
    characterised by a number of internal registers that can be read or
    written to by the means of a coomunication bus.
    Any device is based on a `model` that identifies the `.device` file
    describing the structure of the device (the registers).

    Args:
        init_dict (dict): The dictionary used to initialize the joint.

    The following keys are exepcted in the dictionary:

    - ``name``: the name of the joint
    - ``bus``: the bus object where the device is attached to
    - ``id``: the device ID on the bus
    - ``model``: the model of the device; used to identify the device template

    The following keys are optional and can be omitted. They will be
    defaulted with the values mentioned bellow:

    - ``path``: a path to the model file; defaulted to `get_model_path`
    - ``auto``: the device should open automatically when the robot
      starts; defaults to ``True``

    Raises:
        KeyError: if mandatory parameters are not found
    """
    def __init__(self, init_dict):
        # these are already checked by robot
        self.__name = init_dict['name']
        self.__bus = init_dict['bus']
        check_key('id', init_dict, 'device', self.__name, logger)
        check_key('model', init_dict, 'device', self.__name, logger)
        self.__dev_id = init_dict['id']
        self.__model = init_dict['model']
        # registers
        model_path = init_dict.get('path', self.get_model_path())
        model_file = os.path.join(model_path, self.__model + '.yml')
        with open(model_file, 'r') as f:
            model_ini = yaml.load(f, Loader=yaml.FullLoader)
        self.__registers = {}
        for reg_name, reg_info in model_ini['registers'].items():
            # add name to the dictionary
            reg_info['name'] = reg_name
            reg_class_name = reg_info.get('class', self.default_register())
            reg_class = get_registered_class(reg_class_name)
            reg_info['device'] = self
            new_register = reg_class(reg_info)
            self.__dict__[reg_info['name']] = new_register
            self.__registers[reg_info['name']] = new_register
        self.__auto_open = init_dict.get('auto', True)
        check_options(self.__auto_open, [True, False], 'device',
                      self.name, logger)

    @property
    def name(self):
        """Device name."""
        return self.__name

    @property
    def registers(self):
        """Device registers as dict."""
        return self.__registers

    def register_by_address(self, address):
        for register in self.registers.values():
            if register.address == address:
                return register
        return None

    @property
    def dev_id(self):
        """The device number"""
        return self.__dev_id

    @property
    def bus(self):
        """The bus where the device is connected to."""
        return self.__bus

    @property
    def auto_open(self):
        """Indicates that the device's :py:method:`open` is supposed to be
        called by the robot's :py:method:`Robot.start` method."""
        return self.__auto_open

    def get_model_path(self):
        """Builds the path to the `.device` documents.

        By default it will return the path to the `devices/<model>.yml`
        file in the current directory of the method being called.

        Returns
        -------
        str
            A full document path including the name of the model and the
            extension `.yml`.
        """
        return os.path.join(os.path.dirname(__file__), 'devices')

    def default_register(self):
        """Default register for the device in case is not explicitly
        provided in the device defition file.
        Subclasses of `BaseDevice` can overide the method to derive their
        own class.
        """
        return 'BaseRegister'

    def read_register(self, register):
        """Implements the read of a register using the associated bus.
        More complex devices should overwrite the method to provide
        specific functionality.
        """
        return self.bus.read(self, register)

    def write_register(self, register, value):
        """Implements the write of a register using the associated bus.
        More complex devices should overwrite the method to provide
        specific functionality.
        """
        self.bus.write(self, register, value)

    def open(self):
        """Performs initialization of the device by reading all registers."""
        for register in self.registers.values():
            self.read_register(register)

    def close(self):
        """Perform device closure."""
        pass

    def __str__(self):
        result = f'Device: {self.name}, ID: {self.dev_id} ' + \
                 f'on bus: {self.bus.name}:\n'
        for reg in self.registers.values():
            result += f'\t{reg}\n'
        return result
