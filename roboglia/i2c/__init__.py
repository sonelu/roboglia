from ..utils import register_class

from .bus import I2CBus
from .bus import SharedI2CBus
from .bus import MockSMBus                                  # noqa F401

from .device import I2CDevice

register_class(I2CBus)
register_class(SharedI2CBus)

register_class(I2CDevice)
