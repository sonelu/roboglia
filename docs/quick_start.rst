========================
``roboglia`` Quick Start
========================

The main idea behind the ``roboglia`` package is to provide developers with
reusable components that would require as little coding as possible to put
together the base of a robot.

There are a couple of ways we could write code using ``roboglia``. To understand
better how it works we will first do things manually, one by one, and then move
to YAML templates, a solution more suitable for complex robots.

The Basic Ingredients
---------------------

The minimum that we need when working with ``roboglia`` is a **Bus** and a
**Device**. Ultimately there is little sense of using this framework if
there are no devices to work with and every device needs a bus to control the
communication.

I will choose the case of an actual robot that uses an older version of the
control board that is now `SPR2005 <https://github.com/sonelu/SPR2005>`_
HAt for Raspberry Pi. It uses a SC16IS762 chip to produce two serial ports
that are then processed to produce the Dynamixel-compatible semi-duplex
bus. These two buses are reflected at the system level as ``/dev/ttySC0`` and
``/dev/ttySC1``. Let's see how we can use them.

Creating a Bus Manually
^^^^^^^^^^^^^^^^^^^^^^^

Since we are dealing with Dynamixel devices we will create a
:py:class:`~roboglia.dynamixel.DynamixelBus` like this:

.. code-block:: Python

  >>>from roboglia.dynamixel import DynamixelBus, DynamixelDevice
  >>>bus = DynamixelBus(name='sc1', port='/dev/ttySC1', baudrate=10000000, protocol=1.0, rs485=True)

I know that the devices I want to work with are using the bus created on the
``/dev/ttySC1`` so I am using this as a port. I also know that the devices
have been configured for communication at 1Mbs and that they are older
`AX-12A <https://emanual.robotis.com/docs/en/dxl/ax/ax-12a/>`_ servos that
use protocol 1.0. The last parameter tels the bus to configure the serial
port with rs485 support, something that the add-on board requires in order to
work correctly. The code above will take care of setting up the port handler
and the protocol handler according to the parameters given, so that we
only have to interact with one single object, our ``bus`` instance.

We can now open the bus (don't forget this; operations will not be possible
if the bus is closed and errors will be logged), and let's scan for devices.
The ``DynamixelBus`` class has a convenient method
:py:meth:`~roboglia.dynamixel.DynamixelBus.scan` that will tell us the IDs of
devices connected on the bus:

.. code-block:: Python

  >>>bus.open()
  >>>bus.scan()
  [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

Great! I told us that there are 10 servos on that bus (if you're wandering they
are actually the 2 servos for the head pan / tilt and 4 servos for each hand of
the robot).

Creating a Device Manually
^^^^^^^^^^^^^^^^^^^^^^^^^^

Let us do some work with servo 2 (this is the head pan servo). The easiest
way to interact with it is by setting up a surrogate object, a
``DynamixelDevice`` that will handle all the commands for us.

.. code-block:: Python

  >>>d02 = DynamixelDevice(name='d02', bus=bus, dev_id=2, model='AX-12A')
  >>> d02
  <roboglia.dynamixel.device.DynamixelDevice object at 0x7f9e57eaf0>

Nice, we now have a device that acts as a proxy for the real servo. The
constructor for the servo has done some serious heavy lifting in the background
and prepared this object to be as simple to use as possible. For instance the
``model='AX-12A'`` parameter indicated to the constructor to look for a
file that describes the structure of such a device. There are lots of such
definition files that describe the registers and convenience conversions
and checks that should be done when reading or writing from them. What you
need to understand at this moment is just that the ``d02`` object has now
a large list of attributes corresponding to all these registers and that you
can read or write information through them. One convenient feature for a Device
in ``roboglia`` is that the ``__repr__`` method has been overloaded and we
could get all these registers in one view. Let's see:

.. code-block:: Python

  >>> print(d02)
  Device: d02, ID: 2 on bus: sc1:
          [model_number]: 12 (12)
          [firmware]: 24 (24)
          [id]: 2 (2)
          [baud_rate]: 1000000 (1)
          [return_delay_time]: 0.0 (0)
          [cw_angle_limit]: 0 (0)
          [ccw_angle_limit]: 1023 (1023)
          [temperature_limit]: 70 (70)
          [min_voltage_limit]: 6.0 (60)
          [max_voltage_limit]: 14.0 (140)
          [max_torque]: 1023 (1023)
          [status_return_level]: 2 (2)
          [alarm_led]: 36 (36)
          [shutdown]: 36 (36)
          [torque_enable]: True (1)
          [led]: False (0)
          [cw_compliance_margin]: 1 (1)
          [ccw_compliance_margin]: 1 (1)
          [cw_compliance_slope]: 5 (32)
          [ccw_compliance_slope]: 5 (32)
          [goal_position]: 512 (512)
          [moving_speed]: 0 (0)
          [torque_limit]: 1023 (1023)
          [present_position]: 510 (510)
          [present_speed]: 0 (0)
          [present_load]: 0 (0)
          [present_voltage]: 12.1 (121)
          [present_temperature]: 42 (42)
          [registered_instruction]: False (0)
          [moving]: False (0)
          [locking]: False (0)
          [punch]: 32 (32)
          [cw_angle_limit_deg]: -150.14662756598239 (0)
          [cw_angle_limit_rad]: -2.620553011792073 (0)
          [ccw_angle_limit_deg]: 149.8533724340176 (1023)
          [ccw_angle_limit_rad]: 2.6154347441909165 (1023)
          [max_torque_perc]: 100.0 (1023)
          [alarm_instruction_error]: False (36)
          [alarm_overload_error]: True (36)
          [alarm_checksum_error]: False (36)
          [alarm_range_error]: False (36)
          [alarm_overheating_error]: True (36)
          [alarm_anglelimit_error]: False (36)
          [alarm_inputvoltage_error]: False (36)
          [shutdown_instruction_error]: False (36)
          [shutdown_overload_error]: True (36)
          [shutdown_checksum_error]: False (36)
          [shutdown_range_error]: False (36)
          [shutdown_overheating_error]: True (36)
          [shutdown_anglelimit_error]: False (36)
          [shutdown_inputvoltage_error]: False (36)
          [cw_compliance_margin_deg]: 0.29325513196480935 (1)
          [cw_compliance_margin_rad]: 0.005118267601156392 (1)
          [ccw_compliance_margin_deg]: 0.29325513196480935 (1)
          [ccw_compliance_margin_rad]: 0.005118267601156392 (1)
          [goal_position_deg]: 0.0 (512)
          [goal_position_rad]: 0.0 (512)
          [moving_speed_rpm]: 0.0 (0)
          [moving_speed_dps]: 0.0 (0)
          [moving_speed_rps]: 0.0 (0)
          [torque_limit_perc]: 100.0 (1023)
          [present_position_deg]: -0.5865102639296187 (510)
          [present_position_rad]: -0.010236535202312784 (510)
          [present_speed_rpm]: 0.0 (0)
          [present_speed_dps]: 0.0 (0)
          [present_speed_rps]: 0.0 (0)
          [present_load_perc]: 0.0 (0)

Understanding Registers
^^^^^^^^^^^^^^^^^^^^^^^

The **Register** is the most elemental part in ``roboglia``. All registers
descend from :py:class:`~roboglia.base.BaseRegister` that keeps a raw
representation of the data in ``int_value`` and provides a setter / getter
property pair as ``value`` that allows you to interact with the register in
a more "natural" way. By default for a ``BaseRegister`` the internal value
``int_value`` and the ``value`` are the same, like in the case of the registers
``model_number`` and ``firmware`` (to name a few) above. The first number is
the ``value`` (external or human readable value) while the value in brackets
is the internal value ``int_value``.

But subclasses of ``BaseRegister`` build up on this to provide more useful
support. For instance ``baud_rate`` register is a
:py:class:`~roboglia.base.RegisterWithMapping` that allows you to provide a
static, finite mapping between the internal representation of the register's
content and the external one. In this case the human readable value is
1000000 (1Mbs) while the internal value is 1. The logic for this is taken
from the `producer's specification <https://emanual.robotis.com/docs/en/dxl/ax/ax-12a/#baud-rate-4>`_
and is included in the `YAMl file that describes the device <https://github.com/sonelu/roboglia/blob/master/roboglia/dynamixel/devices/AX-12A.yml>`_.

An even more interesting case is the one involving the positional registers
like ``present_position``. For this particular servo, the register contains
values between 0 and 1023 with 0 representing the servo all the way to the
counter-clockwise side while 1023 representing the servo all to way to the
clockwise side, all across 300 degrees of movement (if you're curious the
specification are `here <https://emanual.robotis.com/docs/en/dxl/ax/ax-12a/#present-position-36>`_).
``roboglia`` not only allows you define convenient transformations between
these representation through the use of :py:class:`~roboglia.base.RegisterWithConversion`
class, butt you can actually have multiple **clone** registers for the same
address, each one with it's own conversion and only one holding the actual
``int_value`` that is synchronized with the actual device. For instance
``present_position`` register above reflects the raw register while
``present_position_deg`` and ``present_position_rad`` reflect the same value
but in degrees, respective radians, with 0 centered at 512 internal value.

Let's see practically how this works. First we'll use the raw register for
the ``goal_position``:

.. code-block:: Python

  >>>d02.goal_position.value = 450

This will do a lot of things in the background:

- it will call the setter for value with 450
- the setter will check if the provided value falls between the ``minimum`` and
  ``maximum`` attributes of the register and will clip if necessary
- it will then store the value in ``int_value``
- it will call the communication bus to synchronize the value to the device,
  effectively writing that value into the physical register of the device.

.. warning:: Please make sure that you use the ``value`` property and not
   assign the value directly to the ``goal_position`` like this:

   .. code-block:: Python

    d02.goal_position = 450

   This will completely overwrite the ``Register`` object that ``d02.goal_position``
   points to with an integer and you will ruin completely the functioning of
   the ``d02`` object. We will address this in a subsequent release so that
   assigning a value directly to a device property that is a register will
   trigger an error.

We should see the servo moving to the position represented by the 450  value.
It would be nice if we could see this value in degrees, isn't it? Well, we have
the register ``goal_position_deg`` that does exactly that:

.. code-block:: Python

  >>>d02.goal_position_deg.value
  -18.18181818181818

We see it is approximately 18 degrees clock-wise. We can use the same register
to set a more user friendly position:

.. code-block:: Python

  >>>d02.goal_position_deg.value = 20

Now the servo has moved 40 degrees in CCW direction. Because the velocity
control is now 0 (see the ``moving_speed`` register meaning moves
will be as fast as possible) the moves are very sharp and sudden. We can change
that and, because we have registers that provide us with conversions of
internal representations to degrees-per-second (dps), radians-per-seconds (rps)
or rotations-per-minute (rpm). Let's use the degrees-per-second and move
again the servo:

.. code-block:: Python

  >>> d02.moving_speed_dps.value = 10
  >>> d02.goal_position_deg.value = -20

We should now see the servo moving back to the pervious position but taking
approximately 4 seconds to get there (there are 40 degrees of movement and
we are setting the speed to 10 degrees per second).

There are many other classes of registers that allow you to manipulate the
most common type of data present in devices and I encourage you have a look
on the :ref:`API_Reference`

Robot Definition File
---------------------

Let's suppose we just finished building a robot that we we would like to
use with ``roboglia``. Let's say that the robot is just a pan-tilt with
an IMU (inertial measurement unit) on top.

Within our code we could create all the instances of the robot components
by calling the class constructors with the specifics of that component. But
there is a more convenient way: use a **robot definition file**, a YAML
document that describes the structure and the components of the robot. With
such a definition file available (and we will discuss it's content later)
our code will simply call the :py:meth:`~roboglia.base.BaseRobot.from_yaml`
class method of :py:class:`roboglia.base.BaseRobot`:

.. code-block:: Python
  :linenos:

  from roboglia.base import BaseRobot
  import roboglia.dynamixel
  import roboglia.i2c

  robot = BaseRobot.from_yaml('path/to/my/robot.yml')
  robot.start()

  ...
  # use our robot
  ...

  robot.stop()

So, what is in the **robot definition file**? Let's see how such a file would
look like for our example robot:

.. code-block:: YAML
   :linenos:

    my_awesome_robot:

      buses:
        dyn_bus:
          class: SharedDynamixelBus
          port: '/dev/ttyUSB0'
          baudrate: 1000000
          protocol: 2.0

        i2c0:
          class: I2CBus
          port: 0

      devices:
        
        d01:
          class: DynamixelDevice
          bus: dyn_bus
          dev_id: 1
          model: XL-320

        d02:
          class: DynamixelDevice
          bus: dyn_bus
          dev_id: 2
          model: XL-320
      
        imu_g:
          class: I2CDevice
          bus: i2c0
          dev_id: 0x6a
          model: LSM330G

        imu_a:
          class: I2CDevice
          bus: i2c0
          dev_id: 0x1e
          model: LSM330A
          
      joints:
        pan:
          class: JointPVL
          device: d01
          pos_read: present_position_deg
          pos_write: goal_position_deg
          vel_read: present_speed_dps
          vel_write: moving_speed_dps
          load_read: present_load_perc
          load_write: torque_limit_perc
          activate: torque_enable
          minim: -90.0
          maxim: 90.0

        tilt:
          class: JointPVL
          device: d02
          inverse: True
          pos_read: present_position_deg
          pos_write: goal_position_deg
          vel_read: present_speed_dps
          vel_write: moving_speed_dps
          load_read: present_load_perc
          load_write: torque_limit_perc
          activate: torque_enable
          minim: -45.0
          maxim: 90.0

      sensors:
        accelerometer:
          class: SensorXYZ
          device: imu_a
          x_read: out_y_deg
          x_inverse: True
          y_read: out_z_deg
          z_read: out_x_deg
          z_offset: 45.0

        gyro:
          class: SensorXYZ
          device: imu_g
          x_read: out_y_deg
          x_inverse: True
          y_read: out_z_deg
          z_read: out_x_deg
          z_offset: 45.0

      groups:
        dev_servos:
          devices: [d01, d02]

        dev_imu:
          devices: [imu_g, imu_a]

        all_joints:
          joints: [pan, tilt]

      syncs:
        read_pslvt:
          # read position, speed, load, voltage, temperature
          class: DynamixelSyncReadLoop
          group: dev_servos
          registers: [present_position, present_speed, present_load, 
                      present_voltage, present_temperature]
          frequency: 50.0
          throttle: 0.25

        write_psl:
          # write position, speed, load
          class: DynamixelSyncWriteLoop
          group: dev_servos
          registers: [goal_position, moving_speed, torque_limit]
          frequency: 50.0
          throttle: 0.25

        read_imu:
          class: I2CReadLoop
          group: dev_imu
          registers: [out_x, out_y, out_z]
          frequency: 25.0

      manager:
        frequency: 50.0
        throttle: 0.25
        group: all_joints
        p_function: mean
        v_function: max
        ld_function: max


I know, it's a pretty long listing, but it's not that hard to understand it.
We will now go component by component and explain it's content.

As you can see the YAML file is a large dictionary that includes one key-value
pair: the name of the robot "my_awesome_robot" and the components of this robot.

.. note:: At this moment ``roboglia`` only supports one robot definition from
   the YAML file and will only look at the information for the first key-value
   pair. If multiple values are defined ``roboglia`` will issue a warning.


The values part of that dictionary is in itself a dictionary of robot components
identified by a number of keywords that reflect the parameters of the robot
class constructor (we'll come to this in a second). We will look at them in
the next sections.

Buses
^^^^^

The first is the ``busses`` section. This describes the communication
channels that the robot uses to interact with the devices. In our framework
buses deal not only with the access to the physical medium (opening, closing,
reading, writing) but also deals with the particular communication protocol
used by the device. For instance the packets used by Dynamixel devices have a
certain structure and follow a number of conventions (ex. command codes,
checksums, etc.).

At this moment there are several communication buses supported by ``roboglia``,
the important ones for our robot are: Dynamixel and I2C. The first one is used
to communicate with the servos while the last one will be
used for the communication with the IMU.

If you look in the listing above you see that the buses are described in a
dictionary, with each bus identified by a **name** and a series of attributes.
All these attributes reflect the constructor parameters for the class that
implements that particular bus. For instance the class
:py:class:`~roboglia.i2c.I2CBus` inherits the parameters from
:py:class:`~roboglia.base.BaseBus` (**name**, **robot**, **port** and **auto**)
while adding a couple of it's own (**mock** and **err**). The **name** of the
bus will be retrieved from the key of the dictionary, in our case they will
be "dyn_upper", "dyn_lower" and "i2c0".

.. warning:: When naming the objects in the YAML file make sure that you
   use the same rules that you use for naming variables in Python: use only
   alphanumeric characters and "_" and make sure they do not start with a
   digit. In all cases the names have to be hashable and Python must be able
   to use them as dictionary keys. In some cases they even end up as instance
   attributes (ex. the registers of a device), in which case they should be
   defined with the the same care as when naming class attributes.

For details of attributes for each type of bus please see the *robot YAML
specification* documentation.

Devices
^^^^^^^

The second important elements are the physical **actuators** and **sensors**
that the robot employs. In ``roboglia`` they are represented by **devices**, the
class of objects that act as a surrogate of the real device and with which the
rest of the framework interacts. Traditionally these surrogate objects were
created by writing classes that implemented the specific behavior of that
device, sometimes taking advantage of inheritance to efficiently implement
common functionality across a range of devices. While this is still the case
in ``roboglia`` (on a significantly larger scale) the very big difference is
that we use **device definition files** (as YAML files) to describe the
type of a device. A more generic class in the framework will be
responsible for creating an instance from the information provided in these
definition files without having to write additional code or to subclass
any "device" class.

For our robot ``roboglia`` already has support for XL-320 devices and we plan
to leverage this. The IMU inside the robot is an LSM330 accelerometer /
gyroscope that is also included in the framework. In general all devices
have a **name** (the key in the dictionary), a **class** identifier,
the **bus** they are attached to, a **device id** (``dev_id`` is used in
the YAML as ``id`` is a reserved word in Python and we should avoid it as an
attribute name) and a **model** that indicates the type of device from that
class. Depending on the device there might be additional mandatory
or optional attributes that you can identify from the *robot YAML
specification* documentation and the specific class constructor.

The device **model** is in itself implemented through a YAML file (a 
**device definition**) that describes the **registers** contained in the
device and adds a series of useful value handling routines allowing for
a more natural representation of the register's information. For more details
look at the devices defined in the ``devices/`` directory in each of the
class of objects (dynamixel, i2c, etc.) or look at the *YAML device
specification* documentation. You can find out more about techniques like
*clone* registers (that access the same physical device register, but provide
a different representation of the content, like in the case of a positional
register in an actuator that could have clones for the position in degrees or
in radians, or the case of a bitwise status register that can have several
clones with masked results representing the specific bit).

Joints
^^^^^^

The actuator devices present in a robot can be of various types and with
various capabilities. **Joints** aim to produce an uniform view of them
so that higher level operations (like move controllers and scripts) can
be run without having to keep in track of all devices' technicalities.

There are 3 types of joints defined in ``roboglia``: the simply named ``Joint``
only deals with the **positional** information. For this it uses two attributes that
identify the device's registries responsible for reading and writing its
position. Please note that the units of measurement that are used by that
register are automatically inherited, so if the register represents the position
in degrees then the joint will also have the same unit of measurement. There
are not unit conversions for joints, specifically because those can and
should be incorporated at the register level and to avoid multiple layers of
conversions. Optionally a ``Joint`` can have a specification for an
**activation** register that controls the torque on the device, if omitted
the joint is assumed to be active at all times. Also, optional, a joint
can have an **inverse** parameter that indicates the coordinate system
of the joint is inverse to the one of of the device, an **offset** that
allows you to indicate that the 0 position of the joint is different from the
one of the device as well as a **minimum** and a **maximum** range defined
in the joints coordinate system (before applying *inverse* and *offset*) to
limit the commands that can be provided to the joint.

``JointPV`` includes **velocity** control on top of the positional control
by including the reference to the device's registries that read, respectively
write the values for the joint velocity. ``JointPVL`` adds **load** control
(or torque control if you want) to the joint, creating a complete managed
joint.

The advantage of using joints in your design is that later you can use higher
level constructs (like ``Script`` and ``Move`` to drive the devices and produce
complex patterns.

Sensors
^^^^^^^

Sensors are similar to Joints in the sense that they abstract the information
stored in the device;s registers and provide a uniform interface for accessing
this data.

At the moment there are 2 flavours of Sensors, the simply called
:py:class:`~roboglia.base.Sensor` that allows the presentation of a single
value from a device and a :py:class:`~roboglia.base.SensorXYZ` that presents
a triplet of data as X, Y, Z, suitable for instance for our accelerometer / 
gyroscope devices.

Like Joints, the Sensors can provide specifications for an **activate** register
and can indicate an **inverse** and **offset** parameters (for SensorXYZ there
is one of those for each axis). Interestingly, you can can assign the device's
registers in a different order than the one they are represented internally
in order to compensate for the position of the device in the robot. In our
example you can see that the sensor's X axis is provided by the device's Y axis
and that the representation is inverse, reflecting the actual position of the
sensor on the board in the robot.

Groups
^^^^^^

Groups are ways of putting together several devices, or joints with the
purpose of having a simpler qualifier for other objects that interact with
them, like `Syncs`_ and `Joint Manager`_.

The components of the groups can be a list of **devices**, **joints** or
other groups, which is very convenient when constructing a hierarchical
structure of devices, for instance for a humanoid robot where you can define
a "left_arm" group and a "right_arm" and then group them together under an
"arms" group that in turn can be combined with a "legs" groups, etc. This
allows for a very flexible structuring of the components so that the access
to them can be split according to need, while still retaining the overall
grouping of all devices if necessary.

Syncs
^^^^^

The device classes that are instantiated by the BaseRobot according to the
specifications in the robot definition file are only surrogate representations
of the actual devices. Each register defined in the device instance has an
``int_value`` that reflects the internal representation of the register's value.
Typically any access to the ``value`` property of that register will trigger
a read (if the accessor is a get) of the register value form the device through
the communication bus, or a write if the (accessor is a set). This works fine
for occasional access to registers (ex. the activation of a joint because we
normally do that very rarely) but is not suitable for information that needs
to be exchanged often. In those cases the buses provide (usually) more
efficient communication methods that bundle multiple registers or even multiple
devices into one request.

This facility is encapsulated in the concept of a **Sync**. The Sync is
a process that runs in it's own **Thread** and performs a bus bulk operation
(either read or write) with a given **frequency**. The sync needs the group
of devices and the list of registers that needs to synchronize. A sync is
quite complex and include self monitoring and adjustment of the processing
frequency so that the target requested is kept (due to the fact that we
run Unix kernel there is no real-time guarantee for the thread execution
and actual processing frequencies can vary wildly depending on the system
performance) and support ``start``, ``stop``, ``pause`` and ``resume``
operations.

When syncs start they place a flag ``sync`` on the registers that are subject
to sync replication and ``value`` properties no longer perform read or write
operations, instead simply relying on the data already available in the
register's ``int_value`` member.

Joint Manager
^^^^^^^^^^^^^

While having the level of abstraction that is provided by Joint and it's
subclasses is nice, there is another problem that usually robots have to deal
with: several streams of commands for the joints. It is common, for complex
robot behavior, to have streams that might provide different instructions to
the joints, according to their purpose. If they are not mitigated the robot
can get in an oscillatory state and can be destabilized. Sometimes, one of the
streams provides a "correction" message to the joints like in the case of a
posture control loop that adjusts the joints to balance the robot while
still allowing the main script or move to run their course.

For this a robot has one, and only one, **Joint Manager** object a construct
that is responsible for mitigating the commands and transmitting an
aggregated signal to the joints.


The **Joint Manager** is instantiated when the robot starts and runs (like
the `Syncs`_ above) in a Python **thread** for which you have the possibility
to specify a **frequency** as well as all the other monitoring parameters.
When moves or scripts need to provide their requests, they do not interact
directly with the joints, but submit these requests to the Joint Manager.
Periodically the Joint Manager processes these requests and compounds a
unique request that is passed to the joints under it's control.

The Joint Manager allows you to specify the way the requests are aggregated
for each of the joints' parameters: position, velocity, load. By default all
use ``mean`` over the request values (for that joint and particular parameter)
but you can use other aggregation functions, like we used ``max`` in our
example for velocity and load, meaning that if multiple orders for the same
joint are received the position is averaged, but velocity and load attributes
are determined by using the maximum between the request.

Moving the Robot
----------------

Now that the robot is loaded and ready for action how do you control it?
``roboglia`` offers two low level interaction methods that can be exploited
into more complex behavior:

- scripted behavior: this is represented by predefined actions that are
  described in a "Script" and can be executed on command

- programmatic behavior: this is more complex interaction that is determined
  programmatically, for instance as a result of running a ML algorithm that
  dynamically produce the joint commands

Scripts
^^^^^^^

**Scripts** are sequences of joint commands that can be described in an YAML
file. ``roboglia`` offers the support for loading of a script from a file,
preparing all the necessary constructs and executing it on command. The
actual execution of the script is performed in a dedicated thread and
therefore inherits the other facilities provided by the
:py:class:`~roboglia.base.Thread` like early stopping, pause and resume.

Here is an example of a script:

.. code-block:: YAML
  :linenos:

  script_1:

    joints: [j01, j02, j03]
    defaults:
      duration: 0.2

    frames:

      start:
        positions: [0, 0, 0]
        velocities: [10, 10, 10]
        loads: [100, 100, 100]

      frame_01: [100, 100, 100]
      frame_02: [200, 200, 200]
      frame_03: [400, 400, 400]
      frame_04: [nan, nan, 300]
      frame_05: [nan, nan, 100]

    sequences:

      move_1:
        frames: [start, frame_01, frame_02, frame_03]
        durations: [0.2, 0.1, 0.2, 0.1]
        times: 1

      move_2:
        frames: [frame_04, frame_05]
        durations: [0.2, 0.15]
        times: 3

      empty:
        times: 1

      unequal:
        frames: [frame_01, frame_02]
        durations: [0.1, 0.2, 0.3]
        times: 1

    scenes:

      greet:
        sequences: [move_1, move_2, move_1.reverse]
        times: 2

    script: [greet]

A script is produced by layering a number of elements, pretty much like a
film script. To start with, the Script defines a number of contextual
elements that simplify the writing of the subsequent components:

- joints: here the joints that the script plans to use a listed in order.
  The names of the joints have to respect those defined in the robot definition
  file and you must ensure that the joints have been advertised by the
  Joint Manager. Only joints defined in the Joint Manager can be controlled
  through a script. Defining the joints here in an ordered list simplifies
  later the writing of the **Frames**.

- defaults: helps with defining values that will automatically be used in
  case no more specific values are provided later in the other components.
  This helps with eliminating the need to write repetitive information in
  the script.   

The most basic structure is the **Frame**: this represents a particular
instruction for the joints. A frame has a **name** (ex. "start" in the code
above) and a dictionary of **positions**, **velocities** and **load** commands
all provided as lists representing the joints in the exact order defined
at the beginning of the file. You can use ``nan`` (not a number) to indicate
that for a particular joint that value is not provided and should remain the
one the joint already has. You can also provide the lists shorter than the
number of joints and the processing will assume all the missing one are ``nan``
and pad the list accordingly to the right. Providing any of the control
elements (position, velocity, load) is optional, so you  can skip any of them
if you don't need to control that item. To make things even simpler, as
most of the times you only want to provide positional instructions, you
can do that by just supplying a list of positions instead of the dictionary 
and the code will assume those are "position" instructions. You can see that
used for "frame_01", "frame_02", etc.

You can group the frames in a **Sequence**. This is an ordered list of Frames
that have associated transition **durations** and additionally can be repeated
a number of **times** to produce the desired effect. If durations are not
provided for a sequence, the ones defined in the **default** section are used.

Sequences are grouped in **Scenes** were you can specify an order for the
execution Sequences and, additionally, you can use the qualifier **reverse**
to indicate that a particular Sequence should be executed in the reverse order
of definition. Like Sequences, Scenes can be executed a number of **times**
by using the qualifier with the same name.

Finally a list of Scenes are combined in a **Script** that also can specify a
repetition parameters **times** like the previous components.

Once a Script is prepared in a YAML file, working with it is very simple.
You load the definition with :py:meth:`~roboglia.move.Script.from_yaml`
and then simply call the :py:meth:`~roboglia.move.Script.start` method
to initiate the moves. The Script will run through all the Frames as and
will gracefully complete when the sequence of instructions is completed.
During this time you can ``pause`` the Script and ``resume`` it or you can
prematurely ``stop`` it if needed. Please be aware that the Script sends all
the commands to the `Joint Manager`_ and as a result you can combine multiple
Script executions in the same time, even if they may have overlapping joints.

Here is an example of running the Script defined above under a ``curses``
loop:

.. code-block:: Python
  :linenos:

  import curses
  from roboglia.move import Script

  def main(win, robot):
    win.nodelay(True)
    key = ""
    win.clear()
    script = Script.from_yaml(robot=robot, file_name='my_script.yml'
    while(True):
      try:
        key = win.get_key()
        if str(key) == 's':
          # start the Script; if already running it will restart!
          script.start()
        elif str(key) == 'x':
          # stop the script
          script.stop()
        elif str(key) == 'p':
          script.pause()
        elif str(key) == 'r':
          script.resume()
        elif str(key) == 'q':
          # stops the main loop
          script.stop()
          break
      except Exception as e:
        # no input
        pass

  # initialize robot
  ...

  curses.wrapper(main)

Of course this is just a quick example, you are free to incorporate the
functionality as needed in you main processing logic of your robot, but keep
in mind how easy it is to control the execution of a script with these 4
methods.

Moves
^^^^^

**Moves** allows you to control the robot joints using arbitrary commands
that are produced programmatically. You will normally subclass the
:py:class:`~roboglia.move.Motion` class and implement the methods that you
need in order to perform the actions.

For instance the following code would move the head of a robot using
a sinusoid trajectory:

.. code-block:: Python
  :linenos:

  from roboglia.move import Motion
  from math import sin, cos

  class HeadMove(Motion):

      def __init__(manager,       # robot manager object needed for super()
                  head_yaw,       # head yaw joint
                  head_pitch,     # head pitch joint
                  yaw_ampli= 60,  # yaw move amplitude (degrees)
                  pitch_ampli=30, # pitch move amplitude (degrees)
                  cycle = 5):     # duration of a cycle
          super().__init__(name='HeadSinus', frequency=25.0,
                          manager=manager, joints=[head_yaw, head_pitch])
          self.head_yaw = head_yaw
          self.head_pitch = head_pitch
          self.yaw_ampli = yaw_ampli
          self.pitch_ampli = pitch_ampli
          self.cycle = cycle

      def atomic(self):
          # calculates the sin and cos for the yaw and pitch
          sin_pos = sin(self.ticks / self.cycle) * self.yaw_ampli
          cos_pos = cos(self.ticks / self.cycle) * self.pitch_ampli
          commands = {}
          commands[self.head_yaw.name] = PVL(sin_pos)
          commands[self.head_pitch.name] = PVL(cos_pos)
          self.manager.submit(self, commands)


And in the main code of your robot you can use it as follows:

.. code-block:: Python
  :linenos:

  from roboglia.base import BaseRobot

  robot = BaseRobot.from_yaml('/path/to/robot.yml')
  robot.start()

  ...

  head_motion = HeadMotion(robot.manager,
                           robot.joints['head_y'], robot.joints['head_p'])
  head_motion.start()

  ...

  robot.stop()

