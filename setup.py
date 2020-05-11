#!/usr/bin/env python

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

import re
import sys

from setuptools import setup, find_packages


def version():
    with open('roboglia/_version.py') as f:
        return re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", f.read()).group(1)


extra = {}
if sys.version_info >= (3,):
    extra['use_2to3'] = True

"""
The following  are not included in the dependencies because otherwise it would
make it impossible to use the framework on platforms where these
libraries are not avaialble. Instead you should install the dependencies
manually as needed.
 - if you want to use Dynamixel servos you need to install dynamixel_sdk
 - if you want to use I2C devices you need to install SMBus
 - if you want to use SPI devices you need to install spidev
"""
install_requires = ['pyyaml']

extras = {
    "spi": ['spidev'],
    "i2c": ['smbus2'],
    "dynamixel": ['dynamixel-sdk'],
    "all": ['spidev','smbus2','dynamixel-sdk']
}

if sys.version_info < (3, 0):
    print("Waning: Python version 2 is not supported...")


setup(name='roboglia',
      version=version(),
      packages=find_packages(),
      install_requires=install_requires,
      extras_require=extras,
      entry_points={},
      package_data={'roboglia': ['base/devices/*.yml',
                                 'dynamixel/devices/*.yml',
                                 'i2c/devices/*.yml',
                                 'spi/devices/*.yml']},
      include_package_data=True,
      exclude_package_data={'': ['.gitignore']},
      zip_safe=False,
      author='Alex Sonea',
      author_email='alex.sonea@gmail.com',
      description='Robotics Framework unsing Dynamixel SDK, I2C, SPI',
      long_description=open('README.md', encoding='utf-8').read(),
      long_description_content_type='text/markdown',
      url='https://github.com/sonelu/roboglia',
      project_urls = {
          'Documentation': 'https://roboglia.readthedocs.io/en/latest/',
          'Bug tracker': 'https://github.com/sonelu/roboglia/issues',
          'Installation': 
            'https://roboglia.readthedocs.io/en/latest/install.html'
      },
      license='GNU GENERAL PUBLIC LICENSE Version 3',
      classifiers=[
          "Programming Language :: Python :: 3",
          "Topic :: Scientific/Engineering", ],
      **extra
      )