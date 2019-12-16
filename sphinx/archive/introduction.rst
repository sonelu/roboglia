Introduction to `roboglia`
==========================

`roboglia` is (yet another) framework for the control of robots, mainly based on the Dynamxel actuators. While it started with this purpose in mind, the framework is designed so that it can be extend (and is in certain cases) to other type of devices.

Architectural elements
---------------------------

The main elements in `robogia` are relatively intuitive:

* the first is the `Robot` an object that contains the information about a physical robot and provides convenient access to its consituent parts.
* the `Robot` contains a number of `Devices` that provide functionality to it. They can be actuators, sensors, display devices, etc. The framework provides a consistent way of representing and interacting with these devices while keeping their particularities in place.
* the Robot interacts with the Devices through `Buses` that are communication channels using defined `Protocols`, specifcally suited for the devices connected to that channel.

The framework starts with a `Base` group of objects that define common functionality expected for all objects. This is then expanded to specialized classes for Dynamixel, I2C, SPI and video - devices, enhancing the base processing. You can easily define additional classes of object and expand the avialable ones in `roboglia`, according to your own needs.

Descriptor files
----------------

Many details in `roboglia` are provided in text formated files instead of writing specialized classes for each object. For instance the devices that can be used by the robot are based on classes that configure themsleves dynamically from information read in these files. Dynamixel servos have a large range of models and quite different internal structure. Instead of writing classes for each of these devices, we only provide a single class DynamixelServo (which we will describe later) and create instance of this by providing information about the model of the servo, representing the `.device` descriptor file to be used. This way it is very easy to introduce new device types without having to add new code or classes to the framework. We will also present later how this

Base classes
------------

We will start with the presentation of the standard objects from the *base* category. In general these classes are intended to provide common functionlity and not to be used directly, but to be subclassed by more detailed classes that also provide implementation for the interaction with the physical devices. But they are important to understand as they cover a significant functional scope that is later inherited by the more specialized classes.

BaseRobot
^^^^^^^^^

We will start with the `BaseRobot` class as this represents the cornerstone of the framework. You shoud not use the `BaseRobot` to initialize a robot in your application, but instead define a subclass of this that handles appropriately all the objects that you need to contain in the description of the robot. The `BaseRobot` only can use `BaseBus` and `BaseDevice` as constituents, while your robot might have to operate with an arbitrary number of devices and buses and many of them could be custom defined for that particular implementation. For this reason it is necessary to make the allocations for these objects from a module that includes the defintions of these classes.

The initialization of a robot is based on a *robot defintion file* that is a plain text (INI) file with sections describing the components of the robot (unsually stored in a file with extension `.robot`)::

    [buses]
    # ports section for the robot
    # table headers are important for the imnitialization of the Class
    # so pay attention to the spelling!
    Class           | Name            | Port                             | Params
    DynamixelBus    | DYN0            | /dev/tty.usbserial-AL01QHDB      | Protocol=2.0, Baudrate=1000000, RS485=N

    [devices]
    Class           | Model    | Name    | Bus     |  Id
    DynamixelServo  | XL-320   | head_p  | DYN0    |  1 
    DynamixelServo  | XL-320   | heap_y  | DYN0    |  2

The robot instance is created by parsing this INI file and allocating the objects as they appear in the various groups. The help function `readIniFile` from `roboglia.utils` performs this parsing and returns a dictionary with all the sections, each section containing all the individual records 

The `[buses]` section provides the defintion of *buses* used by the robot. A typical robot might include, for example, one or more communication channels for actuators, I2C channels for communication with sensors, SPI channel for interacting with a display and a video channel for communication with a camera. From a logical perpective, they are all channels that are listed in this first section of the file, together with a number of basic attributes:

* *Class* is the actual Python class that implements the functionality for that bus.
* *Name* the name under which you will later access the bus
* *Port* the physical port used for communication (the meanining depends on the bus type, for instance a serial bus might be accessed as '/dev/ttyUSB0' while the SPI bus might be just 0 or 1 depending on the bus used).
* *Params* is a list of key=value pairs that are provided additionally to that particular bus and have meanining only in the context of that particular bus.

The contructor from `BaseRobot` uses the method `processBus(businfo)`
You can use any of the classes defined in the `roboglia` or define your own specialized classes. The only restriction is that the code that makes the allocation of these classes needs to be aware of them. This is why it is required to setup your own subclass from `BaseRobot` and include in that module all the bus (and device by extension as we will see later) that are used by the robot. For instance, if your robot uses Dyanmixel buses, I2C bus and a video bus, then you could define your robot as follows::

    from roboglia.base import BaseRobot
    from roboglia.dyamixel import DynamixelBus, DynamixelServo
    from smbus2 import SMBus
    from cv2 import VideoCapture

    class MyRobot(BaseRobot):

        #
        # now the processing of the information
        # 

BaseDevice
^^^^^^^^^^

We'll start with the `BaseDevice`. This class represents a proxy for an actual device that the robot migh interact with. For this purpose the 