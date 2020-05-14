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
import logging
from ..base import BaseRegister

logger = logging.getLogger(__name__)


class DynamixelAXBaudRateRegister(BaseRegister):
    """Implements a representation of a baud rate register for AX servos.

    Defaults `min` to 1 and `max` to 207 and implements the mapping
    between the internal number and the real baud rates.

    For AX Dynamixel the baud rate codes are:

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
    def __init__(self, **kwargs):
        if 'minim' in kwargs:           # pragma: no branch
            logger.warning('parameter "minim" for AXBaudRateRegister ignored, '
                           'it will be defaulted to 1')
            del kwargs['minim']
        if 'maxim' in kwargs:           # pragma: no branch
            logger.warning('parameter "maxim" for AXBaudRateRegister ignored, '
                           'it will be defaulted to 207')
            del kwargs['maxim']
        super().__init__(minim=1, maxim=207, **kwargs)

    def value_to_external(self, value):
        """Converts from the internal codes to external baud rate."""
        return {1: 1000000, 3: 500000, 4: 400000, 7: 250000,
                9: 200000, 16: 115200, 34: 57600, 103: 19200,
                207: 9600}.get(value, 0)

    def value_to_internal(self, value):
        """Converts valid baud rates to internal codes."""
        int_value = {1000000: 1, 500000: 3, 400000: 4, 250000: 7,
                     200000: 9, 115200: 16, 57600: 34, 19200: 103,
                     9600: 207}.get(int(value), None)
        if int_value is None:
            logger.error(f'attempt to write a non supported for AX baud '
                         f'rate: {value}; ignored')
            return self.int_value
        else:
            return int_value


class DynamixelAXComplianceSlopeRegister(BaseRegister):
    """Compliance slope for AX Devices is working in powers of 2 and
    this class performs the conversion between these representations.

    .. seealso::

        http://emanual.robotis.com/docs/en/dxl/ax/ax-12a/#cw-compliance-slope
    """
    def __init__(self, **kwargs):
        if 'maxim' in kwargs:           # pragma: no branch
            logger.warning('parameter "maxim" for '
                           'DynamixelAXComplianceSlopeRegister ignored, '
                           'it will be defaulted to 254')
            del kwargs['maxim']
        super().__init__(maxim=254, **kwargs)

    def value_to_external(self, value):
        """Computes the log in base 2 of the provided value and rounds it
        to the nearest integer."""
        return round(log(value, 2))

    def value_to_internal(self, value):
        """Computes the 2^value."""
        return pow(2, value)


class DynamixelXLBaudRateRegister(BaseRegister):
    """Implements a representation of a baud rate register for XL servos.

    Defaults `min` to 0 and `max` to 7 and implements the mapping
    between the internal number and the real baud rates.

    For XL Dynamixel the baud rate codes are:

    +------+-----------+
    | Code | Baud rate |
    +======+===========+
    | 3    |    1000000|
    | 2    |     115200|
    | 1    |      57600|
    | 0    |       9600|
    +------+-----------+
    """
    def __init__(self, **kwargs):
        if 'minim' in kwargs:           # pragma: no branch
            logger.warning('parameter "minim" for XLBaudRateRegister ignored, '
                           'it will be defaulted to 1')
            del kwargs['minim']
        if 'maxim' in kwargs:           # pragma: no branch
            logger.warning('parameter "maxim" for XLBaudRateRegister ignored, '
                           'it will be defaulted to 7')
            del kwargs['maxim']
        super().__init__(minim=0, maxim=7, **kwargs)

    def value_to_external(self, value):
        """Converts from the internal codes to external baud rate."""
        return {7: 4500000, 6: 4000000, 5: 3000000, 4: 2000000,
                3: 1000000, 2: 115200, 1: 57600,
                0: 9600}.get(value, 0)

    def value_to_internal(self, value):
        """Converts valid baud rates to internal codes."""
        int_value = {4500000: 7, 4000000: 6, 3000000: 5, 2000000: 4,
                     1000000: 3, 115200: 2, 57600: 1,
                     0: 9600}.get(int(value), None)

        if int_value is None:
            logger.error(f'attempt to write a non supported for XL baud '
                         f'rate: {value}; ignored')
            return self.int_value
        else:
            return int_value
