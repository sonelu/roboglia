from .device import BaseDevice

class BaseRegister():
    """A minimal representation of a device register.
    
    The `init_dict` must contain the following information, otherwise
    a `KeyError` will be thrown:
    
    - `device`: the object that owns the register (not the name)
    - `name`: the name of the register
    - `address`: the register address
    
    Optionally the following items can be provided or will be defaulted:
    
    - `size`: the register size in bytes; defaults to 1
    - `min`: min value represented in register; defaults to 0
    - `max`: max value represented in register; defaults to 2^size - 1
    the setter method will check that the desired value is within the 
    [min, max] and trim it accordingly
    - `access`: read ('R') or read-write ('RW'); default 'R'
    - `sync`: True is the register will be updated from the real device
    using a sync loop. If `sync` is False access to the register through
    the value property will invoke reading / writing to the real register;
    default 'False'
    - `default`: the default value for the register; implicit 0
    """
    def __init__(self, init_dict):
        # these will throw exceptions if not provided
        self.device = init_dict['device']
        assert(isinstance(self.device, BaseDevice))
        self.name = init_dict['name']
        self.address = init_dict['address']
        # optionals
        self.size = init_dict.get('size', 1)
        self.min = init_dict.get('min', 0)
        self.max = init_dict.get('max', pow(2, self.size*8)-1)
        self.access = init_dict.get('access', 'R')
        assert(self.access in ['R', 'RW'])
        self.sync = init_dict.get('sync', False)
        assert(self.sync in [True, False])
        self.default = init_dict.get('default', 0)
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
        # trim accroding to min and max for the register
        if self.access != 'R':
            self.int_value = max(self.min, min(self.max, value))
            if not self.sync:
                # direct sync
                self.write()

    value = property(value_to_external, value_to_internal)

    def write(self):
        """Performs the actual writing of the internal value of the register
        to the device. Calls the device's method to write the value of register.
        """
        self.device.write_register(self, self.int_value)


    def read(self):
        """Performs the actual reading of the internal value of the register
        from the device. In `BaseDevice` the method doesn't do anything and
        subclasses should overwrite this mehtod to actually invoke the 
        buses' methods for reading information from the device.
        """
        self.int_value = self.device.read_register(self)


    def __str__(self):
        """Representation of the register [name]: value."""
        return f'[{self.name}]: {self.value} ({self.int_value})'


class BoolRegister(BaseRegister):
    """A register with BOOL representation (true/false).
    
    Inherits from `BaseRegister` all methods and defaults `max` to 1."""
    def __init__(self, init_dict):
        init_dict['max'] = 1
        super().__init__(init_dict)


    def value_to_external(self):
        """
        The external representation of the register's value.
        
        Perform conversion to bool on top of the inherited method.
        """
        return bool(super().value_to_external())


    def value_to_internal(self, value):
        """
        The internal representation of the register's value.
        
        Perform conversion to bool on top of the inherited method.
        """
        super().value_to_internal(bool(value))

    value = property(value_to_external, value_to_internal)


class FloatRegisterWithConversion(BaseRegister):
    """A register with an external representation that is produced by 
    using a linear transformation:
    `external = (internal - offset) / factor`
    `internal = external * factor + offset`
    """
    def __init__(self, init_dict):
        super().__init__(init_dict)
        self.factor = init_dict['factor']
        self.offset = init_dict.get('offset', 0)

    
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
        value = round(float(value)  * self.factor + self.offset)
        super().value_to_internal(value)

    value = property(value_to_external, value_to_internal)


class FloatRegisterWithThreshold(BaseRegister):
    """A register with an external representation that is produced by 
    using a linear transformation:
    `external = internal / factor - offset`
    """
    def __init__(self, init_dict):
        super().__init__(init_dict)
        self.factor = init_dict['factor']
        self.threshold = init_dict['threshold']

    
    def value_to_external(self):
        """The external representation of the register's value.
        
        Performs the translation of the value after calling the inherited
        method.
        """
        value = super().value_to_external()
        if value >= self.threshold:
            return (value - self.threshold) / self.factor
        else:
            return (-value) / self.factor


    def value_to_internal(self, value):
        """The internal representation of the register's value.
        
        Performs the translation of the value before calling the inherited
        method.
        """
        if value < 0:
            value = (-value) * self.factor
        else:
            value = value * self.factor + self.threshold
        super().value_to_internal(round(value))

    value = property(value_to_external, value_to_internal)