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

import logging

from ..utils import check_key, check_type, check_options

logger = logging.getLogger(__name__)


class BaseRegister():
    """A minimal representation of a device register.

    The `init_dict` must contain the following information, otherwise
    a `KeyError` will be thrown:

    Args:
        init_dict (dict): The dictionary used to initialize the register.

    The following keys are expected in the dictionary:

    - ``name``: the name of the register
    - ``device``: the device where the register is attached to
    - ``address``: the register address

    Optionally the following items can be provided or will be defaulted:

    - ``size``: the register size in bytes; defaults to 1
    - ``min``: min value represented in register; defaults to 0
    - ``max``: max value represented in register; defaults to 2^size - 1
        the setter method will check that the desired value is within the
        [min, max] and trim it accordingly
    - ``access``: read ('R') or read-write ('RW'); default 'R'
    - ``sync``: True if the register will be updated from the real device
        using a sync loop. If `sync` is False access to the register through
        the value property will invoke reading / writing to the real register;
        default 'False'
    - ``default``: the default value for the register; implicit 0

    """
    def __init__(self, init_dict):
        # these are already checked by the device
        self.name = init_dict['name']
        self.device = init_dict['device']
        check_key('address', init_dict, 'register', self.name, logger)
        self.address = init_dict['address']
        # optionals
        self.size = init_dict.get('size', 1)
        check_type(self.size, int, 'register', self.name, logger)
        self.min = init_dict.get('min', 0)
        check_type(self.min, int, 'register', self.name, logger)
        self.max = init_dict.get('max', pow(2, self.size * 8) - 1)
        check_type(self.max, int, 'register', self.name, logger)
        self.access = init_dict.get('access', 'R')
        check_options(self.access, ['R', 'RW'], 'register', self.name, logger)
        self.sync = init_dict.get('sync', False)
        check_options(self.sync, [True, False], 'register', self.name, logger)
        self.default = init_dict.get('default', 0)
        check_type(self.default, int, 'register', self.name, logger)
        self.int_value = self.default

    def value_to_external(self):
        """
        The external representation of the register's value.

        The method will return external representation of the register.
        If the register is not flagged as a sync registry it will also
        try to invoke the `read()` method of the register to
        get the most up to date value.
        """
        if not self.sync:
            self.read()
        return self.int_value

    def value_to_internal(self, value):
        """Updates the internal representation of the register's value.

        It will trim the received value to the [min, max]
        range before saving it in the `int_value` attribute. If the register
        is not synced (`sync` is `False`) it will also invoke the `write`
        method to write the content to the device.
        """
        # trim according to min and max for the register
        if self.access != 'R':
            self.int_value = max(self.min, min(self.max, value))
            if not self.sync:       # pragma: no branch
                # direct sync
                self.write()
        else:
            logging.warning(f'attempted to write in RO register {self.name} '
                            f'of device {self.device.name}')

    value = property(value_to_external, value_to_internal)

    def write(self):
        """Performs the actual writing of the internal value of the register
        to the device. Calls the device's method to write the value of
        register.
        """
        self.device.write_register(self, self.int_value)

    def read(self):
        """Performs the actual reading of the internal value of the register
        from the device. In `BaseDevice` the method doesn't do anything and
        subclasses should overwrite this mehtod to actually invoke the
        buses' methods for reading information from the device.
        """
        value = self.device.read_register(self)
        # only update the internal value if the read value from device
        # is not None
        # a value of None indicates that there was an issue with readind
        # the data from the device
        if value is not None:       # pragma: no branch
            self.int_value = value

    def __str__(self):
        """Representation of the register [name]: value."""
        return f'[{self.name}]: {self.value} ({self.int_value})'


class BoolRegister(BaseRegister):
    """A register with BOOL representation (true/false).

    Inherits from `BaseRegister` all methods and defaults `max` to 1.
    Overrides `value_to_external` and `value_to_internal` to process
    a bool value.
    `value` property is updated to use the new setter / getter methods.
    """
    def __init__(self, init_dict):
        init_dict['max'] = 1
        super().__init__(init_dict)

    def value_to_external(self):
        """The external representation of the register's value.

        Perform conversion to bool on top of the inherited method.
        """
        return bool(super().value_to_external())

    def value_to_internal(self, value):
        """The internal representation of the register's value.

        Perform conversion to bool on top of the inherited method.
        """
        super().value_to_internal(bool(value))

    value = property(value_to_external, value_to_internal)


class RegisterWithConversion(BaseRegister):
    """A register with an external representation that is produced by
    using a linear transformation::

        external = (internal - offset) / factor
        internal = external * factor + offset

    Args:
        init_dict (dict): The dictionary used to initialize the register.

    In addition to the fields used in :py:class:`BaseRegister`, the following
    keys are expected in the dictionary:

    - ``factor``: a factor used for conversion (float)

    Optionally the following items can be provided or will be defaulted:

    - ``offset``: the offset; defaults to 0 (int)

    Raises:
        KeyError: if any of the mandatory fields are not proviced
        ValueError: if value provided are wrong or the wrong type
    """
    def __init__(self, init_dict):
        super().__init__(init_dict)
        check_options('factor', init_dict, 'register', self.name, logger)
        self.factor = init_dict['factor']
        check_type(self.factor, float, 'register', self.name, logger)
        self.offset = init_dict.get('offset', 0)
        check_type(self.offset, int, 'register', self.name, logger)

    def value_to_external(self):
        """
        The external representation of the register's value.

        Performs the translation of the value after calling the inherited
        method.
        """
        return (float(super().value_to_external()) - self.offset) / self.factor

    def value_to_internal(self, value):
        """
        The internal representation of the register's value.

        Performs the translation of the value before calling the inherited
        method.
        """
        value = round(float(value) * self.factor + self.offset)
        super().value_to_internal(value)

    value = property(value_to_external, value_to_internal)


class RegisterWithThreshold(BaseRegister):
    """A register with an external representation that is represented by
    a threshold between negative and positive values::

        if internal >= threshold:
            external = (internal - threshold) / factor
        else:
            external = - internal / factor

        and for conversion from external to internal:

        if external >= 0:
            internal = external * factor + threshold
        else:
            internal = - external * factor

    Args:
        init_dict (dict): The dictionary used to initialize the register.

    In addition to the fields used in :py:class:`BaseRegister`, the following
    keys are expected in the dictionary:

    - ``factor``: a factor used for conversion (float)
    - ``threshold``: a threshold that separates the positive from negative
      values (int)

    Raises:
        KeyError: if any of the mandatory fields are not proviced
        ValueError: if value provided are wrong or the wrong type
    """
    def __init__(self, init_dict):
        super().__init__(init_dict)
        check_key('factor', init_dict, 'register', self.name, logger)
        self.factor = init_dict['factor']
        check_type(self.factor, float, 'register', self.name, logger)
        check_key('threshold', init_dict, 'register', self.name, logger)
        self.threshold = init_dict['threshold']
        check_type(self.threshold, int, 'register', self.name, logger)

    def value_to_external(self):
        """The external representation of the register's value.

        Performs the translation of the value after calling the inherited
        method.
        """
        value = super().value_to_external()
        if value < self.threshold:
            return value / self.factor
        else:
            return (self.threshold - value) / self.factor

    def value_to_internal(self, value):
        """The internal representation of the register's value.

        Performs the translation of the value before calling the inherited
        method.
        """
        if value >= 0:
            value = value * self.factor
        else:
            value = (-value) * self.factor + self.threshold
        super().value_to_internal(round(value))

    value = property(value_to_external, value_to_internal)
