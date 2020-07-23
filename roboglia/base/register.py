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

    clone: BaseRegister or subclass or ``None``
        Indicates if the register is a clone; this value provides the
        reference to the register object that acts as the main register
        in interation with the communication bus. This allows you to define
        multiple represtnations of the same physical register (at a given
        address) with the purpose of having different external
        representations. For example:

        - you can have a position register that can provide the external
          value in degrees or radians,
        - a velocity register that can provide the external value in degrees
          per second, radians per second or rotations per minute,
        - a byte register that reads 8 inputs and mask them each as a
          :py:class:`BoolRegister` with a different bit mask

        In the device definition YAML file use ``True`` to indicate if a
        register is a clone. The device constructor will replace the reference
        of the main register with the same address in the constructor of this
        register.

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
        over successive internal registers, but for convenience are groupped
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
    def __init__(self, name='REGISTER', device=None, address=0, clone=None,
                 size=1, minim=0, maxim=None, access='R', sync=False,
                 word=False, bulk=True, order='LH', default=0, **kwargs):
        # these are already checked by the device
        self.__name = name
        # device
        check_not_empty(device, 'device', 'register', self.name, logger)
        check_type(device, BaseDevice, 'register', self.name, logger)
        self.__device = device
        # address
        if address != 0:
            check_not_empty(address, 'address', 'register', self.name, logger)
        self.__address = address
        # clone
        if clone:
            check_type(clone, BaseRegister, 'register', self.name, logger)
        self.__clone = clone
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
    def clone(self):
        """Indicates the register is a clone of another."""
        return self.__clone

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
        if self.clone:
            return self.clone.sync
        return self.__sync

    @sync.setter
    def sync(self, value):
        """Sets the register as being synced by a loop. Only subclasses
        of :py:class:`BaseSync` are allowed to do this change."""
        caller = inspect.stack()[1].frame.f_locals['self']
        if isinstance(caller, (BaseSync, BaseRegister)):
            if self.clone:
                self.clone.sync = (value is True)
            else:
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
        if self.clone:
            return self.clone.default
        return self.__default

    @property
    def int_value(self):
        """Internal value of register, if a clone return the value of the
        main register."""
        if self.clone:
            return self.clone.int_value
        return self.__int_value

    @int_value.setter
    def int_value(self, value):
        """If clone, store the value in the main register."""
        if self.clone:
            self.clone.int_value = value
        else:
            self.__int_value = value

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
            self.int_value = max(self.minim, min(self.maxim, int_value))
            if not self.sync:       # pragma: no branch
                self.write()
        else:
            logging.warning(f'Attempted to write in RO register {self.name} '
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
            self.int_value = value

    def __str__(self):
        """Representation of the register [name]: value."""
        return f'[{self.name}]: {self.value} ({self.int_value})'


class BoolRegister(BaseRegister):
    """A register with BOOL representation (true/false).

    Inherits from :py:class:`BaseRegister` all methods.
    Overrides `value_to_external` and `value_to_internal` to process
    a bool value.

    Parameters
    ----------
    bits: int or ``None``
        An optional bit pattern to use in the determination of the output of
        the register. Default is None and in this case we simply compare the
        internal value with 0.

    mode: str ('all' or 'any')
        Indicates how the bit pattern should be used: 'all' means all the bits
        in the pattern must match  while 'any'
        means any bit that matches the pattern is enough to result in a
        ``True`` external value. Only used if bits is not ``None``. Default
        is 'any'.

    mask: int or ``None``
        An optional mask that allows for partial bit handling on the
        internal values. This mask permits handling only the specified bits
        without affecting the other ones in the internal value. For instance
        if the mask is 0b00001111 then the operations (setter, getter) will
        only affect the most significant 4 bits of the register.
    """
    def __init__(self, bits=None, mode='any', mask=None, **kwargs):
        super().__init__(**kwargs)
        if bits:
            check_type(bits, int, 'register', self.name, logger)
            check_options(mode, ['all', 'any'], 'register', self.name, logger)
            if mask:
                check_type(mask, int, 'register', self.name, logger)
        self.__bits = bits
        self.__mode = mode
        self.__mask = mask

    @property
    def bits(self):
        """The bit pattern used."""
        return self.__bits

    @property
    def mode(self):
        """The bitmasking mode ('all' or 'any')."""
        return self.__mode

    @property
    def mask(self):
        """The partial bitmask for the handling of the bits."""
        return self.__mask

    def value_to_external(self, value):
        """The external representation of bool register.
        """
        if self.bits is None:
            return bool(value)
        # this assumes that if a mask is used the bits in the ``bits``
        # attribute are all 0 already and we don't need to AND the ``mask``
        # with the bits
        if self.mode == 'any':
            return bool(value & self.bits)
        if self.mode == 'all':
            return (value & self.bits) == self.bits
        raise NotImplementedError

    def value_to_internal(self, value):
        """The internal representation of the register's value.
        """
        if not self.mask:
            # no mask used
            if not value:           # False
                ret = 0
            elif self.bits:         # True and bits
                ret = self.bits
            else:                   # True and no bits
                ret = 1
        else:
            # mask used
            # the int() below is to remove a linter error
            masked_int_value = self.int_value & (~ int(self.mask))
            if not value:           # False; reset
                # equivalent to reseting the bits
                ret = masked_int_value
            else:                   # True; set
                # setting the bits
                ret = self.bits | masked_int_value
        return ret


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

    sign_bit: int or None
        If a number is given it means that the register is "signed" and that
        bit represents the sign. Bits are numbered from 1 meaning that if
        ``sign_bit`` is 1 the less significant bit is used and if we have
        a 2 bytes register the most significant bit would be 16.
        The convention is that numbers having 0 in this bit are positive
        and the ones having 1 are negative numbers.

    Raises:
        KeyError: if any of the mandatory fields are not provided
        ValueError: if value provided are wrong or the wrong type
    """
    def __init__(self, factor=1.0, offset=0, sign_bit=None, **kwargs):
        super().__init__(**kwargs)
        check_type(factor, float, 'register', self.name, logger)
        self.__factor = factor
        check_type(offset, int, 'register', self.name, logger)
        self.__offset = offset
        if sign_bit:
            check_type(sign_bit, int, 'register', self.name, logger)
            self.__sign_bit = pow(2, sign_bit)
        else:
            self.__sign_bit = None

    @property
    def factor(self):
        """The conversion factor for external value."""
        return self.__factor

    @property
    def offset(self):
        """The offset for external value."""
        return self.__offset

    @property
    def sign_bit(self):
        """The sign bit, if any."""
        return self.__sign_bit

    def value_to_external(self, value):
        """
        The external representation of the register's value.

        Performs the translation of the value according to::

            external = (internal - offset) / factor

        """
        if self.sign_bit and value > (self.sign_bit / 2):
            # negative number
            value = value - self.sign_bit
        return (float(value) - self.offset) / self.factor

    def value_to_internal(self, value):
        """
        The internal representation of the register's value.

        Performs the translation of the value according to::

            internal = external * factor + offset

        The resulting value is rounded to produce an integer suitable
        to be stored in the register.
        """
        value = round(float(value) * self.factor + self.offset)
        if value < 0 and self.sign_bit:
            value = value + self.sign_bit
        return value


class RegisterWithDynamicConversion(RegisterWithConversion):
    """A register that, in addition to the conversions provided by
    :py:class:`RegisterWithConversion` can use the value provided
    by another register in the device as a factor adjustment.

    Parameters
    ----------
    factor_reg: str
        The name of the register that provides the additional factor
        adjustment.

    Raises:
        KeyError: if any of the mandatory fields are not provided
        ValueError: if value provided are wrong or the wrong type
    """
    def __init__(self, factor_reg=None, **kwargs):
        super().__init__(**kwargs)
        check_type(factor_reg, str, 'register', self.name, logger)
        # the registers may not be in order and the referenced register
        # might have not been setup yet; so we need to delay the access to
        # it for when all registers in the device are setup
        self.__factor_reg_name = factor_reg
        self.__factor_reg = None

    @property
    def factor_reg(self):
        """The register providing the additional conversion."""
        if self.__factor_reg is None:
            self.__factor_reg = getattr(self.device, self.__factor_reg_name)
        return self.__factor_reg

    def value_to_external(self, value):
        """
        The external representation of the register's value.

        Performs the translation of the value according to::

            external = (internal - offset) / factor * dynamic_factor

        """
        # we read directly from the int_value to avoid triggering a
        # read of the register every time we make the conversion
        extra_int_val = self.factor_reg.int_value
        extra_factor = self.factor_reg.value_to_external(extra_int_val)
        if self.sign_bit and value > (self.sign_bit / 2):
            # negative number
            value = value - self.sign_bit
        return (float(value) - self.offset) / self.factor * extra_factor

    def value_to_internal(self, value):
        """
        The internal representation of the register's value.

        Performs the translation of the value according to::

            internal = external * factor / dynamic_factor + offset

        The resulting value is rounded to produce an integer suitable
        to be stored in the register.
        """
        extra_int_val = self.factor_reg.int_value
        extra_factor = self.factor_reg.value_to_external(extra_int_val)

        value = round(float(value) * self.factor / extra_factor + self.offset)
        if value < 0 and self.sign_bit:
            value = value + self.sign_bit
        return value


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
        return (-value) * self.factor + self.threshold


class RegisterWithMapping(BaseRegister):
    """A register that can specify a 1:1 mapping of internal values to
    external values.

    Parameters
    ----------
    mask: int or ``None``
        Optional, can indicate that only certain bits from the value of the
        register are used in the mapping. Ex. using 0b11110000 as a mask
        indicates that only the most significant 4 bits of the internal
        value are significant for the conversion to external values.

    mapping: dict
        A dictionary that provides {internal : external} mapping. Internally
        the register will construct a reverse mapping that is used in
        converting external values to internal ones.
    """
    def __init__(self, mask=None, mapping={}, **kwargs):
        super().__init__(**kwargs)
        check_not_empty(mapping, 'mapping', 'register', self.name, logger)
        check_type(mapping, dict, 'register', self.name, logger)
        self.__mapping = mapping
        self.__inv_mapping = {v: k for k, v in self.__mapping.items()}
        if mask:
            check_type(mask, int, 'register', self.name, logger)
        self.__mask = mask

    @property
    def mapping(self):
        """The mapping {internal: external}."""
        return self.__mapping

    @property
    def inv_mapping(self):
        """The mapping {external: internal}."""
        return self.__inv_mapping

    @property
    def mask(self):
        """The bit mask is any."""
        return self.__mask

    def value_to_external(self, value):
        """Converts the internal value of the register to external format.
        Applies mask on the internal value if one specified before checking
        the mapping. If no entry is found returns 0.
        """
        if self.mask:
            value = value & self.mask
        return self.mapping.get(value, 0)

    def value_to_internal(self, value):
        """Converts the external value into an internal value using the
        inverse mapping dictionary. If no entry is found logs a warning and
        returns the already existing value in the ``int_value``.
        If mask was specified it only affects the bits specified in the mask.
        """
        int_val = self.inv_mapping.get(value, None)
        if int_val is None:
            logger.warning(f'Incorrect value {value} when converting to '
                           f'internal for register "{self.name}" of '
                           f'device "{self.device.name}"')
            return self.int_value
        # else
        if self.mask:
            masked_int_value = self.int_value & (~int(self.mask))
            int_val = int_val | masked_int_value
        return int_val
