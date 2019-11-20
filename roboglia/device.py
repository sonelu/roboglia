import os
from roboglia.utils import readIniFile
from collections import namedtuple

# defintion of the parameters for a register in a Dynamnixel Servo
regparams = ['address',     # address of the register
             'size',        # size of the data represented in the register in bytes (typical 1,2 or 4)
             'name',        # name of the register; must not use whitespaces
             'description', # a long description for the register; free text
             'access',      # 'R' or 'RW' indicating read-only or read-write access
             'memory',      # 'EEPROM' or 'RAM' indicating where the register is located
             'min',         # minimum value that can be stored in the register in internal format
             'max',         # maximum value that can be stored in the register in internal format
             'ext_type',    # external format of the register value ; 'I' for integer, 'F' for float
             'ext_off',     # offset for converting from internal to external format
             'ext_fact']    # factor for converting from internal to external format
                            # converting the data is done as:
                            #     external = (internal - offset) * factor
                            #     internal = (external / factor + offset)
                            # allways the internal value is typecasted to int() while external
                            # value is typecasted depending on the ext_type

DynamixelRegister = namedtuple('DynamixelRegister', regparams)

class DynamixelServo():
    """Convenience class for interacting with a Dynamixel servo.

    DynamixelServo represents the structure of the registers defined for a given Dyamixel type.
    The structure is read from a `.device` file that has a predefined column layout. See the
    provided descriptions included in the `device/dynamixel/` directory.
    
    Arguments:
        model: String, the type of the Dynamixel servo that needs to be created; a file
            with the same name and extension .device needs to be available in the directory
            `devices/dynamixel` otherwise there will be an exception thrown.

    Properties:
        registers: Dict of DynamixelRegister() with key the register name containing the
            imutable characteristicts of the register: address, size, name, description, 
            access, min value, max value, memory location ('EEPROM' or 'RAM'), external
            type representation ('I' for integer or 'F' for float), the offset and the 
            factor for converting the internal values to external values. These last 
            parameters are used to convert from technical internal formats to formats
            that have a functional meaning, for example the position of the servo in
            radians. These conversions are performed as:
                external = (internal - offset) * factor
                internal = external / factor + offset
            For example if internally the position is refected as a 2 Byte number in
            the range 0 - 1023 with 512 indicating the center and the range of the servo
            is -150º to 150º (300º range) we could use the following
            values:
                offset = 512
                factor = 0.293255132
            A value of 256 in the internal registry will represent:
                external = (256 - 512 ) * 0.293255132 ≈ -75.07º
            Similarly setting a 30º value would be:
                internal = 30 / 0.293255132 + 512 = 614 (this is rounded to the nearest
                                                         integer as only ints can be
                                                         storred in the registry)
        values: Dict of ints with key the register value; it is not recommended to 
            access the information in this dictionary directly. Instead you should
            use the the accessors implemented by the class automatically for each
            register name. For instance if you have a register that contains the
            present postion, named `present_postion` you can access the value by:
                `pos = servo.present_position`
            In addition to the convenience (you can access all registers) the
            getter methods perform the conversion from internal to external formats
            as explaied above.
            Similar, setter methods allow you to set the value of the register by
            performing the conversion exeternal > internal format. In addition the
            setter methods will raise ValueError if the register is read-only ('R'
            in `access` attribute) or outside the ranges defined by the min and
            max attributes.
            Also, please note that the values read or written in the `values` dictionary
            are only reflecting this surrogate representation of the servo. A sync
            loop is necessary to synchronize the values from the DynamixelServo 
            to the actual physical servo. Keep in mind that values changed in
            registers that are not included in a sync loop will not reflect the real
            values existing in the physical servo. 
    """
    def __init__(self, model):
        path = os.path.join(os.path.dirname(__file__), 'devices/dynamixel', model+'.device')
        config = readIniFile(path)
        self.registers = {}
        self.values = {}
        for reginfo in config['registers']:
            register = DynamixelRegister(address=int(reginfo['Address']),
                                         size=int(reginfo['Size']),
                                         name=reginfo['Name'],
                                         description=reginfo['Description'],
                                         access=reginfo['Access'],
                                         memory=reginfo['Memory'],
                                         min=int(reginfo['Min']),
                                         max=int(reginfo['Max']),
                                         ext_type=reginfo['Ext_type'],
                                         ext_off=float(reginfo['Ext_off']),
                                         ext_fact=float(reginfo['Ext_fact']))
            self.registers[register.name] = register
            self.values[register.name] = 0

    def __getattr__(self, attr):
        if attr in self.registers:
            reg = self.registers[attr]
            external = (self.values[attr] - reg.ext_off ) * reg.ext_fact
            if reg.ext_type == 'I':
                return int(external)
            else:
                return external
        else:
            raise AttributeError(f'{self.__class__.__name__}.{attr} is invalid.')

    def __setattr__(self, attr, value):
        if attr == 'registers' or attr=='values':
            super().__setattr__(attr, value)
        else:
            if attr in self.registers:
                reg = self.registers[attr]
                if reg.access == 'R':
                    raise ValueError("attribute {} of DynamixelServo is read-only".format(attr))
                internal = round(float(value) / reg.ext_fact + reg.ext_off)
                if internal > reg.max or internal < reg.min:
                    raise ValueError("value {} outside allowed domain for attribute {}".format(value, attr))
                self.values[attr] = internal
            else:
                raise KeyError("attribute {} does not exist".format(attr))