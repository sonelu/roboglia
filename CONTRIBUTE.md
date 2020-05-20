# Contribute to Roboglia

We are very receptive for contributions. There are several ways you could make
a contribution to this repository:

- [Testing](#Testing): simply install the library on your main robot controller
  and see how it works with your project.
- [Submitting issues](#Submitting-Issues): if you find bugs, unexpected behavior
  or the performance of the library is not good, you can submit issues and we
  will try to deal with them as soon as possible.
- Request or Submit [new device definitions](#New-Devices)
- If you know how to fix something you can submit [code changes](#Making-Code-Changes).
  Make sure you read the details below as checks and standards are applied to
  the code submitted to the project.

## Testing

The easiest contribution you can have to this project is to install it and
test it with your own robots. Let us know how it went and if you want you can
[showcase](https://github.com/sonelu/roboglia#showcasing-your-robot) your robot
on the main repository. If you encounter bugs or unexpected behavior you can
[submit an issue](https://github.com/sonelu/roboglia/issues/new/choose).

## Submitting Issues

When you submit issues please make sure that you have at hand the information
about the system you are running the code:

- the board name and type (ex.Raspberry Pi 3B+, Orange Pi 3, Friendlyarm
  Core6818, etc); this is important as the library has dependencies on the
  hardware UART, SPI, I2C, etc.

- the operating system and release (ex. Ubuntu 16.04, Raspbian Buster, etc.)

- the version of Python installed on your machine (ex. 3.6, 3.7, etc.); note
  that ``roboglia`` does not work with Python 2.

Indicate in the issue as much information about the error codes you are seeing
and if necessary provide configuration files (YAML) used for the robot
or for the devices you are using.

## New Devices

``roboglia`` is as good as the library of devices and communication protocols
it supports. Therefore we encourage the community to requests or even better to
submit new device definition files.

If you are familiar with the structure of the device definition files and you
have certain devices that you are using in your robot, please feel free to
submit them with a [Pull Request](#Pull-Requests) and we will include them
in the base library. Make sure that the device is placed in the correct
``/device`` directory and that the naming respects the code of the chip used
by the device.

> **NOTE**: Because these type of devices can only be tested on real hardware
  and they might not be available to all the contributors, we rely on your
  tests for the correct functionality and definition of that device.

## Making Code Changes

We welcome contributors to update the base code of ``roboglia``.
Please clone the repository and make your own code changes or additions. Before
submitting a [pull request](#Pull-Requests) make sure that you have run the
tests and checks indicated below as the CI build will perform them and fail
if not successful.

If you create new Python files please add the copyright comments as they are
included in the other files. Make sure you update your name at the top, we want
people to receive the credit for their work. Similarly, if you change an
existing file feel free to add your name at the top of the file.

### Code Testing

The library comes with a series of automated tests in ``tests.py`` file in the
root directory. The tests use the robot definitions from directory ``tests/``
and run through almost all the code of ``roboglia`` to confirm that it is
working as expected. The tests use [pytest](https://docs.pytest.org/en/latest/)
and you should install it on your local machine then run:

    pytest -v test.py

You should check that all tests pass before submitting a pull requests with
your changes. If any of the tests fails the pull request will fail too and
you will have to address it before it is merged into the master.

> **NOTE**: Do not change the the exiting robot definition files without
  discussing them first as part of an issue or pull request. The files are
  designed to cover as many test scenarios as possible and adding / removing
  items from these files might change the behavior of the standard tests.

### Code Coverage

The tests above are checked using [coverage](https://coverage.readthedocs.io/en/latest/)
and the Github integration will present statistics about the impact of code
changes from a coverage perspective. Although the checks are not enforced
(if the coverage is bellow target for the changes or is going down for the
whole project) we might ask you to include additional test scenarios in
``tests.py`` to cover the newly introduced functionality. A full analysis of
the code on line-by-line basis is provided at [codecov](https://codecov.io/gh/sonelu/roboglia).
Alternatively, if you want to check the coverage in advance on your local
machine you can install [coverage](https://coverage.readthedocs.io/en/latest/)
and instead of running ``pytest`` you can use:

    coverage run -m pytest -v tests.py

followed by:

    coverage xml
    coverage report

If you have a coverage plugin for you IDE you should also be able to see
directly in your editor the coverage of test on a line-by-line basis and check if the changes you
have made are fully covered or not.

### Flake8

The CI build (done with [Travis](https://travis-ci.com/github/sonelu/roboglia))
includes a [flake8](https://pypi.org/project/flake8/) check on the whole ``roboglia``
package (the code in the directory ``roboglia/`` withing the github repo, all
other directories or files in the root are not checked).

> **NOTE**: The check is enforcing and if the code does not pass it will fail
  the build.
  
Please ensure that you run a ``flake8`` check on your repo before submitting
to avoid having to make another commit with the changes. Run this from your
root repo directory:

    flake8 roboglia

There are no exceptions defined in the CI build and you are allowed to use
[``#noqa``](https://flake8.pycqa.org/en/3.1.1/user/ignoring-errors.html)
directives if absolutely necessary to bypass the messages. They will be checked
when the PR is merged in the master.

### Pull Requests

Submit pull requests with the desired contribution. They will be moderated and,
if they add values to the users, they will be integrated. Please note that
the [Travis CI](https://travis-ci.com) integration will perform the following
two tests on the pull requests:

- unit tests as specified in the ``tests.py`` file (see [Code Testing](#Code-Testing) earlier)

- flake8 - code styling check( see [Flake8](#Flake8) earlier)

Both of these need to pass in order for the PR to be successful. In addition,
``coverage`` (see [Code Coverage](#Code-Coverage) earlier) is also run on the
patch (the difference in code) and the whole resulting project. They are not
enforced, but during the review of the PR we might require you to add test
cases in ``tests.py`` to cover for the changes introduced so that the overall
code coverage of the solution remains in in 95%+ range.

### Builds

At this moment, the builds on branches other than ``master`` are performed
on an ``AMD64`` platform using Ubuntu Xenial (16.04.6 LTS) and Python 3.6.

All builds on ``master`` and ``PR``s are build using the following 8 systems:

- AMD64 and ARM64
- Ubuntu 16.04 (Xenial) and 18.04 (Bionic)
- Python 3.6 and 3.7

In total there are 8 builds and **all need to complete successfully**
for the build to be considered successful.

### Deployment to [PyPi](https://pypi.org/project/roboglia/)

This is done automatically by the Travis build when a new Release is produced
with a valid tag.

> **NOTE**: There is no integration between the Github tag assigned to the
  release and the version that will be stored in PyPi. The version in PyPi
  is determined from the ``setup.py`` configuration and is the responsibility
  of the collaborator to make sure this is correct and not already existing
  in PyPi. PiPy will reject deployments with version number that was already
  used (even if that version was deleted from PyPi).

### Documentation

All code submitted needs to be documented according to the standard documenting
practices. If you need to get used to the style, please check some of the
source files, for example [roboglia/base/bus.py](https://github.com/sonelu/roboglia/blob/master/roboglia/base/bus.py).

``roboglia`` uses [Sphinx](https://www.sphinx-doc.org/en/master/) for documenting
with [Read the Docs template](https://readthedocs.org) and deployment.

The documentation is generated automatically for the API, although there are a
few ``.rst`` documents in [docs/](https://github.com/sonelu/roboglia/tree/master/docs)
folder that are organizing the classes in an easier to follow manner by
module.

If you create new classes you have to add them to the corresponding ``.rst``
overview for the module and also you have to make sure they are included in
the ``__init__.py`` file of the module. If you do not need them to be available
for the class factory, mark the line with ``#noqa: 401`` to stop flake8
complaining that they are imported but not used.

The documentation is build automatically for ``master`` branch and published on
[readthedocs.io](https://roboglia.readthedocs.io/en/latest/). The build log can
be accessed [here](https://readthedocs.org/projects/roboglia/builds/).
