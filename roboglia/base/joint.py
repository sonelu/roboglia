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


class Joint():
    """A Joint is a convenient class to represent a positional device.

    A Joint class provides an abstract access to a device providing:

    - access to arbitrary registers in device to retrieve / set the position
    - possibility to invert coordinates
    - possibility to add an offset so that the 0 of the joint is different
      from the 0 of the device
    - include max and min range in joint coordinates to reflect physical
      limitation of the joint

    Args:
        init_dict (dict): The dictionary used to initialize the joint.

    The following keys are expected in the dictionary:

    - ``name``: the name of the joint
    - ``device``: the device object connected to the joint
    - ``pos_read``: the register name used to retrieve current position
    - ``pos_write``: the register name used to write desired position
    - ``activate``: the register name used to control device activation

    The following keys are optional and can be omitted. They will be
    defaulted with the values mentioned bellow:

    - ``inverse``: indicates inverse coordinate system versus the device
    - ``offset``: offset from device's 0
    - ``min``: introduces a minimum limit for the joint value; ignored if
      ``None``
    - ``max``: introduces a maximum limit for the joint value; ignored if
      ``None

    ``min`` and ``max`` are used only when writing values to device. You can
    use both, only one of them or none.
   """
    def __init__(self, init_dict):
        """Initializes the Joint from an ``init_dict``."""
        self._name = init_dict['name']
        device = init_dict['device']
        check_key('pos_read', init_dict, 'joint', self._name, logger)
        check_key(init_dict['pos_read'], device.__dict__,
                  'joint', self._name, logger,
                  f'device {device.name} does not have a register '
                  f'{init_dict["pos_read"]}')
        self._pos_r = getattr(device, init_dict['pos_read'])
        check_key('pos_write', init_dict, 'joint', self._name, logger)
        check_key(init_dict['pos_write'], device.__dict__,
                  'joint', self._name, logger,
                  f'device {device.name} does not have a register '
                  f'{init_dict["pos_write"]}')
        self._pos_w = getattr(device, init_dict['pos_write'])
        check_key('activate', init_dict, 'joint', self._name, logger)
        check_key(init_dict['activate'], device.__dict__,
                  'joint', self._name, logger,
                  f'device {device.name} does not have a register '
                  f'{init_dict["activate"]}')
        self._activate = getattr(device, init_dict['activate'])
        self._inverse = init_dict.get('inverse', False)
        check_options(self._inverse, [True, False], 'joint',
                      self._name, logger)
        self._offset = init_dict.get('offset', 0.0)
        check_type(self._offset, float, 'joint', self._name, logger)
        self._min = init_dict.get('min', None)
        if self._min:
            check_type(self._min, float, 'joint', self._name, logger)
        self._max = init_dict.get('max', None)
        if self._max:
            check_type(self._max, float, 'joint', self._name, logger)

    @property
    def name(self):
        """(read-only) Joint's name."""
        return self._name

    @property
    def device(self):
        """(read-only) The device used by joint."""
        return self._pos_r.device

    @property
    def position_read_register(self):
        """(read-only) The register for current position."""
        return self._pos_r

    @property
    def position_write_register(self):
        """(read-only) The register for desired position."""
        return self._pos_w

    @property
    def activate_register(self):
        """(read-only) The register for activation control."""
        return self._activate

    @property
    def active(self):
        """(read-write) Accessor for activating the joint."""
        return self._activate.value

    @active.setter
    def active(self, value):
        self._activate.value = value

    @property
    def inverse(self):
        """(read-only) Joint uses inverse coordinates versus the device."""
        return self._inverse

    @property
    def offset(self):
        """(read-only) The offset between joint coords and device coords."""
        return self._offset

    @property
    def range(self):
        """(read-only) Tuple (min, max) of joint limits."""
        return (self._min, self._max)

    @property
    def position(self):
        """**Getter** uses the read register and applies `inverse` and `offset`
        transformations, **setter** clips to (min, max) limit if set, applies
        `offset` and `inverse` and writes to the write register.
        """
        value = self._pos_r.value
        if self._inverse:
            value = - value
        value += self._offset
        return value

    @position.setter
    def position(self, value):
        if self._max is not None:
            value = min(self._max, value)
        if self._min is not None:
            value = max(self._min, value)
        value -= self._offset
        if self._inverse:
            value = -value
        self._pos_w.value = value

    @property
    def desired_position(self):
        """(read-only) Retrieves the desired position from the write
        register."""
        value = self._pos_w.value
        if self._inverse:
            value = - value
        value += self._offset
        return value

    def __repr__(self):
        return f'{self.name}: p={self.position:.3f}'


class JointPV(Joint):
    """A Joint with position and velocity control.

    Args:
        init_dict (dict): The dictionary used to initialize the joint.

    In addition to the keys required by the :py:class:`Joint`, the following
    keys are expected in the dictionary:

    - ``vel_read``: the register name used to retrieve current velocity
    - ``vel_write``: the register name used to write desired velocity
   """
    def __init__(self, init_dict):
        """Initializes the JointPV from an ``init_dict``."""
        super().__init__(init_dict)
        check_key('vel_read', init_dict, 'joint', self._name, logger)
        check_key(init_dict['vel_read'], self.device.__dict__,
                  'joint', self._name, logger,
                  f'device {self.device.name} does not have a register '
                  f'{init_dict["vel_read"]}')
        self._vel_r = getattr(self.device, init_dict['vel_read'])
        check_key('vel_write', init_dict, 'joint', self._name, logger)
        check_key(init_dict['vel_write'], self.device.__dict__,
                  'joint', self._name, logger,
                  f'device {self.device.name} does not have a register '
                  f'{init_dict["vel_write"]}')
        self._vel_w = getattr(self.device, init_dict['vel_read'])

    @property
    def velocity(self):
        """**Getter** uses the read register and applies `inverse` transformation,
        **setter** applies `inverse` and writes to the write register.
        """
        value = self._vel_r.value
        if self._inverse:
            value = - value
        return value

    @velocity.setter
    def velocity(self, value):
        if self._inverse:
            value = -value
        self._vel_w.value = value

    @property
    def velocity_read_register(self):
        """(read-only) The register for current velocity."""
        return self._vel_r

    @property
    def velocity_write_register(self):
        """(read-only) The register for desired velocity."""
        return self._vel_w

    @property
    def desired_velocity(self):
        """(read-only) Retrieves the desired velocity from the write
        register."""
        value = self._vel_w.value
        if self._inverse:
            value = - value
        return value

    def __repr__(self):
        return f'{self.name}: p={self.position:.3f}, v={self.velocity:.3f}'


class JointPVL(JointPV):
    """A Joint with position, velocity and load control.

    Args:
        init_dict (dict): The dictionary used to initialize the joint.

    In addition to the keys required by the :py:class:`JointPV`, the following
    keys are expected in the dictionary:

    - ``load_read``: the register name used to retrieve current load
    - ``load_write``: the register name used to write desired load
   """
    def __init__(self, init_dict):
        """Initializes the JointPVL from an ``init_dict``."""
        super().__init__(init_dict)
        check_key('load_read', init_dict, 'joint', self._name, logger)
        check_key(init_dict['load_read'], self.device.__dict__,
                  'joint', self._name, logger,
                  f'device {self.device.name} does not have a register '
                  f'{init_dict["load_read"]}')
        self._load_r = getattr(self.device, init_dict['load_read'])
        check_key('load_write', init_dict, 'joint', self._name, logger)
        check_key(init_dict['load_write'], self.device.__dict__,
                  'joint', self._name, logger,
                  f'device {self.device.name} does not have a register '
                  f'{init_dict["load_write"]}')
        self._load_w = getattr(self.device, init_dict['load_read'])

    @property
    def load(self):
        """**Getter** uses the read register and applies `inverse` transformation,
        **setter** applies `inverse` and writes to the write register.
        """
        value = self._load_r.value
        if self._inverse:
            value = - value
        return value

    @load.setter
    def load(self, value):
        if self._inverse:
            value = -value
        self._load_w.value = value

    @property
    def load_read_register(self):
        """(read-only) The register for current load."""
        return self._load_r

    @property
    def load_write_register(self):
        """(read-only) The register for desired velocity."""
        return self._load_w

    @property
    def desired_load(self):
        """(read-only) Retrieves the desired velocity from the write
        register."""
        value = self._load_w.value
        if self._inverse:
            value = - value
        return value

    def __repr__(self):
        return f'{self.name}: p={self.position:.3f}, ' + \
               f'v={self.velocity:.3f}, l={self.load:.3f}'
