# Roboglia

[![PyPI version](https://badge.fury.io/py/roboglia.svg)](https://badge.fury.io/py/roboglia)
[![Build Status](https://travis-ci.com/sonelu/roboglia.svg?branch=master)](https://travis-ci.com/sonelu/roboglia)
[![Documentation Status](https://readthedocs.org/projects/roboglia/badge/?version=latest)](https://roboglia.readthedocs.io/en/latest/?badge=latest)
[![codecov](https://codecov.io/gh/sonelu/roboglia/branch/master/graph/badge.svg)](https://codecov.io/gh/sonelu/roboglia)

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

We are very receptive for contributions. Please clone the repository and
submit pull requests with the desired contribution. They will be moderated and,
if they add values to the users, they will be integrated. Please note that
the [Travis CI](https://travis-ci.com) integration will perform the following
two tests on the pull requests:

* it will run all automated tests located in ``tests/`` folder. Please make
  sure that you also run them **before** submitting the pull request to avoid
  it failing. You you should install first your version of the package on
  your machine an then run the tests like this (you should be in the top
  directory of the cloned repository):

      sudo python setup.py install
      cd tests
      python all_tests.py

  Make sure that there are no errors issued by the unit tests. If you created
  new classes or new functions that are not covered by testing, then you will
  also need to write a test class or add a test method in an exiting class
  to test that functionality and submit those changes too.

* it will check PEP8 on the Python code using flake8. You should install
  (if you don't have it already) on your machine and run this (from the
  top directory of the cloned repository):

      flake8 roboglia --statistics --count

  Make sure flake8 does not report any problems, and correct any issues
  **before** submitting you are allowed to use ``# noqa`` directives if
  justified.

If you add classes or methods the documentation templates that produce
the API Reference might need to be updated too, but this is something that
will be moderated and can be performed centrally once the code is stable.
If you know [sphinx](https://www.sphinx-doc.org/en/master/) then you can
attempt modifying the files in ``docs/`` folder too and include the changes
in the pull request.

If you create new Python files please add the copyright comments as they are
included in the other files. Make sure you update your name at the top, we want
people to receive the credit for their work. Similarly, if you change an
existing file feel free to add your name at the top of the file.

## Showcasing your robot

If you use ``roboglia`` in your project we will like to hear about it and
we will showcase it on this page. Please
[open an issue](https://github.com/sonelu/roboglia/issues/new) with title
"Showcase of robot" and provide us with information about your robot. You can
send us links to the documentation or code of the robot and one picture
(link to an public one) that we could use in the showcase. If you want to
provide an email address for contact we will be more than happy to include
that too.
