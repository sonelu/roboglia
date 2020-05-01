from pathlib import Path
from ..base.device import BaseDevice


class DynamixelDevice(BaseDevice):

    def __init__(self, init_dict):
        super().__init__(init_dict)


    def get_model_path(self):
        """Builds the path to the `.yml` documents.

        Returns:
            str :A full document path including the name of the model and the
                extension `.yml`.
        """
        #return os.path.join(os.path.dirname(__file__), 'devices')
        return Path(__file__).parent / 'devices/'

    def open(self):
        """Reads all registers of the device in direct mode.
        """
        for reg in self.registers.values():
            reg.int_value = self.read_register(reg)
        