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
"""Module defining classes used to manipulate devices.

A device is a physical robot component that has a state and can send or
receive information. Example of devices are: actuators, sensors, cameras,
displays, etc.

"""

import os
from roboglia.utils import readIniFile
from collections import namedtuple

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

        return os.path.join(os.path.dirname(__file__), 'devices', model+'.device')

    def processRegister(self, reginfo):
        """Defualt processing method for setting up a register.

        Does nothhing in the case of a BaseDevice and subclasses need to
        define their own internal format for the registers and this method
        should return a fully initialized register class based on the 
        information included in `reginfo`.
        """
        pass

    def __getattr__(self, attr):
        """Used to create assesors for register values.

        If the provided member is a name that exists in the `registers`
        dictionary it will return the value of that register.

        Returns
        -------
        int
            The content of the register in external format.

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