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
    can be either boolean if the ``bits`` parameter is used or float, in
    which case the sensor can also apply an ``inverse`` and and ``offset``
    to the values read from the device registry.

    Parameters
    ----------

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
        Default is ``False``. It is ignored if ``bits`` property is used.

    offset: float
        Indicates an offest to be adder to the value read from the register
        (after ``inverse`` if ``True``). Default is 0.0. It is ignored if
        ``bits`` property is used.

    auto: bool
        Indicates if the sensor should be automatically activated when the
        robot is started (:py:meth:roboglia.base.BaseRobot.`start` method).
        Default is ``True``.
    """
    def __init__(self, name='SENSOR', device=None, value_read=None,
                 activate=None, inverse=False, offset=0.0,
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
        ``True`` (assumes the sensors are active by default if not
        controllable.

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
        # default
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
        """(read-only) sensor uses inverse coordinates versus the device."""
        return self.__inverse

    @property
    def offset(self):
        """(read-only) The offset between sensor coords and device coords."""
        return self.__offset


    @property
    def value(self):
        """Returns the value of the sensor.

        Returns
        -------
        bool or float:
            The value of the register is adjusted with the
            ``offset`` and the ``inverse`` attributes.
        """
        reg_value = self.read_register.value
        if isinstance(reg_value, bool):
            # bool return
            return ~ reg_value if self.inverse else reg_value
        # float return
        if self.inverse:
            reg_value = - reg_value
        return reg_value + self.offset


class SensorXYZ():
    """An XYZ sensor.

    A sensor is associated with a device and has connections to 3 registers
    in that device that represents the X, Y and Z values the sensor is
    representing. In addition a sensor can have an optional register used
    to activate or deactivate the device and can publish ``X``, ``Y`` and
    ``Z`` values that are floats where the sensor applies an ``inverse``
    and and ``offset`` to the values read from the device registry.

    Parameters
    ----------

    name: str
        The name of the sensor

    device: BaseDevice or subclass
        The device associated with the sensor

    x_read: str
        The name of the register in device used to retrieve the sensor's
        value for x

    x_inverse: bool
        Indicates if the value read from the x register should be inverted
        before being presented to the user in the :py:meth:`x`. The
        inverse operation is performed before the ``x_offset`` (see below).
        Default is ``False``.

    x_offset: float
        Indicates an offest to be adder to the value read from the register x
        (after ``x_inverse`` if ``True``). Default is 0.0.

    y_read: str
        The name of the register in device used to retrieve the sensor's
        value for y

    y_inverse: bool
        Indicates if the value read from the y register should be inverted
        before being presented to the user in the :py:meth:`y`. The
        inverse operation is performed before the ``y_offset`` (see below).
        Default is ``False``.

    y_offset: float
        Indicates an offest to be adder to the value read from the register y
        (after ``y_inverse`` if ``True``). Default is 0.0.

    z_read: str
        The name of the register in device used to retrieve the sensor's
        value for z

    z_inverse: bool
        Indicates if the value read from the x register should be inverted
        before being presented to the user in the :py:meth:`z`. The
        inverse operation is performed before the ``z_offset`` (see below).
        Default is ``False``.

    z_offset: float
        Indicates an offest to be adder to the value read from the register z
        (after ``z_inverse`` if ``True``). Default is 0.0.

    activate: str or None
        The name of the register used to activate the device. If ``None``
        is used no activation for the device can be done and the sensor
        is by default assumed to be activated.

    auto: bool
        Indicates if the sensor should be automatically activated when the
        robot is started (:py:meth:roboglia.base.BaseRobot.`start` method).
        Default is ``True``.
    """
    def __init__(self, name='SENSOR-XYZ', device=None,
                 x_read=None, x_inverse=False, x_offset=0.0,
                 y_read=None, y_inverse=False, y_offset=0.0,
                 z_read=None, z_inverse=False, z_offset=0.0,
                 activate=None, auto=True, **kwargs):
        self.__name = name
        check_not_empty(device, 'device', 'sensor', self.name, logger)
        check_type(device, BaseDevice, 'sensor', self.name, logger)
        self.__device = device
        # X - value
        check_not_empty(x_read, 'x_read', 'sensor', self.name, logger)
        check_key(x_read, device.__dict__, 'sensor', self.name, logger,
                  f'device {device.name} does not have a register '
                  f'{x_read}')
        self.__x_read = getattr(device, x_read)
        check_options(x_inverse, [True, False], 'sensor', self.name, logger)
        self.__x_inverse = x_inverse
        check_type(x_offset, float, 'sensor', self.name, logger)
        self.__x_offset = x_offset
        # Y - value
        check_not_empty(y_read, 'y_read', 'sensor', self.name, logger)
        check_key(y_read, device.__dict__, 'sensor', self.name, logger,
                  f'device {device.name} does not have a register '
                  f'{y_read}')
        self.__y_read = getattr(device, y_read)
        check_options(y_inverse, [True, False], 'sensor', self.name, logger)
        self.__y_inverse = y_inverse
        check_type(y_offset, float, 'sensor', self.name, logger)
        self.__y_offset = y_offset
        # Z - value
        check_not_empty(z_read, 'z_read', 'sensor', self.name, logger)
        check_key(z_read, device.__dict__, 'sensor', self.name, logger,
                  f'device {device.name} does not have a register '
                  f'{z_read}')
        self.__z_read = getattr(device, z_read)
        check_options(z_inverse, [True, False], 'sensor', self.name, logger)
        self.__z_inverse = z_inverse
        check_type(z_offset, float, 'sensor', self.name, logger)
        self.__z_offset = z_offset
        # activate
        if activate:
            check_key(activate, device.__dict__, 'sensor', self.__name, logger,
                      f'device {device.name} does not have a register '
                      f'{activate}')
            self.__activate = getattr(device, activate)
        else:
            self.__activate = activate
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
    def x_register(self):
        """The register used to access the sensor X value."""
        return self.__x_read

    @property
    def x_inverse(self):
        """(read-only) Sensor uses inverse coordinates versus the device for
        X value."""
        return self.__x_inverse

    @property
    def x_offset(self):
        """(read-only) The offset between sensor coords and device coords for
        X value."""
        return self.__x_offset

    @property
    def y_register(self):
        """The register used to access the sensor Y value."""
        return self.__y_read

    @property
    def y_inverse(self):
        """(read-only) Sensor uses inverse coordinates versus the device for
        Y value."""
        return self.__y_inverse

    @property
    def y_offset(self):
        """(read-only) The offset between sensor coords and device coords for
        Y value."""
        return self.__y_offset

    @property
    def z_register(self):
        """The register used to access the sensor Z value."""
        return self.__z_read

    @property
    def z_inverse(self):
        """(read-only) Sensor uses inverse coordinates versus the device for
        Z value."""
        return self.__z_inverse

    @property
    def z_offset(self):
        """(read-only) The offset between sensor coords and device coords for
        Z value."""
        return self.__z_offset

    @property
    def activate_register(self):
        """(read-only) The register for activation sensor."""
        return self.__activate

    @property
    def active(self):
        """(read-write) Accessor for activating the senser. If the activation
        registry was not specified (``None``) the method will return
        ``True`` (assumes the sensors are active by default if not
        controllable.

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
        # default
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
    def x(self):
        """Returns the processed X value of register."""
        reg_value = self.x_register.value
        if self.x_inverse:
            reg_value = - reg_value
        return reg_value + self.x_offset

    @property
    def y(self):
        """Returns the processed Y value of register."""
        reg_value = self.y_register.value
        if self.y_inverse:
            reg_value = - reg_value
        return reg_value + self.y_offset

    @property
    def z(self):
        """Returns the processed Z value of register."""
        reg_value = self.z_register.value
        if self.z_inverse:
            reg_value = - reg_value
        return reg_value + self.z_offset

    @property
    def value(self):

        """Returns the value of the sensor as a tuple (X, Y, Z)."""
        return (self.x, self.y, self.z)
