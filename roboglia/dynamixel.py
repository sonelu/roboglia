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
from roboglia.base import BaseBus, BaseRegister, BaseDevice, BaseRobot
from dynamixel_sdk import PortHandler, PacketHandler
from serial import rs485
import os
from collections import namedtuple


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
    def __init__(self, name, port, 
                protocol=2.0, baudrate=1000000, rs485=False):
        super().__init__(name, port)
        self.protocol = protocol
        self.baudrate = baudrate
        self.rs485 = rs485
        self.portHandler = None
        self.packetHandler = None

        # assigned devices
        self.devices = []

    def open(self):
        self.portHandler = PortHandler(self.port)
        self.portHandler.setBaudRate(self.baudrate)
        if self.rs485:
            self.portHandler.ser.rs485_mode = rs485.RS485Settings()
        self.portHandler.openPort()

        self.packetHandler = PacketHandler(self.protocol)


    def close(self):
        self.packetHandler = None
        self.portHandler.closePort()
        self.portHandler = None

    def isOpen(self):
        return self.packetHandler != None

    def ping(self, dxl_id):
        return self.packetHandler.ping(self.portHandler, dxl_id)

    def broadcastPing(self):
        return self.packetHandler.broadcastPing(self.portHandler)

    def read1Byte(self, dxl_id, address):
        return self.packetHandler.read1ByteTxRx(self.portHandler, dxl_id, address)

    def read2Byte(self, dxl_id, address):
        return self.packetHandler.read2ByteTxRx(self.portHandler, dxl_id, address)

    def read4Byte(self, dxl_id, address):
        return self.packetHandler.read4ByteTxRx(self.portHandler, dxl_id, address)

    def write1Byte(self, dxl_id, address, value):
        return self.packetHandler.write1ByteTxRx(self.portHandler, dxl_id, address, value)

    def write2Byte(self, dxl_id, address, value):
        return self.packetHandler.write2ByteTxRx(self.portHandler, dxl_id, address, value)

    def write4Byte(self, dxl_id, address, value):
        return self.packetHandler.write4ByteTxRx(self.portHandler, dxl_id, address, value)


class DynamixelRegister(BaseRegister):

    def __init__(self, reginfo):
        super().__init__(reginfo)
        self.size = int(reginfo['Size'])
        self.memory = reginfo['Memory']
        self.min = int(reginfo['Min'])
        self.max = int(reginfo['Max'])
        self.dir = reginfo['Dir']
        self.ext_type = reginfo['Ext_type']
        self.ext_off = float(reginfo['Ext_off'])
        self.ext_fact = float(reginfo['Ext_fact'])

    def valueToExternal(self, value):
        intval = self.int_value
        if self.dir == 'Y' and intval > self.max:
            intval -= (self.max+1)
            sign = -1
        else:
            sign = 1
        external = (intval - self.ext_off ) * self.ext_fact * sign
        if self.ext_type == 'I':
            return int(external)
        elif self.ext_type == 'B':
            return external > 0
        else:
            return external

    def valueToInternal(self, value):
        if self.access == 'R':
            raise ValueError("DynamixelRegister: {} register is read-only")
        internal = round(value / self.ext_fact + self.ext_off)
        if internal < self.min or internal > self.max:
            raise ValueError("DynamixelRegister: internal value {} outside [{}:{}] range".format(internal, self.min, self.max))
        return internal


class DynamixelServo(BaseDevice):
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
    def getModelPath(self, model):
        return os.path.join(os.path.dirname(__file__), 'devices/dynamixel', model+'.device')

    def initRegister(self, reginfo):
        return DynamixelRegister(reginfo)

    def pullRegister(self, regname):
        if super().pullRegister(regname) == False:
            # some basic processing did not work
            return False
        else:
            reg = self.registers[regname]
            # pick the correct read method
            if reg.size == 1:
                function = self.bus.read1ByteTxRx
            if reg.size == 2:
                function = self.bus.read2ByteTxRx
            if reg.size == 4:
                function = self.bus.read4ByteTxRx
            # execute the method  
            rxpacket, result, _ = function(reg.dev_id, reg.address)
            if result != 0:
                return False
            else:
                reg.int_value = rxpacket
                return True

    def pushRegister(self, regname):
        if super().pushRegister(regname) == False:
            # some basic processing did not work
            return False
        else:
            reg = self.registers[regname]
            # pick the correct read method
            if reg.size == 1:
                function = self.bus.write1ByteTxRx
            if reg.size == 2:
                function = self.bus.write2ByteTxRx
            if reg.size == 4:
                function = self.bus.write4ByteTxRx
            # execute the method   
            result, _ = function(reg.dev_id, reg.address, reg.int_value)
            if result != 0:
                return False
            else:
                return True


class DynamixelRobot(BaseRobot):
    """This is a convenience class to be used for robots that only use
    Dynamixel servos.

    In principle complex robots use other types of buses and devices 
    and you should subclass `BaseRobot` and implement your own methods
    for initializing Bus and Device object, based on the classes you
    are using (including your own custom subclasses of buses and devices).
    """

    def processBus(self, businfo):
        if businfo['Class'] == 'DynamixelBus':
            new_bus = DynamixelBus(businfo['Name'], 
                                businfo['Port'], 
                                float(businfo['Protocol']), 
                                int(businfo['Baudrate']), 
                                businfo['RS485']=='Y')
            #new_bus.open()
            return new_bus
        else:
            return super().processBus(businfo)


    def processDevice(self, devinfo, bus):
        if devinfo['Class'] == 'DynamixelServo':
            return DynamixelServo(model=devinfo['Model'], 
                                  bus=bus, 
                                  dev_id=int(devinfo['Id']))
        else:
            return super().processDevice(devinfo, bus)