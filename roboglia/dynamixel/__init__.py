from ..utils import register_class                              # noqa: E401

from .register import DynamixelAXBaudRateRegister               # noqa: E401
from .register import DynamixelAXComplianceSlopeRegister        # noqa: E401

from .device import DynamixelDevice                             # noqa: E401

from .bus import DynamixelBus                                   # noqa: E401

from .sync import DynamixelSyncReadLoop                         # noqa: E401
from .sync import DynamixelSyncWriteLoop                        # noqa: E401
from .sync import DynamixelBulkReadLoop                         # noqa: E401
from .sync import DynamixelBulkWriteLoop                        # noqa: E401

register_class(DynamixelAXBaudRateRegister)                     # noqa: E401
register_class(DynamixelAXComplianceSlopeRegister)              # noqa: E401

register_class(DynamixelDevice)                                 # noqa: E401

register_class(DynamixelBus)                                    # noqa: E401

register_class(DynamixelSyncReadLoop)                           # noqa: E401
register_class(DynamixelSyncWriteLoop)                          # noqa: E401
register_class(DynamixelBulkReadLoop)                           # noqa: E401
register_class(DynamixelBulkWriteLoop)                          # noqa: E401
