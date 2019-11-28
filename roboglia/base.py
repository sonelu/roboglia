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

from roboglia.utils import readIniFile, processList
from collections import deque


class BaseBus():
    """A base abstract class for handling an arbitrary bus.

    You will normally subclass ``BaseBus`` and define particular functionality
    specific to the bus by impementing the methods of the ``BaseBus``.
    This class only stores the name of the bus and the access to the
    physical object. Your subclass can add additional attributes and 
    methods to deal with the particularities of the real bus represented.

    Parameters
    ----------
    name : str
        Identifucation of the bus. Should not contain whitespaces.

    port : str
        A string that indentifies technically the bus. For instance a
        serial bus would be `/dev/ttyUSB0` while an SPI bus might be
        represented as `0` only (indicating the SPI 0 bus).

    Attributes
    ----------
    writeQueue : collections.deque
        A queue that holds deferred updates to devices' registries. See
        more in the description of `BaseDevice`. 
    """
    def __init__(self, name, port):
        """Initializes a ``BaseBus``.

        Parameters
        ----------
        name : str
            The name of the bus. Must not contain whitespaces.

        port : str
            The port used by the bus.
        """
        self.name = name
        self.port = port
        self.writeQueue = deque()

    @classmethod
    def fromInfoDict(cls, businfo):
        """Instantiate a ``BaseBus`` from a dictionary.

        Parameters
        ----------
        businfo : dict
            A dictionary with information about the bus. Must
            have at least the following 2 keys:

            * `Name` : the name of the bus
            * `Port` : the port for the bus

            All values are expected to be strings.
        """
        return BaseBus(businfo['Name'], businfo['Port'])

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
            Register that is queed for deferred write. 
        """
        self.writeQueue.append(register)
        print('added to queue; len={}'.format(len(self.writeQueue)))

    def writeQueueExec(self):
        """Invokes the register's `write()` method to syncronize the content
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


class BaseRegister():
    """A minimal representation of a device register.

    Parameters
    ----------
    device : BaseDevice or subclass
        The owner of the register

    name : str
        The name of the register. Must not contain whitespaces.

    address : int
        How the register is phisically addressed.

    access : str
        Should be 'R' for read-only registers and 'RW' for writtable
        registers. You will not be able to set values of a 'R' register.

    sync : str
        The way the register is syncronised with the real device. Possible
        values are: 
            * 'D' - direct syncronisation: a read or write of the register 
              will trigger a low level hardware read or write and produce 
              the value of from the actual device
            * 'Q' - queued synchronisation: applies only for a write to a
              register; it will queue the request to the bus's writeQueue
              and it is the responsibility of the bus owner (ex. the robot)
              to schedule a thread that will periodically flush the queue.
              Subsequent reads of the register's value will reflect the
              requested write value and not the actual value until the 
              queue request is processed.
            * 'B' - batch synchronisation; this assumes that the bus owner
              (ex. the robot) schedules a period thread to synchronize the
              information of this register (for efficency purposes). As a
              result result the values in these registers might be different
              from the actual values in the device until such a refresh
              thread completes.

    Attributes
    ----------
    device : BaseDevice or subclass
        Stores the owner of the register

    name : str
        The name of the register

    address : int
        The address of the register in the device

    access : str
        How the register is accessed

    sync : str
        The syncronization mode

    int_value : int
        The internal representation of the register's value
    """
    def __init__(self, device, name, address, access, sync):
        self.device = device
        self.name = name
        self.address = address
        self.access = access
        self.sync = sync
        self.int_value = 0

    @property
    def value(self):
        """
        The external representation of the register's value.
        
        The getter will return external representation of the register.
        If the register has a 'D' sych property (direct) it will also 
        try to invoke the `read()` method of the register to 
        get the most up to date value. ``BaseRegister`` assumes all
        values are represented as ``int``.

        The setter will invoke the ``valueToInteral`` method before
        storring the result in the ``int_value``. If the register is read 
        only it will raise an exception. If the register has a sync 'D' it 
        will invoke the ``write()`` method of the register. If the sync 
        mode is 'Q' it will push the update request to the bus' 
        ``writeQueue``.
        """
        if self.sync == 'D':
            self.read()
        return self.valueToExternal(self.int_value)

    @value.setter
    def value(self, value):
        if self.access == 'R':
            raise ValueError('Register: {} is read-only. You cannot assign a value to it'.format(self.name))
        self.int_value = self.valueToInternal(value)
        if self.sync == 'D':
            # direct sync
            self.write()
        elif self.sync == 'Q':
            print('Adding to queue...')
            self.device.bus.writeQueueAdd(self)

    def valueToExternal(self, value):
        """Converts the internal value to an external one. For `BaseRegister`
        this simply returns the input value without any conversion. 
        Subclasses might overwrite this method to provide more complex
        behaviour.
        """
        return value

    def valueToInternal(self, value):
        """Converts the external value to an internal one. For `BaseRegister`
        this simply returns the input value converted to an integer. 
        Subclasses might overwrite this method to provide more complex
        behaviour.
        """
        return int(value)

    def write(self):
        """Performs the actual writing of the internal value of the register
        to the device. In `BaseDevice` the method doesn't do anything and
        subclasses should overwrite this mehtod to actually invoke the 
        buses' methods for writing information to the device.
        """
        pass

    def read(self):
        """Performs the actual reading of the internal value of the register
        from the device. In `BaseDevice` the method doesn't do anything and
        subclasses should overwrite this mehtod to actually invoke the 
        buses' methods for reading information from the device.
        """
        pass


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
    def __init__(self, name, model, bus, dev_id):
        self.name = name
        self.bus = bus
        self.dev_id = dev_id
        self.registers = {}
        model_file = self.getModelPath(model)
        model_ini = readIniFile(model_file)
        for reginfo in model_ini['registers']:
            new_register = self.initRegister(reginfo)
            self.__dict__[reginfo['Name']] = new_register
            self.registers[reginfo['Name']] = new_register

    @classmethod
    def fromInfoDict(cls, devinfo, robot):
        bus = robot.buses[devinfo['Bus']]
        return cls(name=devinfo['Name'],
                   model=devinfo['Model'],
                   bus=bus,
                   dev_id=devinfo['Id'])

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
        return BaseRegister(device=self,
                            name=reginfo['Name'],
                            address=reginfo['Address'],
                            access=reginfo['Access'],
                            sync=reginfo['Sync'])

    def readRegisterList(self, reglist=[]):
        result = {}
        for regname in reglist:
            register = self.registers[regname]
            result[register.name] = register.read()
        return result

    def writeRegisterList(self, reglist=[]):
        result = {}
        for regname in reglist:
            register = self.registers[regname]
            if register.access != 'R':
                result[register.name] = register.write()
        return result

    def readAllRegisters(self):
        return self.readRegisterList(self.registers.keys())

    def writeAllRegisters(self):
        return self.writeRegisterList(self.registers.keys())

    def toDict(self):
        result = {}
        for regname, reg in self.registers.items():
            result[regname] = reg.value
        return result


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
            new_bus = self.initBus(businfo, self)
            self.buses[businfo['Name']] = new_bus
            self.__dict__[businfo['Name']] = new_bus
        # load the devices
        for devinfo in config['devices']:
            new_device = self.initDevice(devinfo, self)
            self.devices[devinfo['Name']] = new_device
            self.buses[devinfo['Bus']].devices.append(new_device)
            self.__dict__[devinfo['Name']] = new_device
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
        
    def initBus(self, businfo, robot):
        """BaseRobot only knows BaseBus and this default method
        will allocate one. Subclasses should override this method and
        implement allocation for all the device classes they use.
        """
        if businfo['Class'] == 'BaseBus':
            return BaseBus.fromInfoDict(businfo)
        else:
            raise KeyError('Unknown bus class name: {}'.format(businfo['Class']))

    def initDevice(self, devinfo, robot):
        if devinfo['Class'] == 'BaseDevice':
            return BaseDevice.fromInfoDict(devinfo, robot)
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