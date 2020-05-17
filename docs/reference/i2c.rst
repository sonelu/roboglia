==============
``i2c`` Module
==============

.. automodule:: roboglia.i2c

This module contains classes that are specific for interaction with I2C
devices.

*Buses*

.. autosummary::
   :nosignatures:
   :toctree: i2c

   I2CBus
   SharedI2CBus
   MockSMBus

*Devices*

.. autosummary::
   :nosignatures:
   :toctree: i2c

   I2CDevice

*Syncs*

.. autosummary::
   :nosignatures:
   :toctree: i2c

   I2CReadLoop
   I2CWriteLoop
