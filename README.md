# Roboglia

[![Master Version](https://img.shields.io/badge/master-0.0.12-blue)](https://img.shields.io/badge/master-0.0.12-blue)
[![PyPI version](https://badge.fury.io/py/roboglia.svg)](https://badge.fury.io/py/roboglia)
![GitHub issues](https://img.shields.io/github/issues/sonelu/roboglia)

[![Build Status](https://travis-ci.com/sonelu/roboglia.svg?branch=master)](https://travis-ci.com/sonelu/roboglia)
[![Documentation Status](https://readthedocs.org/projects/roboglia/badge/?version=latest)](https://roboglia.readthedocs.io/en/latest/?badge=latest)
[![codecov](https://codecov.io/gh/sonelu/roboglia/branch/master/graph/badge.svg)](https://codecov.io/gh/sonelu/roboglia)
[![CodeFactor](https://www.codefactor.io/repository/github/sonelu/roboglia/badge/codefactor)](https://www.codefactor.io/repository/github/sonelu/roboglia/overview/codefactor)

``roboglia`` is a framework that helps developers with the setup of robots
in a more reusable fashion. Most of the times the creation of robots involve
integrating actuators, sensors, cameras and microphones, periodically accessing
the information provided by these or supplying commands according to the desired
activities.

The name `roboglia` is derived from the glial cells present in the brian.
Their role is to support the neurons' functions by supplying them
with nutrients, energy and disposing of waste. The analogy is that ``roboglia``
provides this boring, but very complex activity of putting together the specific
functions of the physical devices used in robots in order to provide a more
accessible high-level representation of the robot for the use of the "smart"
control logic that sits at the top.

With ``roboglia``, low level functionality, currently split across multiple
libraries and frameworks are put together and integrated in an extensible way,
making it easier for developer to focus on the higher level functionality,
rather than gritty details.

## Installation

You can install ``roboglia`` with ``pip`` as follows:

    pip install roboglia

By default this will only install the ``roboglia`` package and the core
dependencies (like ``PyYAML``) and will not include any hardware access
libraries. As different projects require different hardware communication
it is up to yu to decide which of the **extra** dependencies need to be
installed.

If you need to use Dynamixel devices, then install the ``dynamixel_sdk``
library like this:

    pip install roboglia[dynamixel]

If you need to work with I2C devices, install it the following way:

    pip install roboglia[i2c]

If you need SPI devices, install the extra libraries with:

    pip install roboglia[spi]

If you need to install a combination of libraries, then enter them separated
by commas as follows:

    pip install roboglia[dynamixel,i2c]

If you wish to install all the hardware access packages then use:

    pip install roboglia[all]

The ``all`` option for` **extras** will be updated if additional hardware
channels are added to the library.

Please read carefully the installation instructions from the
[documentation](https://roboglia.readthedocs.io/en/latest/install.html).
As ``roboglia`` needs to interact with a lot of hardware devices, it is very
sensitive to the platform and OS version used. The documentation provides more
details about avoiding the installation of packages that are not needed for
you particular robot.

## Documentation

You can access the detailed documentation on the
[readthedocs.io](https://roboglia.readthedocs.io/en/latest/) website. If you
want to access the documentation in PDF format you can get it from
[here](https://roboglia.readthedocs.io/_/downloads/en/latest/pdf/).
There is also an epub version that can be accessed
[here](https://roboglia.readthedocs.io/_/downloads/en/latest/epub/).

## Contribution

We are very receptive for contributions. There are many ways you can
contribute on ``roboglia``, so please check our dedicated [contributing page](CONTRIBUTING.md)
for details about the way you can do this.

## Showcasing your robot

If you use ``roboglia`` in your project we will like to hear about it and
we will showcase it on this page. Please
[open an issue](https://github.com/sonelu/roboglia/issues/new) with title
"Showcase of robot" and provide us with information about your robot. You can
send us links to the documentation or code of the robot and one picture
(link to an public one) that we could use in the showcase. If you want to
provide an email address for contact we will be more than happy to include
that too.
