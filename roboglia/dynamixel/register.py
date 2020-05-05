# Copyright (C) 2020  Alex Sonea

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from math import log
from ..base import BaseRegister


class DynamixelAXBaudRateRegister(BaseRegister):
    """Implements a representation of a baud rate register for AX servos.

    Defaults `min` to 1 and `max` to 207 and implements the mapping
    between the internal number and the real baud rates.

    For AX Dynamixels the baud rate codes are:

    +------+-----------+
    | Code | Baud rate |
    +======+===========+
    | 1    |    1000000|
    | 3    |     500000|
    | 4    |     400000|
    | 7    |     250000|
    | 9    |     200000|
    | 16   |     115200|
    | 34   |      57600|
    | 103  |      19200|
    | 207  |       9600|
    +------+-----------+
    """
    def __init__(self, init_dict):
        init_dict['min'] = 1
        init_dict['max'] = 207
        super().__init__(init_dict)

    def value_to_external(self):
        """Converts from the internal codes to external baud rate."""
        return {1: 1000000, 3: 500000, 4: 400000, 7: 250000,
                9: 200000, 16: 115200, 34: 57600, 103: 19200,
                207: 9600}.get(super().value_to_external(), 0)

    def value_to_internal(self, value):
        """Converts valid baud rates to internal codes."""
        conv_value = {1000000: 1, 500000: 3, 400000: 4, 250000: 7,
                      200000: 9, 115200: 16, 57600: 34, 19200: 103,
                      9600: 207}.get(int(value), None)
        if conv_value is None:
            raise ValueError(f'{value} not supported for AX baud rate')
        super().value_to_internal(conv_value)

    value = property(value_to_external, value_to_internal)
    """Accessor for the register value. Calls the getter/setter methods
    to perform the conversions."""


class DynamixelAXComplianceSlopeRegister(BaseRegister):
    """Compliance slope for AX Devices is working in powers of 2 and
    this class performs the conversion between these representations.
    
    .. seealso::

        http://emanual.robotis.com/docs/en/dxl/ax/ax-12a/#cw-compliance-slope
    """
    def __init__(self, init_dict):
        init_dict['max'] = 254
        super().__init__(init_dict)

    def value_to_external(self):
        """Computes the log in base 2 of the provided value and rounds it
        to the nearest integer."""
        return round(log(super().value_to_external(), 2))

    def value_to_internal(self, value):
        """Computes the 2^value."""
        super().value_to_internal(pow(2, value))

    value = property(value_to_external, value_to_internal)
    """Accessor for the register value. Calls the getter/setter methods
    to perform the conversions."""