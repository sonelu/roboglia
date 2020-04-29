from .factory import register_class
from .bus import  FileBus
from .register import BaseRegister, FloatRegisterWithConversion, \
                      FloatRegisterWithThreshold, BoolRegister

register_class(FileBus)
register_class(BaseRegister)
register_class(FloatRegisterWithConversion)
register_class(FloatRegisterWithThreshold)
register_class(BoolRegister)