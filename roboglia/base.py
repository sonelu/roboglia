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

from roboglia.utils import readIniFile, processList, processParams
from collections import deque


class BaseNamedOwed():
    """A base class for all objects that have a name and a parent.
    """
    def __init__(self, parent, dictInfo):
        self.name = dictInfo['Name']
        self.parent = parent


class BaseBus(BaseNamedOwed):
    """A base abstract class for handling an arbitrary bus.

    You will normally subclass ``BaseBus`` and define particular functionality
    specific to the bus by implementing the methods of the ``BaseBus``.
    This class stores the name of the bus and the access to the
    physical object as well as a ``deque`` for postponed writes to the
    actual bus. Your subclass can add additional attributes and 
    methods to deal with the particularities of the real bus represented.

    Parameters
    ----------
    parent : object
        The owner of the bus, usually the robot.

    dictInfo : dict
        The data in the dictionary is usually taken from an INI file and
        should include at least (for this class) the keys 'Name' and 'Port'.
        
    Attributes
    ----------
    writeQueue : collections.deque
        A queue that holds deferred updates to devices' registries. See
        more in the description of ``BaseDevice``. 
    """
    def __init__(self, parent, dictInfo):
        super().__init__(parent, dictInfo)
        self.port = dictInfo['Port']
        self.writeQueue = deque()

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

    def writeQueueAdd(self, register):
        """Add a register to the write queue.

        Parameters
        ----------
        register : BaseRegister or subclass
            Register that is queued for deferred write. 
        """
        self.writeQueue.append(register)

    def writeQueueExec(self):
        """Invokes the register's ``write()`` method to syncronize the content
        of a register for all the requests in the ``writeQueue``. The robot
        is responsible for setting up a thread that calls regularly this 
        method for each bus owned in order to flush all queued requests
        for syncronization.

        .. note: This method might be very unperformant depending on the
           they of the bus since it will invoke transimtting a communication
           packet for each register included in the queue. For certain type
           of devices (ex. Dynamixel servos) there are more performant methods
           like using SyncWrite or BulkWrite that perform the write in a
           single communication packet for a series of devices and registers.
        """
        while len(self.writeQueue) > 0:
            register = self.writeQueue.popleft()
            register.write()


class BaseRegister(BaseNamedOwed):
    """A minimal representation of a device register.
    """
    def __init__(self, parent, dictInfo):
        super().__init__(parent, dictInfo)
        self.address = int(dictInfo['Address'])
        self.size = int(dictInfo['Size'])
        self.type = dictInfo['Type']
        self.access = dictInfo['Access']
        self.sync = dictInfo['Sync']
        self._int_value = 0

    @property
    def int_value(self):
        if self.sync == 'D':
            # refresh the value of the register
            if not self.read():
                msg = "Failed to read register {} of {}"
                raise IOError(msg.format(self.name, self.parent.name))
        return self._int_value

    @int_value.setter
    def int_value(self, value):
        self._int_value = value
        if self.sync == 'D':
            if not self.write():
                msg = "Failed to write register {} of {}"
                raise IOError(msg.format(self.name, self.parent.name))
        elif self.sync == 'Q':
            self.parent.writeQueueAdd(self)

    def write(self):
        """Performs the actual writing of the internal value of the register
        to the device. In `BaseDevice` the method doesn't do anything and
        subclasses should overwrite this mehtod to actually invoke the 
        buses' methods for writing information to the device.
        """
        return True

    def read(self):
        """Performs the actual reading of the internal value of the register
        from the device. In `BaseDevice` the method doesn't do anything and
        subclasses should overwrite this mehtod to actually invoke the 
        buses' methods for reading information from the device.
        """
        return True


class RegisterWithMinMax(BaseRegister):
    """An extension of the ``BaseRegister`` to include Min and Max values
    with checks.
    """
    def __init__(self, parent, dictInfo):
        super().__init__(parent, dictInfo)
        self.min = int(dictInfo['Min'])
        self.max = int(dictInfo['Max'])

    @property
    def int_value(self):
        return super().int_value

    @int_value.setter
    def int_value(self, value):
        if value < self.min or value > self.max:
            msg = "Value {} outside of range {} - {} for register {} of {}"
            raise ValueError(msg.format(value, self.min, self.max, self.name, self.parent.name))
        else:
            super().int_value = value


class RegisterWithExternalRepresentation(BaseRegister):
    """An extension of ``BaseRegister`` to include external representation
    and conversion.
    """
    def __init__(self, parent, dictInfo):
        super().__init__(parent, dictInfo)
        extParams = processParams(dictInfo['External'])
        self.ext_type = extParams['Type']
        # no conversion functions by default
        self.to_ext = None
        self.to_int = None
        # default Divisor and Offset
        self.ext_div = 1.0
        self.ext_offPre = 0.0
        self.ext_offPost = 0.0
        if 'Div' in extParams:
            self.ext_div = float(extParams['Div'])
            self.to_ext = 'convDaOtoExternal'
            self.to_int = 'convDaOtoInternal'
        if 'OffPre' in extParams:
            self.ext_offPre = float(extParams['OffPre'])
            self.to_ext = 'convDaOtoExternal'
            self.to_int = 'convDaOtoInternal'
        if 'OffPost' in extParams:
            self.ext_offPost = float(extParams['OffPost'])
            self.to_ext = 'convDaOtoExternal'
            self.to_int = 'convDaOtoInternal'
        if 'Fun' in extParams:
            # make sure only 'Fun' used
            if self.to_ext != None:
                msg = "You cannot set both Divisor/Offset and custom function for register {} for parent {}"
                raise ValueError(msg.format(self.name, self.parent.name))
            else:
                self.to_ext = extParams['Fun']+'ToExternal'
                self.to_int = extParams['Fun']+'ToInternal'
                # check methods exist
                if not hasattr(self, self.to_ext):
                    raise ValueError("Class {} has no method {}".format(self.__class__.__name__, self.to_ext))
                if not hasattr(self, self.to_int):
                    raise ValueError("Class {} has no method {}".format(self.__class__.__name__, self.to_int))

    def convDaOtoExternal(self, value):
        return ((value -self.ext_offPre) / self.ext_div - self.ext_offPost ) #* sign

    def convDaOtoInternal(self, value):
        return round((value + self.ext_offPost) * self.ext_div + self.ext_offPre)

    @property
    def value(self):
        if self.to_ext != None:
            converted = getattr(self, self.to_ext)(self.int_value)
        else:
            converted = self.int_value
        # convert to type
        if self.ext_type == 'I':
            return int(converted)
        elif self.ext_type == 'F':
            return float(converted)
        elif self.ext_type == 'B':
            return converted != 0
        else:
            msg = "Unknown external type {} for register {} of {}"
            raise KeyError(msg.format(self.ext_type, self.name, self.parent.name))

    @value.setter
    def value(self, external):
        if self.to_int != None:
            converted = getattr(self, self.to_int)(external)
        else:
            converted = int(external)
        self.int_value = converted


class BaseDevice(BaseNamedOwed):
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
    def __init__(self, parent, dictInfo):
        super().__init__(parent, dictInfo)
        self.dev_id = int(dictInfo['Id'])
        self.registers = {}
        model_file = self.getModelPath(dictInfo['Model'])
        model_ini = readIniFile(model_file)
        for reginfo in model_ini['registers']:
            new_register = self.initRegister(reginfo)
            self.__dict__[reginfo['Name']] = new_register
            self.registers[reginfo['Name']] = new_register

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
        return ''

    def initRegister(self, reginfo):
        """Default processing method for setting up a register.

        Does nothhing in the case of a BaseDevice and subclasses need to
        define their own internal format for the registers. This method
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
        return BaseRegister(parent=self,
                            dictInfo = reginfo)

    # def readRegisterList(self, reglist=[]):
    #     result = {}
    #     for regname in reglist:
    #         register = self.registers[regname]
    #         result[register.name] = register.read()
    #     return result

    # def writeRegisterList(self, reglist=[]):
    #     result = {}
    #     for regname in reglist:
    #         register = self.registers[regname]
    #         if register.access != 'R':
    #             result[register.name] = register.write()
    #     return result

    # def readAllRegisters(self):
    #     return self.readRegisterList(self.registers.keys())

    # def writeAllRegisters(self):
    #     return self.writeRegisterList(self.registers.keys())

    # def toDict(self):
    #     result = {}
    #     for regname, reg in self.registers.items():
    #         result[regname] = reg.value
    #     return result


class BaseGroup():

    def __init__(self, devlist, subgrouplist, check=True):
        self.items = devlist.copy()
        for subgroup in subgrouplist:
            self.items.extend(subgroup.items)
        if check:
        # check all devices have the same class
            if len(self.items) > 0:
                classname = self.items[0].__class__.__name__
                for item in self.items:
                    if item.__class__.__name__ != classname:
                        raise ValueError("devices must have the same class in a group")

    @classmethod
    def fromInfoDict(cls, groupinfo, robot):
        devnames = processList(groupinfo['Devices'])
        groupnames = processList(groupinfo['Subgroups'])
        devs = [robot.devices[devname] for devname in devnames]
        groups = [robot.groups[groupname] for groupname in groupnames]
        return cls(devs, groups)

    def __getattr__(self, attr):
        if (self.items) == 0:
            return self
        if hasattr(self.items[0], attr):
            return BaseGroup([getattr(item, attr) for item in self.items], [], check=False)
        else:
            raise AttributeError("class {} does not have {} attribute".format(self.devices[0].__class__.__name__, attr))

    def __setattr__(self, attr, value):
        if attr == 'items':
            super().__setattr__(attr, value)
        elif len(self.items) > 0:
            for item in self.items:
                setattr(item, attr, value)


class BaseSync():

    @classmethod
    def fromInfoDict(cls, syncinfo, robot):
        identifiers = processList(syncinfo['Devices'])
        devices = robot.devicesFromMixedList(identifiers)
        regnames = processList(syncinfo['Registers'])
        registers = [getattr(device, regname) for regname in regnames for device in devices]
        return cls(registers)

    def run(self):
        pass

class BaseSyncRead(BaseSync):

    def __init__(self, reglist):
        self.registers = reglist

    def run(self):
        for register in self.registers:
            register.read()


class BaseSyncWrite(BaseSync):

    def __init__(self, reglist):
        self.registers = reglist

    def run(self):
        for register in self.registers:
            if register.access != 'R':
                register.write()


class BaseRobot():

    def __init__(self, ini_file):
        if ini_file == '':
            config = {}
        else:
            config = readIniFile(ini_file)
        self.buses = {}
        self.devices = {}
        self.groups = {}
        self.sync = {}
        # load the bus configuration
        for businfo in config['buses']:
            new_bus = self.initBus(self, businfo)
            self.buses[businfo['Name']] = new_bus
        # load the devices
        for devinfo in config['devices']:
            bus = self.buses[devinfo['Bus']]
            new_device = self.initDevice(bus, devinfo)
            self.devices[devinfo['Name']] = new_device
            bus.devices.append(new_device)
        # load groups
        for groupinfo in config['groups']:
            new_group = self.initGroup(groupinfo, self)
            self.groups[groupinfo['Name']] = new_group
            self.__dict__[groupinfo['Name']] = new_group
        # load sync definition
        for syncinfo in config['sync']:
            new_sync = self.initSync(syncinfo, self)
            self.sync[syncinfo['Name']] = new_sync
            self.__dict__[syncinfo['Name']] = new_sync

    def devicesFromMixedList(self, listOfIdentifiers):
        devices = []
        for identifier in listOfIdentifiers:
            if identifier in self.groups:
                devices.extend(self.groups[identifier].items)
            elif identifier in self.devices:
                devices.append(self.devices[identifier])
            else:
                raise KeyError('Unknown device {}'.format(identifier))
        return devices
        
    def initBus(self, owner, businfo):
        """BaseRobot only knows BaseBus and this default method
        will allocate one. Subclasses should override this method and
        implement allocation for all the device classes they use.
        """
        if businfo['Class'] == 'BaseBus':
            return BaseBus(parent=owner, dictInfo=businfo)
        else:
            msg = "Unknown bus class name: {}"
            raise KeyError(msg.format(businfo['Class']))

    def initDevice(self, owner, devinfo):
        if devinfo['Class'] == 'BaseDevice':
            return BaseDevice(owner, devinfo)
        else:
            raise KeyError('Unknown device class name {}'.format(devinfo['Class']))

    def initGroup(self, groupinfo, robot):
        if groupinfo['Class']== 'BaseGroup':
            return BaseGroup.fromInfoDict(groupinfo, robot)
        else:
            raise KeyError('Unknown group class name {}'.format(groupinfo['Class']))

    def initSync(self, syncinfo, robot):
        if syncinfo['Class'] == 'BaseSyncRead':
            return BaseSyncRead.fromInfoDict(syncinfo, robot)
        elif syncinfo['Class'] == 'BaseSyncWrite':
            return BaseSyncWrite.fromInfoDict(syncinfo, robot)
        else:
            raise KeyError('Unknown sync class name {}'.format(syncinfo['Class']))