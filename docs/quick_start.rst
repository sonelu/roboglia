========================
``roboglia`` Quick Start
========================

The main idea behind the ``roboglia`` package is to provide developers with
reusable components that would require as little coding as possible to put
together the base of a robot.

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


Robot Definition File
---------------------

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
-----

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
-------

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
------

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
-------

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
------

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
-----

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
-------------

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


