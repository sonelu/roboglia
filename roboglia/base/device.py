import os
import yaml
from .factory import get_registered_class

class BaseDevice():
    """A base virtual class for all devices.

    A BaseDevice is a surrogate representation of an actual device,
    characterised by a number of internal registers that can be read or
    written to by the means of a coomunication bus.
    Any device is based on a `model` that identifies the `.device` file
    describing the structure of the device (the registers).

    Parameters
    ----------

    Attributes
    ----------
    
    """
    def __init__(self, init_dict):
        # these are mandatory attributes; will throw exception if
        # not provided in the initialization dictionary
        self.name = init_dict['name']
        self.bus = init_dict['bus']
        self.dev_id = init_dict['id']
        # registers
        model_path = init_dict.get('path', self.get_model_path())
        model_file = os.path.join(model_path, init_dict['model']+'.yml')
        with open(model_file, 'r') as f:
            model_ini = yaml.load(f, Loader=yaml.FullLoader)
        self.registers = {}
        for reginfo in model_ini['registers']:
            reg_class_name = reginfo.get('class', self.default_register())
            register_class = get_registered_class(reg_class_name)
            reginfo['device'] = self
            new_register = register_class(reginfo)
            self.__dict__[reginfo['name']] = new_register
            self.registers[reginfo['name']] = new_register


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
        """Performs initialization of the device.
        """
        pass


    def __str__(self):
        result = f'Device: {self.name}, ID: {self.dev_id} on bus: {self.bus.name}:\n'
        for reg in self.registers.values():
            result += f'\t{reg}\n'
        return result