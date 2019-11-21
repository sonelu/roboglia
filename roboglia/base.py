# Copyright 2019 Alexandru Sonea. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =============================================================================
"""Module defining the base classes.

The base classes for Bus, Device and Robot are defined here. Specific
classes for dedicated bus and device processing will be derived from
these classes.
"""


from roboglia.utils import readIniFile


class BaseBus():
    """A base abstract class for handling an arbitrary bus.

    You will normally subclass `BaseBus` and define particular functionality
    specific to the bus by impementing the methods of the `BaseBus`.
    This class only stores the name of the bus and the access to the
    physical object. Your subclass can add additional attributes and 
    methods to deal with the particularities of the real bus represented.

    Parameters
    ---------
    name
        A string used to identify the bus.

    port
        A string that indentifies technically the bus. For instance a
        serial bus would be `/dev/ttyUSB0` while an SPI bus might be
        represented as `0` only (indicating the SPI 0 bus).

    """
    def __init__(self, name, port):
        """Initializes the bus information.


        """
        self.name = name
        self.port = port

    def open(self):
        """Opens the actual physical bus. Must be overriden by the
        subclass.

        """
        pass

    def close(self):
        """Closes the actual physical bus. Must be overriden by the
        subclass.

        """
        pass

    def isOpen(self):
        """Returns `True` or `False` if the bus is open. Must be overriden 
        by the subclass.

        """
        return False


class BaseDevice():
    """A base virtual class for all devices.

    A BaseDevice is a surrogate representation of an actual device,
    characterised by a number of internal registers that can be read or
    written to by the means of a coomunication bus.
    Any device is based on a `model` that identifies the `.device` file
    describing the structure of the device (the registers).

    Parameters
    ----------
    name : str
        The name that the created device will be associated with. Ex.
        it could be 'l_arm_p' for a Dynamixel servo representing the 
        left arm pitch joint, or it could be 'imu_accel' for the device
        describing the accelerometer.

    model : str
        The name of the device type that is used to initialize its
        structure. A file `.device` needs to be located and parsed 
        successfully in order to the construction of the device to
        be completed. The locatization of the `.device` file is performed
        by the method `getModelPath()` that can return different paths for
        different devices and can be oveloaded by a custom subclass that
        uses custom `.device` files located outside of the main package.

    bus : BaseBus or subclass
        It is the bus that the device uses to read or write values when
        syncronising with the actual device.

    Attributes
    ----------
    name : str
        The name of the device.

    bus : object
        The bus that operates the device.

    registers : dict of objects
        A dictionary with the imutable data of the device's registries
        as loaded from the model `.device` file and initialized.

    values : dict of int
        A dictionary with the current values of the registers. Please note
        that the synchronisation with the physical device must be 
        implemented separatelly.
    """

    def __init__(self, name, model, bus):
        self.name = name
        self.bus = bus
        self.registers = {}
        self.values = {}
        model_file = self.getModelPath(model)
        model_ini = readIniFile(model_file)
        for reginfo in model_ini['registers']:
            new_register = self.processRegister(reginfo)
            reg_name = reginfo['Name']
            self.registers[reg_name] = new_register
            self.values[reg_name] = 0
        

    def getModelPath(self, model):
        """Builds the path to the `.device` documents.

        For BaseDevice it will return a file path located in the directory
        `devices` imediately under the current directory of the Python 
        modeule code.

        Returns
        -------
        str
            A full document path including the name of the model and the
            externasion `.device`.
        """
        pass

    def processRegister(self, reginfo):
        """Defualt processing method for setting up a register.

        Does nothhing in the case of a BaseDevice and subclasses need to
        define their own internal format for the registers and this method
        should return a fully initialized register class based on the 
        information included in `reginfo`.

        Parameters
        ----------
        reginfo : dict
            A dictionry with the register attributes and values.

        Returns
        -------
        object
            An allocated registered which normally should be a
            `namedtuple` class with the attributes of the regiter 
            initialized from the `reginfo` dictionary.
        """
        pass

    def __getattr__(self, attr):
        """Used to create assesors for register values.

        If the provided member is a name that exists in the `registers`
        dictionary it will return the value of that register. Subclasses
        might want to overide this method and implement a more complex
        one that performs conversions between the internal and external
        format of the data (see the DynamixelServo class).

        Parameters
        ----------
        attr: str
            The name of the attribute to be evaluated. Please note that
            this method is called only after the class has already tried
            to evaluate the `attr` against it's own dictionary of 
            attributes and will be called only if the class instance does
            not already have a member with the name as indicated in 
            `attr`. For instance `device.bus` will return the value from
            the `bus` member of the class.
        Returns
        -------
        int
            The content of the register.

        Raises
        ------
        AttributeError 
            If the member name is not in in the list of registers.

        """   
        if attr in self.registers:
            return self.values[attr]
        else:
            raise AttributeError(f'{self.__class__.__name__}.{attr} is invalid.')

    def __setattr__(self, attr, value):
        """Used for setting values of registers.

        If the provided name is a register the method will try to update
        the value into the `values` dictionary.

        Parameters
        ----------
        attr : str
            THe name of the register. Normally passed when invoking
            `servo.register`.

        value 
            The external-formatted value to the stored in the register
            according to the format of that particular register.

        Raises
        ------
        KeyError
            If the attribute requested is not in the list of registers.
        """

        if attr in ['registers', 'values', 'name', 'bus']:
            super().__setattr__(attr, value)
        else:
            if attr in self.registers:
                self.values[attr] = value
            else:
                raise KeyError("attribute {} does not exist".format(attr))


class BaseRobot():

    def __init__(self, ini_file):
        config = readIniFile(ini_file)
        self.ports = {}
        self.devices = {}

        # load the port configuration
        for portconfig in config['ports']:
            PortClass = globals()[portconfig['Class']]
            new_port = PortClass(name=portconfig['Name'],
                                 port=portconfig['Port'])
            self.ports[portconfig['Name']] = new_port
        
        # load the devices
        for device in config['devices']:
            DevClass = globals()[device['Class']]
            new_device = DevClass(name=device['Name'],
                                  model=device['Type'],
                                  bus=self.ports[device['Bus']])
            new_device.id = device['Id']
            self.devices[device['Name']] = new_device
            self.ports[device['Bus']].devices.append(new_device)

    def __getattr__(self, attr):
        if attr in self.devices:
            return self.devices[attr]
        else:
            raise AttributeError(f'{self.__class__.__name__}.{attr} is invalid.')        