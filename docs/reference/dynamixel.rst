====================
``dynamixel`` Module
====================

.. automodule:: roboglia.dynamixel

This module contains classes that are specific for interation with dynamixel
devices.

*Buses*

.. autosummary::
   :nosignatures:
   :toctree: dynamixel

   DynamixelBus
   ShareableDynamixelBus
   MockPacketHandler
   MockDynamixelBus

*Devices*

.. autosummary::
   :nosignatures:
   :toctree: dynamixel

   DynamixelDevice

*Registers*

.. autosummary::
   :nosignatures:
   :toctree: dynamixel

   DynamixelAXBaudRateRegister
   DynamixelAXComplianceSlopeRegister
   DynamixelXLBaudRateRegister

*Syncs*

.. autosummary::
   :nosignatures:
   :toctree: dynamixel

   DynamixelSyncReadLoop
   DynamixelSyncWriteLoop
   DynamixelBulkReadLoop
   DynamixelBulkWriteLoop
