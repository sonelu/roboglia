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

from pathlib import Path
from ..base import BaseDevice


class DynamixelDevice(BaseDevice):

    def __init__(self, init_dict):
        super().__init__(init_dict)

    def get_model_path(self):
        """Builds the path to the `.yml` documents.

        Returns:
            str :A full document path including the name of the model and the
                extension `.yml`.
        """
        # return os.path.join(os.path.dirname(__file__), 'devices')
        return Path(__file__).parent / 'devices/'

    def open(self):
        """Reads all registers of the device in direct mode.
        """
        for reg in self.registers.values():
            reg.int_value = self.read_register(reg)
