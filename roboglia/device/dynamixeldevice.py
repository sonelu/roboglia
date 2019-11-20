
import os
from collections import namedtuple

from roboglia.utils import readIniFile
from roboglia.device.basedevice import BaseDevice

# defintion of the parameters for a register in a Dynamnixel Servo
regparams = ['address',     # address of the register
             'size',        # size of register in bytes (typical 1,2 or 4)
             'name',        # name of the register; must not use whitespaces
             'description', # a long description for the register; free text
             'access',      # 'R' or 'RW' indicating read-only or read-write
             'memory',      # 'EEPROM' or 'RAM'; where is located
             'min',         # minimum value in internal format
             'max',         # maximum value in internal format
             'dir',         # register has an extra bit for direction
             'ext_type',    # external format of the register value ; 
                            # 'I' for integer, 'F' for float, 'B' for bool
             'ext_off',     # offset for converting from internal to external format
             'ext_fact']    # factor for converting from internal to external format
                            # converting the data is done as:
                            #     external = (internal - offset) * factor
                            #     internal = (external / factor + offset)
                            # allways the internal value is typecasted to int() while external
                            # value is typecasted depending on the ext_type

DynamixelRegister = namedtuple('DynamixelRegister', regparams)
"""A convenience representation of a Dynamixel register.

Implemented as a `namedtuple` so that the properties can be easily accessed
via dot notation (ex. `register.name`).

"""

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

    def processRegister(self, reginfo):
        return DynamixelRegister(
            address = int(reginfo['Address']),
            size = int(reginfo['Size']),
            name = reginfo['Name'],
            description = reginfo['Description'],
            access = reginfo['Access'],
            memory = reginfo['Memory'],
            min = int(reginfo['Min']),
            max = int(reginfo['Max']),
            dir = reginfo['Dir'],
            ext_type = reginfo['Ext_type'],
            ext_off = float(reginfo['Ext_off']),
            ext_fact = float(reginfo['Ext_fact'])
        )
        


    def __getattr__(self, attr):
        """Used to create assesors for register values.

        If the provided member is a name that exists in the `registers`
        dictionary it will return the value of that register.

        It performs a conversion from internal format (as storred in
        `values` dict) to output format (as indicated by the `ext_type`)
        using the offset (`ext_off`) and the factor (`ext_fact`).

        Returns
        -------
        int, float or bool
            The content of the register in external format.

        Raises
        ------
        AttributeError 
            If the member name is not in in the list of registers.

        """
        if attr in self.registers:
            reg = self.registers[attr]
            val = self.values[attr]
            if reg.dir == 'Y' and val > reg.max:
                val -= (reg.max+1)
                sign = -1
            else:
                sign = 1
            external = (val - reg.ext_off ) * reg.ext_fact * sign
            if reg.ext_type == 'I':
                return int(external)
            elif reg.ext_type == 'B':
                return external > 0
            else:
                return external
        else:
            raise AttributeError(f'{self.__class__.__name__}.{attr} is invalid.')

    def __setattr__(self, attr, value):
        """Used for setting values of registers.

        If the provided name is a register the method will try to update
        the value into the `values` dictionary by inviking the conversion
        external > internal::

            internal = external / factor + offset
        
        Parameters
        ----------
        attr : str
            THe name of the register. Normally passed when invoking
            `servo.register`.

        value : (int, float, bool)
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
                reg = self.registers[attr]
                if reg.access == 'R':
                    raise ValueError("attribute {} of DynamixelServo is read-only".format(attr))
                internal = round(float(value) / reg.ext_fact + reg.ext_off)
                if internal > reg.max or internal < reg.min:
                    raise ValueError("value {} outside allowed domain for attribute {}".format(value, attr))
                self.values[attr] = internal
            else:
                raise KeyError("attribute {} does not exist".format(attr))