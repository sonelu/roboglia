import os
import yaml
import logging
from roboglia.utils import get_registered_class, check_key

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

    Raises:
        KeyError: if mandatory parameters are not found
    """
    def __init__(self, init_dict):
        # these are already checked by robot
        self._name = init_dict['name']
        self._bus = init_dict['bus']
        check_key('id', init_dict, 'device', self._name, logger)
        check_key('model', init_dict, 'device', self._name, logger)
        self._dev_id = init_dict['id']
        self._model = init_dict['model']
        # registers
        model_path = init_dict.get('path', self.get_model_path())
        model_file = os.path.join(model_path, self._model + '.yml')
        with open(model_file, 'r') as f:
            model_ini = yaml.load(f, Loader=yaml.FullLoader)
        self._registers = {}
        for index, reg_info in enumerate(model_ini['registers']):
            check_key('name', reg_info, self._model + ' register',
                      index, logger)
            reg_class_name = reg_info.get('class', self.default_register())
            reg_class = get_registered_class(reg_class_name)
            reg_info['device'] = self
            new_register = reg_class(reg_info)
            self.__dict__[reg_info['name']] = new_register
            self._registers[reg_info['name']] = new_register

    @property
    def name(self):
        """Device name."""
        return self._name

    @property
    def registers(self):
        """Device registers as dict."""
        return self._registers

    @property
    def dev_id(self):
        """The device number"""
        return self._dev_id

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
        return self._bus.read(self, register)

    def write_register(self, register, value):
        """Implements the write of a register using the associated bus.
        More complex devices should overwrite the method to provide
        specific functionality.
        """
        self._bus.write(self, register, value)

    def open(self):
        """Performs initialization of the device."""
        pass

    def close(self):
        """Perform device closure."""
        pass

    def __str__(self):
        result = f'Device: {self._name}, ID: {self._dev_id} ' + \
                 f'on bus: {self._bus.name}:\n'
        for reg in self._registers.values():
            result += f'\t{reg}\n'
        return result
