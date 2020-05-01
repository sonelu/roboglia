import math

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
    - ``pos_read``: the register name used to retrieve from the
        device the position
    - ``pos_write``: the register name used to write to the device
        the desired position
    - ``activate``: the register name used to change the activation
        of the device
    
    The following keys are optional and can be omitted. They will be
    defaulted with the values mentioned bellow:

    - ``inverse``: ``True`` or ``False``, indicates that a joint has
        inverse coordinate system versus the device (ex. if the device
        moves counter-clockwise the joint will be clockwise); defaults
        to ``False``
    - ``offset``: represents an offset in the units used by the 
        device registers between the joint's 0 and device's 0; the
        offset is added **after** the impact of ``inverse``; defaults
        to 0
    - ``min``: introduces a minimum limit for the joint value; the
        limit is applied in joint coordinates (after ``offset`` and 
        ``inverse``); defaults to ``None`` which means no minimum is
        applied
    - ``max``: introduces a maximum limit for the joint value; the
        limit is applied in joint coordinates (after ``offset`` and 
        ``inverse``); defaults to ``None`` which means no maximum is
        applied
        
        ``min`` and ``max`` are used only when writing values to device.
        You can use both, only one of them or none.
    
    Attributes:

        name (str): The name of the joint.
        device (obj): The device object connected to the joint.
        pos_r (property reference): A reference to a `value` property of a 
                device register used for reading the present position of 
                the device.
        pos_w (property reference): A reference to a `value` property of a 
                device register used for writting the desired position to 
                the device.
        activate (property reference): A reference to a `value` property of 
                a device register used for controlling the active state of 
                the device.
        inverse (bool):  If ``True`` it indicates that the Joint is using 
                inverse coordinates in respect to the device (ie. inverted).
                If ``False`` they are the same.
        offset (float): Indicates an offset in respect to the device's 0 
                position. The offset is applied after the `inverse` 
                parameter is considered.
        min (float): Indicates a minimum limit for the Joint after considering 
                the `inverse` and `offset` parameters. If ``None`` then no 
                limit is imposed.
        max (float): Indicates a maximum limit for the Joint after considering
                the `inverse` and `offset` parameters. If ``None`` then no 
                limit is imposed.
    """
    def __init__(self, init_dict):
        """Initializes the Joint from an ``init_dict``."""
        self.name = init_dict['name']
        device = init_dict['device']
        self.pos_r = getattr(device, init_dict['pos_read']).value
        self.pos_w = getattr(device, init_dict['pos_write']).value
        self.activate = getattr(device, init_dict['activate']).value
        self.inverse = init_dict.get('inverse', False)
        self.offset = init_dict.get('offset', 0.0)
        self.min = init_dict.get('min', None)
        self.max = init_dict.get('max', None)

    def get_position(self):
        """Retrieves the position from the device surrogate and returns
        it according to the definition of the joint.
        
        Processing in order:

        - reads the value from register
        - if joint has inverse coordinates then invert the value
        - apply offset

        """
        value = self.pos_r
        if self.inverse:
            value = - value
        value += self.offset
        return value


    def set_position(self, value):
        """Requeres the position from the device surrogate according to 
        the definition of the joint.
        Processing in order:

        - clips the value between min and max
        - remove offset
        - if joint has inverse coordinates then invert the value
        - writes the value to register

        """
        if self.max != None:
            value = min(self.max, value)
        if self.min != None:
            value = max(self.min, value)
        value -= self.offset
        if self.inverse:
            value = -value
        self.pos_w = value

    position = property(fget=get_position, fset=set_position)

    @property
    def desired_position(self):
        """Provides a read-only value of the desired position of the joint.

        It is similar to the getter for position, but it uses the write
        register for the position.
        Provided for information purposes.
        """
        value = self.pos_w
        if self.inverse:
            value = - value
        value += self.offset
        return value

    def __repr__(self):
        return f'{self.name}: p={self.position:.3f}'