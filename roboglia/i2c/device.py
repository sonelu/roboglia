# Copyright (C) 2020  Alex Sonea

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import logging
from pathlib import Path

from ..base import BaseDevice

logger = logging.getLogger(__name__)


class I2CDevice(BaseDevice):
    """Implements a representation of an I2C device.

    It only adds an override for the :py:method:`~get_model_path` in order
    to localize the device definitions in the ``device`` directory of the
    ``i2c`` module and the method :py:method:`~open` that will attempt to
    read all the registers not marked as ``sync``.
    """
    def __init__(self, init_dict):
        super().__init__(init_dict)

    def get_model_path(self):
        """Builds the path to the `.yml` documents.

        Returns:
            str: the path to the *standard`* directory with device
                definitions. In this case ``devices`` in the ``i2c`` module
                directory.
        """
        # return os.path.join(os.path.dirname(__file__), 'devices')
        return Path(__file__).parent / 'devices/'

    def open(self):
        """Reads all registers of the device if not synced."""
        for reg in self.registers.values():
            # only registers that are not flagged for sync replication
            if not reg.sync:
                value = self.read_register(reg)
                if value is not None:
                    reg.int_value = value
