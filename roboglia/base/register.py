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
import inspect

from ..utils import check_type, check_options, check_not_empty
from .device import BaseDevice
from .sync import BaseSync

logger = logging.getLogger(__name__)


class BaseRegister():
    """A minimal representation of a device register.

    Parameters
    ----------
    name: str
        The name of the register

    device: BaseDevice or subclass
        The device where the register is attached to

    address: int (typpically but some devices might use other addressing)
        The register address

    size: int
        The register size in bytes; defaults to 1

    minim: int
        Minimum value represented in register in internal format; defaults to 0

    maxim: int
        Maximum value represented in register; defaults to 2^size - 1.
        The setter method for internal value will check that the desired
        value is within the [min, max] and trim it accordingly

    access: str
        Read ('R') or read-write ('RW'); default 'R'

    sync: bool
        ``True`` if the register will be updated from the real device
        using a sync loop. If `sync` is ``False`` access to the register
        through the value property will invoke reading / writing to the real
        register; default ``False``

    word: bool
        Indicates that the register is a ``word`` register (16 bits) instead
        of a usual 8 bits. Some I2C and SPI devices use 16bit registers
        and need to use separate access functions to read them as opposed to
        the 8 bit registers. Default is ``False`` which effectively makes it
        an 8 bit register

    order: ``LH`` or ``HL``
        Applicable only for registers with size > 1 that represent a value
        over succesive internal registers, but for convenience are groupped
        as one single register with size 2 (or higher).
        ``LH`` means low-high and indicates the bytes in the registry are
        organized starting with the low byte first. ``HL`` indicates that
        the registers are with the high byte first. Technically the ``read``
        and ``write`` functions always read the bytes in the order they
        are stored in the device and if the register is marked as ``HL`` the
        list is reversed before being returned to the requester or processed
        as a number in case the ``bulk`` is ``False``. Default is ``LH``.

    default: int
        The default value for the register; implicit 0

    """
    def __init__(self, name='REGISTER', device=None, address=0, size=1,
                 minim=0, maxim=None, access='R', sync=False, word=False,
                 bulk=True, order='LH', default=0, **kwargs):
        # these are already checked by the device
        self.__name = name
        # device
        check_not_empty(device, 'device', 'register', self.name, logger)
        check_type(device, BaseDevice, 'register', self.name, logger)
        self.__device = device
        # address
        # check_not_empty(address, 'address', 'register', self.name, logger)
        self.__address = address
        # size
        check_not_empty(size, 'size', 'register', self.name, logger)
        check_type(size, int, 'register', self.name, logger)
        self.__size = size
        # minim
        check_type(minim, int, 'register', self.name, logger)
        self.__minim = minim
        # maxim
        if maxim:
            check_type(maxim, int, 'register', self.name, logger)
            self.__maxim = maxim
        else:
            self.__maxim = pow(2, self.size * 8) - 1
        # access
        check_options(access, ['R', 'RW'], 'register', self.name, logger)
        self.__access = access
        # sync
        check_options(sync, [True, False], 'register', self.name, logger)
        self.__sync = sync
        # word
        check_options(word, [True, False], 'register', self.name, logger)
        self.__word = word
        # bulk
        check_options(bulk, [True, False], 'register', self.name, logger)
        self.__bulk = bulk
        # order
        check_options(order, ['LH', 'HL'], 'register', self.name, logger)
        self.__order = order
        # default
        check_type(default, int, 'register', self.name, logger)
        self.__default = default
        self.__int_value = self.default

    @property
    def name(self):
        """Register's name."""
        return self.__name

    @property
    def device(self):
        """The device the register belongs to."""
        return self.__device

    @property
    def address(self):
        """The register's address in the device."""
        return self.__address

    @property
    def size(self):
        """The regster's size in Bytes."""
        return self.__size

    @property
    def minim(self):
        """The register's minimum value in internal format."""
        return self.__minim

    @property
    def maxim(self):
        """The register's maximum value in internal format."""
        return self.__maxim

    @property
    def range(self):
        """Tuple with (minim, maxim) values in internal format."""
        return (self.__minim, self.__maxim)

    @property
    def min_ext(self):
        """The register's minimum value in external format."""
        return self.value_to_external(self.minim)

    @property
    def max_ext(self):
        """The register's maximum value in external format."""
        return self.value_to_external(self.maxim)

    @property
    def range_ext(self):
        """Tuple with (minim, maxim) values in external format."""
        return (self.min_ext, self.max_ext)

    @property
    def access(self):
        """Register's access mode."""
        return self.__access

    @property
    def sync(self):
        """Register is subject to a sync loop update."""
        return self.__sync

    @sync.setter
    def sync(self, value):
        """Sets the register as being synced by a loop. Only subclasses
        of :py:class:`BaseSync` are allowed to do this change."""
        caller = inspect.stack()[1].frame.f_locals['self']
        if isinstance(caller, BaseSync):
            self.__sync = (value is True)
        else:
            logger.error('only BaseSync subclasses can chance the sync '
                         'flag of a register')

    @property
    def word(self):
        """Indicates if the register is an 16 bit register (``True``) or
        an 8 bit register.
        """
        return self.__word

    @property
    def order(self):
        """Indicates the order of the data representartion; low-high (LH)
        or high-low (HL)
        """
        return self.__order

    @property
    def default(self):
        """The register's default value in internal format."""
        return self.__default

    @property
    def int_value(self):
        """The internal value of the register."""
        return self.__int_value

    @int_value.setter
    def int_value(self, value):
        """Allows only :py:class:`BaseSync` derrived classes to set the values
        for the ``int_value``."""
        caller = inspect.stack()[1].frame.f_locals['self']
        if isinstance(caller, BaseSync):
            self.__int_value = value
        else:
            logger.error('only BaseSync subclasses can chance the '
                         'internal value ')

    def value_to_external(self, value):
        """Converts the presented value to external format according to
        register's settings. This method should be overridden by subclasses
        in case they have specific conversions to do.

        .. see also: :py:class:`BoolRegister`,
            :py:class:`RegisterWithConversion`,
            :py:class:`RegisterWithThreshold`

        Parameters
        ----------
        value: int
            A value (internal representation) to be converted.

        Returns
        -------
        int
            For ``BaseRegister`` it returns the same value unchanged.
        """
        return value

    def value_to_internal(self, value):
        """Converts the presented value to internal format according to
        register's settings. This method should be overridden by subclasses
        in case they have specific conversions to do.

        .. see also: :py:class:`BoolRegister`,
            :py:class:`RegisterWithConversion`,
            :py:class:`RegisterWithThreshold`

        Parameters
        ----------
        value: int
            A value (external representation) to be converted.

        Returns
        -------
        int
            For ``BaseRegister`` it returns the same value unchanged.
        """
        return value

    @property
    def value(self):
        """Provides the value of the register in external format. If the
        register is not marked for ``sync`` then it requests the device
        to perform a ``read`` in order to refresh the content of the
        register.

        Returns
        -------
        any
            The value of the register in the external format. It invokes
            :py:meth:`value_to_external` which can be overridden by
            subclasses to provide different representations of the register's
            value (hence the ``any`` return type).
        """
        if not self.sync:
            self.read()
        return self.value_to_external(self.int_value)

    @value.setter
    def value(self, value):
        """Updates the internal value of the register with a value provided
        in external format. It invokes the :py:meth:`value_to_internal`
        method to perform the conversion. If the register's ``sync`` is not
        ``True`` it will ask the device to initiate a ``write`` of the data
        to the device. The method also checks if the converted value sits in
        the allowed range defined by the ``minim`` and ``maxim`` attributes
        of the register before updating. If the register is with access 'R'
        (read-only) it will ignore the request and log a warning.

        Parameters
        ----------
        value: any
            The value in external format needed to be stored.
        """
        # trim according to min and max for the register
        if self.access != 'R':
            int_value = self.value_to_internal(value)
            self.__int_value = max(self.minim, min(self.maxim, int_value))
            if not self.sync:       # pragma: no branch
                # direct sync
                self.write()
        else:
            logging.warning(f'attempted to write in RO register {self.name} '
                            f'of device {self.device.name}')

    def write(self):
        """Performs the actual writing of the internal value of the register
        to the device. Calls the device's method to write the value of
        register.
        """
        self.device.write_register(self, self.int_value)

    def read(self):
        """Performs the actual reading of the internal value of the register
        from the device. Calls the device's method to read the value of
        register.
        """
        value = self.device.read_register(self)
        # only update the internal value if the read value from device
        # is not None
        # a value of None indicates that there was an issue with readind
        # the data from the device
        if value is not None:       # pragma: no branch
            self.__int_value = value

    def __str__(self):
        """Representation of the register [name]: value."""
        return f'[{self.name}]: {self.value} ({self.int_value})'


class BoolRegister(BaseRegister):
    """A register with BOOL representation (true/false).

    Inherits from :py:class:`BaseRegister` all methods and defaults ``max``
    to 1.
    Overrides `value_to_external` and `value_to_internal` to process
    a bool value.
    """
    def __init__(self, **kwargs):
        if 'maxim' in kwargs:           # pragma: no branch
            logger.warning('parameter "maxim" for BoolRegister ignored, '
                           'it will be defaulted to 1')
            del kwargs['maxim']
        super().__init__(maxim=1, **kwargs)

    def value_to_external(self, value):
        """The external representation of bool register.
        """
        return bool(value)

    def value_to_internal(self, value):
        """The internal representation of the register's value.
        """
        return int(value)


class RegisterWithConversion(BaseRegister):
    """A register with an external representation that is produced by
    using a linear transformation::

        external = (internal - offset) / factor
        internal = external * factor + offset

    The ``RegisterWithConversion`` inherits all the paramters from
    :py:class:`BaseRegister` and in addition includes the following
    specific parameters that are used when converting the data from internal
    to external format.

    Parameters
    ----------
    factor: float
        A factor used for conversion. Defaults to 1.0.

    offset: int
        The offset for the conversion; defaults to 0 (int)

    Raises:
        KeyError: if any of the mandatory fields are not provided
        ValueError: if value provided are wrong or the wrong type
    """
    def __init__(self, factor=1.0, offset=0, **kwargs):
        super().__init__(**kwargs)
        check_type(factor, float, 'register', self.name, logger)
        self.__factor = factor
        check_type(offset, int, 'register', self.name, logger)
        self.__offset = offset

    @property
    def factor(self):
        """The conversion factor for external value."""
        return self.__factor

    @property
    def offset(self):
        """The offset for external value."""
        return self.__offset

    def value_to_external(self, value):
        """
        The external representation of the register's value.

        Performs the translation of the value according to::

            external = (internal - offset) / factor

        """
        return (float(value) - self.offset) / self.factor

    def value_to_internal(self, value):
        """
        The internal representation of the register's value.

        Performs the translation of the value according to::

            internal = external * factor + offset

        The resulting value is rounded to produce an integer suitable
        to be stored in the register.
        """
        return round(float(value) * self.factor + self.offset)


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

    The ``RegisterWithThreshold`` inherits all the paramters from
    :py:class:`BaseRegister` and in addition includes the following
    specific parameters that are used when converting the data from internal
    to external format.

    Parameters
    ----------
    factor: float
        A factor used for conversion. Defaults to 1.0

    threshold: int
        A threshold that separates the positive from negative
        values. Must be supplied.

    Raises:
        KeyError: if any of the mandatory fields are not proviced
        ValueError: if value provided are wrong or the wrong type
    """
    def __init__(self, factor=1.0, threshold=None, **kwargs):
        super().__init__(**kwargs)
        check_type(factor, float, 'register', self.name, logger)
        self.__factor = factor
        check_not_empty(threshold, 'threshold', 'register', self.name, logger)
        check_type(threshold, int, 'register', self.name, logger)
        self.__threshold = threshold

    @property
    def factor(self):
        """Conversion factor."""
        return self.__factor

    @property
    def threshold(self):
        """The threshold for conversion."""
        return self.__threshold

    def value_to_external(self, value):
        """The external representation of the register's value.

        Performs the translation of the value according to::

            if value < threshold:
                external = value / factor
            else:
                external = (threshold - value) / factor
        """
        if value < self.threshold:
            return value / self.factor
        else:
            return (self.threshold - value) / self.factor

    def value_to_internal(self, value):
        """The internal representation of the register's value.

        Performs the translation of the value according to::

            if value > 0:
                internal = value * factor
            else:
                internal = (-value) * factor + threshold
        """
        if value >= 0:
            return value * self.factor
        else:
            return (-value) * self.factor + self.threshold
