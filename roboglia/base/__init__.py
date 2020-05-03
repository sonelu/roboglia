from ..utils.factory import register_class

from .bus import BaseBus                        # noqa: 401
from .bus import FileBus                        # noqa: 401

from .register import BaseRegister              # noqa: 401
from .register import BoolRegister              # noqa: 401
from .register import RegisterWithConversion    # noqa: 401
from .register import RegisterWithThreshold     # noqa: 401

from .device import BaseDevice                  # noqa: 401

from .joint import Joint                        # noqa: 401
from .joint import JointPV                      # noqa: 401
from .joint import JointPVL                     # noqa: 401

from .sync import BaseThread                    # noqa: 401
from .sync import BaseLoop                      # noqa: 401
from .sync import StepLoop                      # noqa: 401

from .robot import BaseRobot                    # noqa: 401

register_class(FileBus)

register_class(BaseRegister)
register_class(RegisterWithConversion)
register_class(RegisterWithThreshold)
register_class(BoolRegister)

register_class(BaseDevice)

register_class(Joint)
register_class(JointPV)
register_class(JointPVL)
