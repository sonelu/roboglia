import math

class Joint():
    """A Joint is a convenient class to represent a positional device.

    A Joint class provides an abstract access to a device providing:

    - access to arbitrary registers in device to retrieve / set the position
    - conversion between degrees and radians (if necessary)
    - possibility to invert coordinates
    - possibility to add an offset so that the 0 of the joint is different
    from the 0 of the device
    - include max and min range in joint coordinates to reflect physical
    limitation of the joint
    
    """
    def __init__(self, init_dict):
        self.name = init_dict['name']
        device = init_dict['device']
        self.pos_r = getattr(device, init_dict['pos_read']).value
        self.pos_w = getattr(device, init_dict['pos_write']).value
        self.activate = getattr(device, init_dict['activate']).value
        self.inverse = init_dict.get('inverse', False)
        self.offset = init_dict.get('offset', 0.0)
        self.min = init_dict.get('min', -math.pi)
        self.max = init_dict.get('max', math.pi)
        conv = init_dict.get('pos_conv', None)
        if conv == None:
            self.conv_w = None
            self.conv_r = None
        elif conv == 'deg_to_rad':
            self.conv_w = math.degrees
            self.conv_r = math.radians
        else:
            raise ValueError(f'conversion method {conv} not supported, use None or deg_to_rad')


    def get_position(self):
        """Retrieves the position from the device surrogate and returns
        it according to the definition of the joint.
        Processing in order:
        - reads the value from register
        - if conversion to radians is required then do it
        - if joint has inverse coordinates then invert the value
        - apply offset
        """
        value = self.pos_r
        if self.conv_r:
            value = self.conv_r(value)
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
        - if conversion from radians is required then do it
        - writes the value to register
        """
        value = max(self.min, min(self.max, value))
        value -= self.offset
        if self.inverse:
            value = -value
        if self.conv_w:
            value = self.conv_w(value)
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
        if self.conv_r:
            value = self.conv_r(value)
        if self.inverse:
            value = - value
        value += self.offset
        return value

    def __repr__(self):
        return f'{self.name}: p={self.position:.3f}'