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


class Joint():
    """A Joint is a convenient class to represent a positional device.

    A Joint class provides an abstract access to a device providing:

    - access to arbitrary registers in device to retrieve / set the position
    - possibility to invert coordinates
    - possibility to add an offset so that the 0 of the joint is different
      from the 0 of the device
    - include max and min range in joint coordinates to reflect physical
      limitation of the joint

    Parameters
    ----------
    name: str
        The name of the joint

    device: BaseDevice or subclass
        The device object connected to the joint

    pos_read: str
        The register name used to retrieve current position

    pos_write: str
        The register name used to write desired position

    activate: str or ``None``
        The register name used to control device activation. Optional.

    inverse: bool
        Indicates inverse coordinate system versus the device; default
        ``False``

    offset: float
        Offset of the joint from device's 0; default 0.0

    minim: float or ``None``
        Introduces a minimum limit for the joint value; ignored if ``None``
        which is also the default

    maxim: float or ``None``
        Introduces a maximum limit for the joint value; ignored if ``None
        which is also the default

    auto: bool
        The joint should activate automatically when the robot starts;
        defaults to ``True``
   """
    def __init__(self, name='JOINT', device=None, pos_read=None,
                 pos_write=None, activate=None, inverse=False, offset=0.0,
                 minim=None, maxim=None, auto=True, **kwargs):
        self.__name = name
        check_not_empty(device, 'device', 'joint', self.name, logger)
        check_type(device, BaseDevice, 'joint', self.name, logger)
        self.__device = device
        check_not_empty(pos_read, 'pos_read', 'joint', self.name, logger)
        check_key(pos_read, device.__dict__, 'joint', self.name, logger,
                  f'device {device.name} does not have a register '
                  f'{pos_read}')
        self.__pos_r = getattr(device, pos_read)
        check_not_empty(pos_read, 'pos_read', 'joint', self.name, logger)
        check_key(pos_write, device.__dict__, 'joint', self.name, logger,
                  f'device {device.name} does not have a register '
                  f'{pos_write}')
        self.__pos_w = getattr(device, pos_write)
        if activate:
            check_key(activate, device.__dict__, 'joint', self.__name, logger,
                      f'device {device.name} does not have a register '
                      f'{activate}')
            self.__activate = getattr(device, activate)
        else:
            self.__activate = activate
        check_options(inverse, [True, False], 'joint', self.name, logger)
        self.__inverse = inverse
        check_type(offset, float, 'joint', self.name, logger)
        self.__offset = offset
        if minim:
            check_type(minim, float, 'joint', self.name, logger)
        self.__min = minim
        if maxim:
            check_type(maxim, float, 'joint', self.name, logger)
        self.__max = maxim
        check_options(auto, [True, False], 'joint', self.name, logger)
        self.__auto_activate = auto

    @property
    def name(self):
        """(read-only) Joint's name."""
        return self.__name

    @property
    def device(self):
        """(read-only) The device used by joint."""
        return self.__device

    @property
    def position_read_register(self):
        """(read-only) The register for current position."""
        return self.__pos_r

    @property
    def position_write_register(self):
        """(read-only) The register for desired position."""
        return self.__pos_w

    @property
    def activate_register(self):
        """(read-only) The register for activation control."""
        return self.__activate

    @property
    def active(self):
        """(read-write) Accessor for activating the joint. If the activation
        registry was not specified (``None``) the method will return
        ``True`` (assumes the joints are active by default if not controllable.

        The setter will log a warning if you try to assign a value to this
        property if there is no register assigned to it.

        Returns
        -------
        bool:
            Value of the activate register or ``True`` if no register was
            specified when the joint was created.
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
            logger.warning(f'attempted to change activation of joint '
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
    def range(self):
        """(read-only) Tuple (min, max) of joint limits.

        Returns
        -------
        (min, max)
            A tuple with the min and max limits for the joints. ``None``
            indicates that the joint does not have a particular limit set.
            """
        return (self.__min, self.__max)

    @property
    def position(self):
        """**Getter** uses the read register and applies `inverse` and `offset`
        transformations, **setter** clips to (min, max) limit if set, applies
        `offset` and `inverse` and writes to the write register.
        """
        value = self.__pos_r.value
        if self.__inverse:
            value = - value
        value += self.__offset
        return value

    @position.setter
    def position(self, value):
        if self.__max is not None:
            value = min(self.__max, value)
        if self.__min is not None:
            value = max(self.__min, value)
        value -= self.__offset
        if self.__inverse:
            value = -value
        self.__pos_w.value = value

    @property
    def desired_position(self):
        """(read-only) Retrieves the desired position from the write
        register."""
        value = self.__pos_w.value
        if self.__inverse:
            value = - value
        value += self.__offset
        return value

    def __repr__(self):
        return f'{self.name}: p={self.position:.3f}'


class JointPV(Joint):
    """A Joint with position and velocity control.

    It inherits all the paramters from :py:class:`Joint` and adds the
    following additional ones:

    Parameters
    ----------
    vel_read: str
        The register name used to retrieve current velocity

    vel_write: str
        The register name used to write desired velocity
   """
    def __init__(self, vel_read=None, vel_write=None, **kwargs):
        super().__init__(**kwargs)
        check_not_empty(vel_read, 'vel_read', 'joint', self.name, logger)
        check_key(vel_read, self.device.__dict__,
                  'joint', self.name, logger,
                  f'device {self.device.name} does not have a register '
                  f'{vel_read}')
        self.__vel_r = getattr(self.device, vel_read)
        check_not_empty(vel_write, 'vel_write', 'joint', self.name, logger)
        check_key(vel_write, self.device.__dict__,
                  'joint', self.name, logger,
                  f'device {self.device.name} does not have a register '
                  f'{vel_write}')
        self.__vel_w = getattr(self.device, vel_write)

    @property
    def velocity(self):
        """**Getter** uses the read register and applies `inverse` transformation,
        **setter** uses absolute values and writes to the write register.
        """
        value = self.__vel_r.value
        if self.inverse:
            value = - value
        return value

    @velocity.setter
    def velocity(self, value):
        # desired velocity is absolute only!
        self.__vel_w.value = abs(value)

    @property
    def velocity_read_register(self):
        """(read-only) The register for current velocity."""
        return self.__vel_r

    @property
    def velocity_write_register(self):
        """(read-only) The register for desired velocity."""
        return self.__vel_w

    @property
    def desired_velocity(self):
        """(read-only) Retrieves the desired velocity from the write
        register."""
        # should be absolute only
        return self.__vel_w.value

    def __repr__(self):
        return f'{Joint.__repr__(self)}, v={self.velocity:.3f}'


class JointPVL(JointPV):
    """A Joint with position, velocity and load control.

    It inherits all the paramters from :py:class:`JointPV` and adds the
    following additional ones:

    Paramters
    ---------
    load_read: str
        The register name used to retrieve current load

    load_write: str
        The register name used to write desired load
   """
    def __init__(self, load_read=None, load_write=None, **kwargs):
        super().__init__(**kwargs)
        check_not_empty(load_read, 'load_read', 'joint', self.name, logger)
        check_key(load_read, self.device.__dict__,
                  'joint', self.name, logger,
                  f'device {self.device.name} does not have a register '
                  f'{load_read}')
        self.__load_r = getattr(self.device, load_read)
        check_not_empty(load_write, 'load_write', 'joint', self.name, logger)
        check_key(load_write, self.device.__dict__,
                  'joint', self.name, logger,
                  f'device {self.device.name} does not have a register '
                  f'{load_write}')
        self.__load_w = getattr(self.device, load_write)

    @property
    def load(self):
        """**Getter** uses the read register and applies `inverse` transformation,
        **setter** uses absolute values and writes to the write register.
        """
        value = self.__load_r.value
        if self.inverse:
            value = - value
        return value

    @load.setter
    def load(self, value):
        # desired load is absolute value!
        self.__load_w.value = abs(value)

    @property
    def load_read_register(self):
        """(read-only) The register for current load."""
        return self.__load_r

    @property
    def load_write_register(self):
        """(read-only) The register for desired velocity."""
        return self.__load_w

    @property
    def desired_load(self):
        """(read-only) Retrieves the desired velocity from the write
        register."""
        # should be absolute value!
        return self.__load_w.value

    def __repr__(self):
        return f'{JointPV.__repr__(self)}, l={self.load:.3f}'
