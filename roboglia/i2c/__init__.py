from ..utils import register_class

from .bus import I2CBus
from .bus import SharedI2CBus
from .bus import MockSMBus                                  # noqa F401

from .device import I2CDevice

from .sync import I2CReadLoop
from .sync import I2CWriteLoop

register_class(I2CBus)
register_class(SharedI2CBus)

register_class(I2CDevice)

register_class(I2CReadLoop)
register_class(I2CWriteLoop)
