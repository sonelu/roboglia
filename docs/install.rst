Installation
============

Requirements
------------

``roboglia`` requires Python 3.

Due to the heavily hardware dependent nature of ``roboglia`` some of the
functionality requires lower level modules needed to communicate with the
physical devices. For example to use Dynamixel devices you need ``dynamixel_sdk``
module, for I2C devices ``smbus2``, for SPI devices ``spidev``. These
packages are not available for all platforms and Phyton version, so care
must be taken when deciding what platform to use for the robot.

While the package includes these functionalities, we are aware that not
all robots will need to use all these types of devices. For instance,
a robot might use only PWM controlled devices accessed through an I2C
multiplexer like this `16 Channel PWM Bonnet`_ from Adafruit.
There is therefore no need to install ``dynamixel_sdk`` whihch is a relatively
complex activity.

With this observation in mind we have decided not to explicitly include
dependencies on these low level packages. Whihch means when you will install
``roboglia`` it will not automatically install them for you. It will also
not check if they are avaialable, instead it will be your responsiblity
to install the dependencies as you need them, as explained in the next
paragraphs. This is an important point to remember, so here is it emphasised
in a warning:

.. warning::
    ``roboglia`` does not install automatically dependent packages for
    hardware access. You will have to install them manually as your
    robot requires.

dynamixel_sdk
^^^^^^^^^^^^^

You will need to install ``dynamixel_sdk`` if you plan to use any Dynamixel
devices or use any of the class in the module ``roboglia.dynamixel``.

The `dynamixel_sdk`_ is released and maintained by ROBOTIS, the maker of 
the Dynamixel ecosystem. The installation requires running ``setuptools``
and is not avaialable in ``pip``.

The installation procedure involves downloading the package from Github and
installing it manually. The following instructions are for Linux and MacOS,
although they are very similiar for Windows::

    cd /tmp
    git clone https://github.com/ROBOTIS-GIT/DynamixelSDK.git
    cd DynamixelSDK/python
    sudo python setup.py install

The last command might require you to enter the password to allow ``sudo`` elevation.
Depending on your platform settings you might be able to run the last command
without ``sudo``.

If you plan to use virtual environments or ``conda`` make sure that you
first activate the environment where you want to install ``dynamixel_sdk``.

For more details about the package and up to date information and installation
instructions visit the `DynamixelSDK Manual`_ on ROBOTIS website.

smbus2
^^^^^^

``roboglia`` uses ``smbus2`` to operate I2C devices. Therefore, if your robot
will need to access these types of devices you will need to install this
package.

Fortunatelly this is simple and can be done with ``pip`` as follows::

    pip install smbus2

If you plan to use virtual environments or ``conda`` make sure that you
first activate the environment where you want to install ``smbus2``.

For more details about the package and up to date information and installation
instructions visit the `smbus2 Github`_ page.


spidev
^^^^^^

``roboglia`` uses ``spidev`` to operate SPI devices. Therefore, if your robot
will need to access these types of devices you will need to install this
package.

Fortunatelly this is simple and can be done with ``pip`` as follows::

    pip install spidev

If you plan to use virtual environments or ``conda`` make sure that you
first activate the environment where you want to install ``spidev``.

For more details about the package and up to date information and installation
instructions visit the `spidev Github`_ page.

.. warning:
    ``spidev`` might not work on all platforms and is highly dependent on 
    the operating system and the configuration of the machine.

Installation procedure
----------------------

You can install ``roboglia`` without installing previously the hardware
dependencies, but when you will use it you must have those dependencies
available otherwise Python will raise an ``No module`` exception.

For the time being the installation is manual. You will have to download
the package from Github and install it using the setup script provided::

    cd /tmp
    git clone https://github.com/sonelu/roboglia.git
    cd roboglia
    sudo python setup.py install

The last command might require you to enter the password to allow ``sudo`` elevation.
Depending on your platform settings you might be able to run the last command
without ``sudo``.

If you plan to use virtual environments or ``conda`` make sure that you
first activate the environment where you want to install ``dynamixel_sdk``.

References
----------

.. target-notes::

.. _`16 Channel PWM Bonnet`: https://www.adafruit.com/product/3416
.. _`dynamixel_sdk`: https://github.com/ROBOTIS-GIT/DynamixelSDK
.. _`DynamixelSDK Manual`: https://github.com/ROBOTIS-GIT/DynamixelSDK.git
.. _`smbus2 Github`: https://github.com/kplindegaard/smbus2
.. _`spidev Github`: https://github.com/doceme/py-spidev