Installation
============

Requirements
------------

``roboglia`` requires Python 3. The CI builds test the package with:

- Python **3.6** and **3.7**
- OS: **Linux**; distributions **Xenial** (16.04) and **Bionic** (18.04)
- Architecture: **AMD64** and **ARM64**

This doesn't mean the package might not work on other OS / Architecture /
Python version combinations, but they are not officially supported.

Due to the heavily hardware dependent nature of ``roboglia`` some of the
functionality requires lower level modules to communicate with the
physical devices. For example to use Dynamixel devices you need ``dynamixel_sdk``
module, for I2C devices ``smbus2``, for SPI devices ``spidev``, etc. These
packages are not available for all platforms and Python version, so care
must be taken when deciding what platform to use for the robot.

While the package includes these functionalities, we are aware that not
all robots will need to use all these types of devices. For instance,
a robot might use only PWM controlled devices accessed through an I2C
multiplexer like this `16 Channel PWM Bonnet`_ from Adafruit.
There is therefore no need to install ``dynamixel_sdk`` or ``spidev``.

With this observation in mind we have decided not to explicitly include
dependencies on these low level packages. This means that when you will install
``roboglia`` it will not automatically install them for you. It will also
not check if they are available, instead it will be your responsibility
to install the dependencies as you need them, as explained in the next
paragraphs. This is an important point to remember, so here it is emphasized
in a warning:

.. warning::

    ``roboglia`` does not automatically install dependent packages for
    hardware access. You will have to install them manually as your
    robot requires.

Installation procedure
----------------------

You can install ``roboglia`` without installing previously the hardware
dependencies, but when you will use it you must have those dependencies
available otherwise Python will raise an ``No module`` exception.

You can install ``roboglia`` using pip::

    pip install roboglia

This will work well, and is especially recommended, for `conda`_ environments.
This will install only the main package without hardware package dependencies,
but with other dependencies (like ``PyYAML``).

If you want to install a particular version of the package you can specify::

    pip install roboglia==X.X.X

If you want to install the latest code from Github, you can clone it and
install it from there::

    cd /tmp
    git clone https://github.com/sonelu/roboglia.git
    cd roboglia
    sudo python setup.py install

The last command might require you to enter the password to allow ``sudo`` elevation.

Installing hardware dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The installer comes with a number of configurations for **extra** packages that
can be installed as needed.

`dynamixel_sdk`_ is released and maintained by ROBOTIS, the maker of 
the Dynamixel ecosystem. For more details about the package and up to date 
information and installation instructions visit the `DynamixelSDK Manual`_ 
on ROBOTIS website.

To install ``dynamixel_sdk`` when you install ``roboglia`` you specify::

    pip install roboglia[dynamixel]

.. warning::

    ``dynamixel_sdk`` is itself dependent on ``pyserial`` and will attempt to
    install it. Not all platforms have support for ``pyserial``.


If you plan to use ``I2C`` devices in your robot, then you need to install
``smbus2``::

    pip install roboglia[i2c]

For more details about the package and up to date information and installation
instructions visit the `smbus2 Github`_ page.

.. warning::

    Not all platforms have support for ``smbus2``.

If you plan to use ``SPI`` devices in your robot, then you need to install
``spidev``::

    pip install roboglia[spi]

For more details about the package and up to date information and installation
instructions visit the `spidev Github`_ page.

.. warning::

    Not all platforms have support for ``spidev``.

If you intend to use a combination of hardware you can install them by
entering the codes above separated by comas, for instance if you need
Dynamixel and I2C you would use::

    pip install roboglia[dynamixel,i2c]

.. warning::

    The ``pip`` syntax requires there are no blanks between the elements in
    the square brackets above.

To simplify things, if you need **all** communication packages there is an option
``all`` that you can use in the installation::

    pip install roboglia[all]

.. note::

    This option will be kept in line with future developments and, if new
    hardware dependencies will be added, will be updated to include them.
    So you can be assured that this installation option will install **all**
    extra dependencies in addition to the core dependencies.


References
----------

.. target-notes::

.. _`16 Channel PWM Bonnet`: https://www.adafruit.com/product/3416
.. _`dynamixel_sdk`: https://github.com/ROBOTIS-GIT/DynamixelSDK
.. _`DynamixelSDK Manual`: https://github.com/ROBOTIS-GIT/DynamixelSDK.git
.. _`smbus2 Github`: https://github.com/kplindegaard/smbus2
.. _`spidev Github`: https://github.com/doceme/py-spidev
.. _`conda`: https://www.anaconda.com