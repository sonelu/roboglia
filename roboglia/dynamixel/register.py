from math import log
from roboglia.base.register import BaseRegister


class DynamixelAXBaudRateRegister(BaseRegister):
    """Implements a representation of a baud rate register for AX servos.

    Defaults `min` to 1 and `max` to 207 and implements the mapping
    between the internal number and the real baud rates.
    """
    def __init__(self, init_dict):
        init_dict['min'] = 1
        init_dict['max'] = 207
        super().__init__(init_dict)

    def value_to_external(self):
        return {1: 1000000, 3: 500000, 4: 400000, 7: 250000,
                9: 200000, 16: 115200, 34: 57600, 103: 19200,
                207: 9600}.get(super().value_to_external(), 0)

    def value_to_internal(self, value):
        conv_value = {1000000: 1, 500000: 3, 400000: 4, 250000: 7,
                      200000: 9, 115200: 16, 57600: 34, 19200: 103,
                      9600: 207}.get(int(value), None)
        if conv_value is None:
            raise ValueError(f'{value} not supported for AX baud rate')
        super().value_to_internal(conv_value)

    value = property(value_to_external, value_to_internal)


class DynamixelAXComplianceSlopeRegister(BaseRegister):

    def __init__(self, init_dict):
        init_dict['max'] = 254
        super().__init__(init_dict)

    def value_to_external(self):
        return round(log(super().value_to_external(), 2))

    def value_to_internal(self, value):
        super().value_to_internal(pow(2, value))

    value = property(value_to_external, value_to_internal)
