from roboglia.utils.factory import register_class
from .bus import  *
from .register import *
from .device import *
from .joint import *
from .sync import *
from .robot import *


register_class(FileBus)
register_class(BaseRegister)
register_class(RegisterWithConversion)
register_class(RegisterWithThreshold)
register_class(BoolRegister)