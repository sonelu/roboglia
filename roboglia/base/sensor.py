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
from ..utils import check_key, check_type, check_options, check_not_empty
from .device import BaseDevice

logger = logging.getLogger(__name__)


class Sensor():
    """A one-value sensor.

    A sensor is associated with a device and has at least a connection
    to a register in that device that represents the value the sensor is
    representing. In addition a sensor can have an optional register used
    to activate or deactivate the device and can publish a ``value`` that
    can be either boolean if the ``mask`` parameter is used or float, in
    which case the sensor can also apply an ``inverse`` and and ``offset``
    to the values read from the device registry.

    Parameter
    ---------
    name: str
        The name of the sensor

    device: BaseDevice or subclass
        The device associated with the sensor

    value_read: str
        The name of the register in device used to retrieve the sensor's
        value

    activate: str or None
        The name of the register used to activate the device. If ``None``
        is used no activation for the device can be done and the sensor
        is by default assumed to be activated.

    inverse: bool
        Indicates if the value read from the register should be inverted
        before being presented to the user in the :py:meth:`value`. The
        inverse operation is performed before the ``offset`` (see below).
        Default is ``False``. It is ignored if ``mask`` property is used.

    offset: float
        Indicates an offest to be adder to the value read from the register
        (after ``inverse`` is ``True``). Default is 0.0. It is ignored if
        ``mask`` property is used.

    mask: int
        A bit mask used to AND the value read from device. After the AND is
        performed the :py:meth:`value` will return ``True`` or ``False`` if
        the result is different than 0 or not. If ``mask`` is used, the
        paramters ``inverse`` and ``offset`` are ignored. If no mask is
        needed, use ``None``. This is also the default.

    auto: bool
        Indicates if the sensor should be automatically activated when the
        robot is started (:py:meth:roboglia.base.BaseRobot.`start` method).
        Default is ``True``.
    """
    def __init__(self, name='SENSOR', device=None, value_read=None,
                 activate=None, inverse=False, offset=0.0, mask=None,
                 auto=True, **kwargs):
        self.__name = name
        check_not_empty(device, 'device', 'sensor', self.name, logger)
        check_type(device, BaseDevice, 'sensor', self.name, logger)
        self.__device = device
        check_not_empty(value_read, 'value_read', 'sensor', self.name, logger)
        check_key(value_read, device.__dict__, 'sensor', self.name, logger,
                  f'device {device.name} does not have a register '
                  f'{value_read}')
        self.__value_r = getattr(device, value_read)
        if activate:
            check_key(activate, device.__dict__, 'sensor', self.__name, logger,
                      f'device {device.name} does not have a register '
                      f'{activate}')
            self.__activate = getattr(device, activate)
        else:
            self.__activate = activate
        check_options(inverse, [True, False], 'sensor', self.name, logger)
        self.__inverse = inverse
        check_type(offset, float, 'sensor', self.name, logger)
        self.__offset = offset
        self.__mask = mask
        check_options(auto, [True, False], 'joint', self.name, logger)
        self.__auto_activate = auto

    @property
    def name(self):
        """The name of the sensor."""
        return self.__name

    @property
    def device(self):
        """The devices associated with the sensor."""
        return self.__device


    @property
    def read_register(self):
        """The register used to access the sensor value."""
        return self.__value_r

    @property
    def activate_register(self):
        """(read-only) The register for activation sensor."""
        return self.__activate

    @property
    def active(self):
        """(read-write) Accessor for activating the senser. If the activation
        registry was not specified (``None``) the method will return
        ``True`` (assumes the sensors are active by default if not controllable.

        The setter will log a warning if you try to assign a value to this
        property if there is no register assigned to it.

        Returns
        -------
        bool:
            Value of the activate register or ``True`` if no register was
            specified when the sensor was created.
        """
        if self.__activate:
            return self.__activate.value
        else:
            return True

    @active.setter
    def active(self, value):
        if self.__activate:
            self.__activate.value = value
        else:
            logger.warning(f'attempted to change activation of sensor '
                           f'{self.name} that does not have an activation '
                           'registry assigned.')

    @property
    def auto_activate(self):
        """Indicates if the joint should automatically be activated when
        the robot starts."""
        return self.__auto_activate

    @property
    def inverse(self):
        """(read-only) Joint uses inverse coordinates versus the device."""
        return self.__inverse

    @property
    def offset(self):
        """(read-only) The offset between joint coords and device coords."""
        return self.__offset

    @property
    def mask(self):
        """The (optional) bit mask to interpret the sensor data."""
        return self.__mask

    @property
    def value(self):
        """Returns the value of the sensor.

        Returns
        -------
        bool or float:
            If ``mask`` is used the sensor is assumed to produce a ``float``
            response resulted from the AND between the value of the register
            in the device and the mask. If not mask is used the sensor is
            assumed to produce a float value that is adjusted with the
            ``offset`` and the ``inverse`` attributes.
        """
        reg_value = self.read_register.value
        if self.mask:
            # boolean value
            return reg_value & self.mask != 0
        else:
            # float value
            if self.inverse:
                reg_value = - reg_value
            return reg_value + self.offset
