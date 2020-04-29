from roboglia.base.factory import register_class

from .register import DynamixelAXBaudRateRegister, DynamixelAXComplianceSlopeRegister
from .device import DynamixelDevice
from .bus import DynamixelBus

register_class(DynamixelAXBaudRateRegister)
register_class(DynamixelAXComplianceSlopeRegister)
register_class(DynamixelDevice)
register_class(DynamixelBus)