.. _BaseRegister:

======================
``BaseRegister`` class
======================

Overview
========
.. currentmodule:: roboglia.base
.. autoclass:: BaseRegister

Methods
=======

Accessors
--------------

Custom getter / setter methods are provided for ``value`` that allows 
access to the external formatting of the register's data.

.. autosummary::
   :toctree: generated/

   BaseRegister.value

Conversions
-----------

.. autosummary::
   :toctree: generated/

   BaseRegister.valueToExternal
   BaseRegister.valueToInternal

Sync
----

.. autosummary::
   :toctree: generated/

   BaseRegister.write
   BaseRegister.read


.. toctree::
   :maxdepth: 2