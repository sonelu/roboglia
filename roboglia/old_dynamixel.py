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
"""Module defining the Dynamixel specific bus and device.
"""
from roboglia.base import BaseBus, RegisterWithMinMax, \
                          RegisterWithExternalRepresentation, BaseDevice, \
                          BaseRobot, BaseGroup, BaseSync
from dynamixel_sdk import PortHandler, PacketHandler, \
                          GroupBulkRead, GroupBulkWrite, \
                          GroupSyncRead, GroupSyncWrite, \
                          DXL_LOBYTE, DXL_HIBYTE, DXL_LOWORD, DXL_HIWORD, \
                          COMM_SUCCESS
from serial import rs485
import os
from collections import namedtuple
from roboglia.utils import processParams, processList


class DynamixelBus(BaseBus):
    """A class for handling the communication on a Dynamixel bus.

    Parameters
    ----------

    name : str
        Identifier of the bus. Ex. `lower_body`.

    port : str
        The port name for communication. Ex. `/dev/ttyUB0`.

    protocol : (1.0, 2.0)
        Could be `1.0` or `2.0` indicating the two possible protocls 
        supported by the `dynamixel_sdk` communincation.

    baudrate : int
        Desired baudrate for the port.

    rs485 : bool
        Set to `True` if you need the port to be configured (software) in
        RS485 mode.
    """
    def __init__(self, parent, dictInfo):
        super().__init__(parent, dictInfo)
        params=processParams(dictInfo['Params'])
        self.baudrate = int(params['Baudrate'])
        if 'RS485' in params:
            self.rs485 = params['RS485'] =='Y'
        else:
            self.rs485 = False
        self.portHandler = None
        self.packetHandler1 = None
        self.packetHandler2 = None
        # assigned devices
        self.devices = []

    def open(self):
        self.portHandler = PortHandler(self.port)
        self.portHandler.setBaudRate(self.baudrate)
        if self.rs485:
            self.portHandler.ser.rs485_mode = rs485.RS485Settings()
        self.portHandler.openPort()

        self.packetHandler1 = PacketHandler(1.0)
        self.packetHandler2 = PacketHandler(2.0)

    def close(self):
        self.packetHandler1 = None
        self.packetHandler2 = None
        self.portHandler.closePort()
        self.portHandler = None

    def isOpen(self):
        return self.portHandler != None

    def packetHandler(self, protocol):
        return self.packetHandler1 if protocol==1.0 else self.packetHandler2

    def ping(self, protocol, dxl_id):
        return self.packetHandler(protocol).ping(dxl_id)

    def broadcastPing(self, protocol):
        return self.packetHandler(protocol).broadcastPing(self.portHandler)

    def read1Byte(self, protocol, dxl_id, address):
        return self.packetHandler(protocol).read1ByteTxRx(self.portHandler, dxl_id, address)

    def read2Byte(self, protocol, dxl_id, address):
        return self.packetHandler(protocol).read2ByteTxRx(self.portHandler, dxl_id, address)

    def read4Byte(self, protocol, dxl_id, address):
        return self.packetHandler(protocol).read4ByteTxRx(self.portHandler, dxl_id, address)

    def write1Byte(self, protocol, dxl_id, address, value):
        return self.packetHandler(protocol).write1ByteTxRx(self.portHandler, dxl_id, address, value)

    def write2Byte(self, protocol, dxl_id, address, value):
        return self.packetHandler(protocol).write2ByteTxRx(self.portHandler, dxl_id, address, value)

    def write4Byte(self, protocol, dxl_id, address, value):
        return self.packetHandler(protocol).write4ByteTxRx(self.portHandler, dxl_id, address, value)


class DynamixelRegister(RegisterWithMinMax, RegisterWithExternalRepresentation):

    def __init__(self, parent, dictInfo):
        RegisterWithMinMax.__init__(self, parent, dictInfo)
        RegisterWithExternalRepresentation.__init__(self, parent, dictInfo)
        self.memory = dictInfo['Memory']
        self.dir = dictInfo['Dir']

    def read(self):
        device = self.parent
        bus = device.parent
        if self.size == 1:
            function = bus.read1Byte
        elif self.size == 2:
            function = bus.read2Byte
        else:
            function = bus.read4Byte
        rxpacket, result, error = function(device.protocol,
                                           device.dev_id,
                                           self.address)
        if result != 0 or error !=0:
            return False
        else:
            self._int_value = int(rxpacket)
            return True

    def write(self):
        device = self.parent
        bus = device.parent
        if self.size == 1:
            function = bus.write1Byte
        elif self.size == 2:
            function = bus.write2Byte
        else:
            function = bus.write4Byte
        result, error = function(device.protocol,
                                 device.dev_id, 
                                 self.address, 
                                 self._int_value)
        return result == 0 and error == 0


class DynamixelDevice(BaseDevice):
    """Convenience class for interacting with a Dynamixel servo.

    DynamixelServo represents the structure of the registers defined for 
    a given Dyamixel type. The structure is read from a `.device` file that 
    has a predefined column layout. See the provided descriptions included 
    in the `device/dynamixel/` directory.
    
    Parameters
    ----------
    model : str
        String, the type of the Dynamixel servo that needs to be created; 
        a file with the same name and extension .device needs to be 
        available in the directory `devices/dynamixel` otherwise there will 
        be an exception thrown.

    Attributes
    ----------
    registers : dict of DynamixelRegister
        Is a dictionary of DynamixelRegister() with key the register name 
        containing the imutable characteristicts of the register: address, 
        size, name, description, access, min value, max value, memory 
        location ('EEPROM' or 'RAM'), external type representation ('I' for 
        integer or 'F' for float, 'B' for bool), the offset and the factor 
        for converting the internal values to external values. These last 
        parameters are used to convert from technical internal formats to 
        formats that have a functional meaning, for example the position 
        of the servo in radians. These conversions are performed as::

            external = (internal - offset) * factor
            internal = external / factor + offset
        
        For example if internally the position is refected as a 2 Byte 
        number in the range 0 - 1023 with 512 indicating the center and the
        range of the servo is -150° to 150° (300° range) we could use the 
        following values::

            offset = 512
            factor = 0.293255132
        
        A value of 256 in the internal registry will represent::

            external = (256 - 512 ) * 0.293255132 ≈ -75.07°

        Similarly setting a 30° value would be::

            internal = 30 / 0.293255132 + 512 = 614 

        (this is rounded to the nearest integer as only ints can be storred 
        in the registry)

    values : Dict of int
        This is a dictionary with the actual register values with key
        the register value; it is not recommended to 
        access the information in this dictionary directly. Instead you 
        should use the the accessors implemented by the class automatically 
        for each register name. For instance if you have a register that 
        contains the present postion, named `present_postion` you can access 
        the value by: `pos = servo.present_position`.
        In addition to the convenience (you can access all registers) the
        getter methods perform the conversion from internal to external 
        formats as explaied above.
        Similar, setter methods allow you to set the value of the register 
        by performing the conversion exeternal > internal format. In 
        addition the setter methods will raise ValueError if the register is 
        read-only ('R' in `access` attribute) or outside the ranges defined 
        by the min and max attributes.
        Also, please note that the values read or written in the `values` 
        dictionary are only reflecting this surrogate representation of the 
        servo. A sync loop is necessary to synchronize the values from the 
        DynamixelServo to the actual physical servo. Keep in mind that 
        values changed in registers that are not included in a sync loop 
        will not reflect the real values existing in the physical servo. 

    """
    def __init__(self, parent, dictInfo):
        super().__init__(parent, dictInfo)
        params = processParams(devinfo['Params'])
        self.protocol=params['Protocol']    

    def getModelPath(self, model):
        return os.path.join(os.path.dirname(__file__), 'devices/dynamixel', model+'.device')

    def initRegister(self, reginfo):
        if reginfo['Class'] == 'DynamixelRegister':
            return I2CRegister(parent=self, dictInfo = reginfo)
        else:
            return super.initRegister(reginfo)
        return DynamixelRegister(device=self,
                                 name=reginfo['Name'],
                                 address=int(reginfo['Address']),
                                 access=reginfo['Access'],
                                 sync=reginfo['Sync'],
                                 size=int(reginfo['Size']),
                                 memory=reginfo['Memory'],
                                 min=int(reginfo['Min']),
                                 max=int(reginfo['Max']),
                                 dir=reginfo['Dir'],
                                 ext_type=reginfo['Ext_type'],
                                 ext_off=float(reginfo['Ext_off']),
                                 ext_fact=float(reginfo['Ext_fact']))



class DynamixelGroup(BaseGroup):

    def __init__(self, devlist, subgrouplist):
        super().__init__(devlist, subgrouplist)
        if len(self.items) > 0:
            protocol = self.items[0].protocol
            for device in self.items:
                if device.protocol != protocol:
                    raise ValueError("groups of dynamixel devices must have the same protocol")


class DynamixelSync(BaseSync):

    def __init__(self, devlist, regnamelist):
        # save the details
        self.devlist = devlist
        self.regnamelist = regnamelist
        self.port = devlist[0].bus.portHandler
        self.ph = devlist[0].bus.packetHandler(devlist[0].protocol)
        firstReg = getattr(devlist[0], regnamelist[0])
        lastReg = getattr(devlist[0], regnamelist[-1])
        self.addrStart = firstReg.address
        self.addrLen = lastReg.address + lastReg.size - firstReg.address

    @classmethod
    def fromInfoDict(cls, syncinfo, robot):
        identifiers = processList(syncinfo['Devices'])
        devices = robot.devicesFromMixedList(identifiers)
        bus = robot.buses[syncinfo['Bus']]
        # filter devices for the sync's bus
        selectedDevices = [device for device in devices if device.bus==bus]
        if len(selectedDevices) == 0:
            raise ValueError('Device list is empty for sync: {}'.format(syncinfo['Name']))
        # check if all devices have the same protocol
        protocol = selectedDevices[0].protocol
        for device in selectedDevices:
            if device.protocol != protocol:
                raise ValueError('Devices in sync {} must have the same protocol'.format(syncinfo['Name']))
        regnames = processList(syncinfo['Registers'])
        return cls(selectedDevices, regnames)

    def makeBuffer(self, device, regnamelist):
        buffer = bytearray(self.addrLen)
        for regname in regnamelist:
            reg = getattr(device, regname)
            if reg.size == 1:
                buffer[reg.address-self.addrStart] = reg.int_value
            elif reg.size == 2:
                buffer[reg.address-self.addrStart] = DXL_LOBYTE(reg.int_value)
                buffer[reg.address-self.addrStart+1] = DXL_HIWORD(reg.int_value)
            elif reg.size == 4:
                buffer[reg.address-self.addrStart] = DXL_LOWORD(DXL_LOBYTE(reg.int_value))
                buffer[reg.address-self.addrStart+1] = DXL_LOWORD(DXL_HIWORD(reg.int_value))
                buffer[reg.address-self.addrStart+2] = DXL_HIWORD(DXL_LOBYTE(reg.int_value))
                buffer[reg.address-self.addrStart+3] = DXL_HIWORD(DXL_HIWORD(reg.int_value))
        return buffer


class DynamixelBulkRead(DynamixelSync):

    def __init__(self, devlist, regnamelist):
        super().__init__(devlist, regnamelist)
        # allocate GroupBulkRead
        self.gbr = GroupBulkRead(self.port, self.ph)
        for device in devlist:
            res = self.gbr.addParam(device.dev_id, self.addrStart, self.addrLen)
            if res != True:
                raise ValueError("addParam failed for BulkRead for ID: {}".format(device.dev_id))

    def run(self):
        res = self.gbr.txRxPacket()
        if res != COMM_SUCCESS:
            raise IOError("BulkRead txRxPacket() failed")
        for device in self.devlist:
            for regname in self.regnamelist:
                reg = getattr(device, regname)
                if self.gbr.isAvailable(device.dev_id, reg.address, reg.size):
                    reg.int_value = self.gbr.getData(device.dev_id, reg.address, reg.size)
                else:
                    raise IOError("BulkRead getData failed for ID {} and register {}".format(device.dev_id, regname))


class DynamixelBulkWrite(DynamixelSync):

    def __init__(self, devlist, regnamelist):
        super().__init__(devlist, regnamelist)
        if devlist[0].protocol == 1.0:
            raise ValueError("BulkWrite not supported for protocol 1.0; use SyncWrite instead")
        # allocate GroupBulkWrite
        self.gbw = GroupBulkWrite(self.port, self.ph)

    def run(self):
        for device in self.devlist:
            buffer = self.makeBuffer(device, self.regnamelist)
            res = self.gbw.addParam(device.dev_id, self.addrStart, self.addrLen, buffer)
            if res != True:
                raise ValueError("addParam failed for BulkWrite for ID: {}".format(device.dev_id))
        res = self.gbw.txPacket()
        if res != COMM_SUCCESS:
            raise IOError("BulkWrite failed in txPacket()")
        self.gbw.clearParam()


class DynamixelSyncRead(DynamixelSync):

    def __init__(self, devlist, regnamelist):
        super().__init__(devlist, regnamelist)
        if devlist[0].protocol == 1.0:
            raise ValueError("SyncRead not supported for protocol 1.0; use BulkRead instead")
        # allocate GroupSyncRead
        self.gsr = GroupSyncRead(self.port, self.ph, self.addrStart, self.addrLen)
        for device in devlist:
            res = self.gsr.addParam(device.dev_id)
            if res != True:
                raise ValueError("addParam failed for SyncRead for ID: {}".format(device.dev_id))

    def run(self):
        res = self.gsr.txRxPacket()
        if res != COMM_SUCCESS:
            raise IOError("BulkRead txRxPacket() failed")
        for device in self.devlist:
            for regname in self.regnamelist:
                reg = getattr(device, regname)
                if self.gsr.isAvailable(device.dev_id, reg.address, reg.size):
                    reg.int_value = self.gsr.getData(device.dev_id, reg.address, reg.size)
                else:
                    raise IOError("SyncRead getData failed for ID {} and register {}".format(device.dev_id, regname))


class DynamixelSyncWrite(DynamixelSync):

    def __init__(self, devlist, regnamelist):
        super().__init__(devlist, regnamelist)
        # allocate GroupSyncWrite
        self.gsw = GroupSyncWrite(self.port, self.ph, self.addrStart, self.addrLen)

    def run(self):
        for device in self.devlist:
            buffer = self.makeBuffer(device, self.regnamelist)
            res = self.gsw.addParam(device.dev_id, buffer)
            if res != True:
                raise ValueError("addParam failed for SyncWrite for ID: {}".format(device.dev_id))
        res = self.gsw.txPacket()
        if res != COMM_SUCCESS:
            raise IOError("SyncWrite failed in txPacket()")
        self.gsw.clearParam()


class DynamixelRobot(BaseRobot):
    """This is a convenience class to be used for robots that only use
    Dynamixel servos.

    In principle complex robots use other types of buses and devices 
    and you should subclass `BaseRobot` and implement your own methods
    for initializing Bus and Device object, based on the classes you
    are using (including your own custom subclasses of buses and devices).
    """

    def initBus(self, businfo, robot):
        if businfo['Class'] == 'DynamixelBus':
            return DynamixelBus.fromInfoDict(businfo)
        else:
            return super().initBus(businfo, robot)

    def initDevice(self, devinfo, robot):
        if devinfo['Class'] == 'DynamixelDevice':
            return DynamixelDevice.fromInfoDict(devinfo, robot)
        else:
            return super().initDevice(devinfo, robot)

    def initGroup(self, groupinfo, robot):
        if groupinfo['Class'] == 'DynamixelGroup':
            return DynamixelGroup.fromInfoDict(groupinfo, robot)
        else:
            return super().initGroup(groupinfo, robot)

    def initSync(self, syncinfo, robot):
        if syncinfo['Class'] == 'DynamixelBulkRead':
            return DynamixelBulkRead.fromInfoDict(syncinfo, robot)
        elif syncinfo['Class'] == 'DynamixelBulkWrite':
            return DynamixelBulkWrite.fromInfoDict(syncinfo, robot)
        elif syncinfo['Class'] == 'DynamixelSyncRead':
            return DynamixelSyncRead.fromInfoDict(syncinfo, robot)
        elif syncinfo['Class'] == 'DynamixelSyncWrite':
            return DynamixelSyncWrite.fromInfoDict(syncinfo, robot)
        else:
            return super().initSync(syncinfo, robot)
