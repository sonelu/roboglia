#!/usr/bin/env python

#from io import open
import re
import sys

from setuptools import setup, find_packages


def version():
    with open('roboglia/_version.py') as f:
        return re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", f.read()).group(1)


extra = {}
if sys.version_info >= (3,):
    extra['use_2to3'] = True

install_requires = ['dynamixel-sdk',
                    'smbus2'
                   ]

if sys.version_info < (2, 7):
    print("python version < 2.7 is not supported")
    sys.exit(1)

setup(name='roboglia',
      version=version(),
      packages=find_packages(),
      install_requires=install_requires,
      extras_require={},
      entry_points={},
      include_package_data=True,
      exclude_package_data={'': ['.gitignore']},
      zip_safe=False,
      author='Alex Sonea',
      author_email='alex.sonea@gmail.com',
      description='Robotics Framwork based on Dynamixel SDK',
      long_description=open('README.md', encoding='utf-8').read(),
      url='https://github.com/sonelu/roboglia',
      license='GNU GENERAL PUBLIC LICENSE Version 3',
      classifiers=[
          "Programming Language :: Python :: 2",
          "Programming Language :: Python :: 3",
          "Topic :: Scientific/Engineering", ],
      **extra
      )