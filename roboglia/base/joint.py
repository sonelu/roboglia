

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

    The following keys are exepcted in the dictionary:

    - ``name``: the name of the joint
    - ``device``: the device object connected to the joint
    - ``pos_read``: the register name used to retrieve current position
    - ``pos_write``: the register name used to write desired position
    - ``activate``: the register name used to control device activation
    
    The following keys are optional and can be omitted. They will be
    defaulted with the values mentioned bellow:

    - ``inverse``: indicates inverse coordinate system versus the device
    - ``offset``: offset from device's 0
    - ``min``: introduces a minimum limit for the joint value; ignored if ``None``
    - ``max``: introduces a maximum limit for the joint value; ignored if ``None
        
    ``min`` and ``max`` are used only when writing values to device. You can 
    use both, only one of them or none.
   """
    def __init__(self, init_dict):
        """Initializes the Joint from an ``init_dict``."""
        self._name = init_dict['name']
        device = init_dict['device']
        self._pos_r = getattr(device, init_dict['pos_read'])
        self._pos_w = getattr(device, init_dict['pos_write'])
        self._activate = getattr(device, init_dict['activate'])
        self._inverse = init_dict.get('inverse', False)
        self._offset = init_dict.get('offset', 0.0)
        self._min = init_dict.get('min', None)
        self._max = init_dict.get('max', None)

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
    def activate(self):
        """(read-write) Accessor for activating the joint."""
        return self._activate.value

    @activate.setter
    def activate(self, value):
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
        if self._max != None:
            value = min(self._max, value)
        if self._min != None:
            value = max(self._min, value)
        value -= self._offset
        if self._inverse:
            value = -value
        self._pos_w.value = value

    @property
    def desired_position(self):
        """(read-only) Retrieves the desired position from the write register."""
        value = self._pos_w.value
        if self._inverse:
            value = - value
        value += self._offset
        return value

    def __repr__(self):
        return f'{self.name}: p={self.position:.3f}'