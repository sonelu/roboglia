from ..utils import register_class

from .register import DynamixelAXBaudRateRegister
from .register import DynamixelAXComplianceSlopeRegister
from .device import DynamixelDevice
from .bus import DynamixelBus

register_class(DynamixelAXBaudRateRegister)
register_class(DynamixelAXComplianceSlopeRegister)
register_class(DynamixelDevice)
register_class(DynamixelBus)
