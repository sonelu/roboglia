===============
``base`` Module
===============

.. automodule:: roboglia.base

Classes in ``roboglia`` can be categorized in two groups in relation to their
position to the main robot class:

* **Downstream** classes: are classes that are located between the robot class 
  and the physical devices.

* **Upstream** classes are classes that expose the robot capabilities in a 
  uniform way like 'joints', 'sensors', 'moves', etc.
   
**Downstream**

The following classes from ``base`` module are provided for representing
various structural elements of a robot.

*Buses*

.. autosummary::
   :nosignatures:
   :toctree: base

   BaseBus
   FileBus
   SharedBus
   SharedFileBus

*Registers*

.. autosummary::
   :nosignatures:
   :toctree: base

   BaseRegister
   BoolRegister
   RegisterWithConversion
   RegisterWithThreshold

*Devices*

.. autosummary::
   :nosignatures:
   :toctree: base

   BaseDevice

*Threads and Loops*

.. autosummary::
   :nosignatures:
   :toctree: base

   BaseThread
   BaseLoop
   BaseSync
   BaseReadSync
   BaseWriteSync
   
**Middle**

.. autosummary::
   :nosignatures:
   :toctree: base

   BaseRobot
   JointManager

**Upstream**

The following classes from ``base`` module are provided for helping with
the synchronization of devices' values task.

*Joints*

.. autosummary::
   :nosignatures:
   :toctree: base

   PVL
   PVLList
   Joint
   JointPV
   JointPVL

*Sensors*

.. autosummary::
   :nosignatures:
   :toctree: base

   Sensor
   SensorXYZ