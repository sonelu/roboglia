from ..utils.factory import register_class

from .bus import BaseBus                        # noqa: 401
from .bus import FileBus
from .bus import SharedBus                      # noqa: 401
from .bus import SharedFileBus

from .register import BaseRegister
from .register import BoolRegister
from .register import RegisterWithConversion
from .register import RegisterWithThreshold
from .register import RegisterWithMapping

from .device import BaseDevice

from .joint import PVL                          # noqa: 401
from .joint import PVLList                      # noqa: 401
from .joint import Joint
from .joint import JointPV
from .joint import JointPVL

from .sensor import Sensor
from .sensor import SensorXYZ

from .thread import BaseThread                  # noqa: 401
from .thread import BaseLoop                    # noqa: 401

from .sync import BaseSync                      # noqa: 401
from .sync import BaseReadSync                  # noqa: 401
from .sync import BaseWriteSync                 # noqa: 401

from .robot import BaseRobot                    # noqa: 401
from .robot import JointManager                 # noqa: 401

register_class(FileBus)
register_class(SharedFileBus)

register_class(BaseRegister)
register_class(RegisterWithConversion)
register_class(RegisterWithThreshold)
register_class(BoolRegister)
register_class(RegisterWithMapping)

register_class(BaseDevice)

register_class(Joint)
register_class(JointPV)
register_class(JointPVL)

register_class(Sensor)
register_class(SensorXYZ)

register_class(BaseReadSync)
register_class(BaseWriteSync)
