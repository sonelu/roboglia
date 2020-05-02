Using ``roboglia``
==================

``roboglia`` is a framework that helps developers with the setup of robots 
in a more reusable fashion. Most of the times the creation of robots involve 
integrating actuators, sensors, cameras and microphones, periodically accessing 
the information provided by these or supplying commands according to the desired
activities.

The name `roboglia` is derived from the glial cells present in the brian. 
Their role is to support the neurons in their functions by supplying them 
with nutirients, energy and disposing of the residues produced during the 
execution of their activities. The analogy is that ``roboglia`` provides this 
boring, but very complex activity of putting together the specific functions 
of the physical devices used in robots in order to provide a more accessible 
high-level representation of the robot for the use of the "smart" control logic
that sits at the top.

With ``roboglia`` some low level functionality, currently split across multiple
libraries and frameworks are put together and integrated in an extensible way 
making it easier for developer to focus on the higher level functionlity, 
rather than gritty details.

.. note::

    When using a IMU device developers typically inspect the documentation of 
    the chip or look for some example code and incorporate that in their 
    particular project. It makes it very difficult when moving from a device 
    to another or when the main controller or libraries are changed. With 
    ``roboglia`` this is handled in the following way:
    
    * first a ``Bus`` is instantiated with information from a robot definition 
      (an YAML) file, using an existing class from ``roboglia`` or a custom 
      defined one in case these are not enough. In this example most likely 
      the bus woould be an ``I2CBus`` which is provided out of the box in 
      ``roboglia``.
    * the robot definition file then contains information about the devices 
      used and their association with the buses. In our example the device 
      will be an ``I2CDevice`` and ``roboglia`` frameowork will construct 
      the specific instance of this device by resorting to a *device 
      defintion file*.  Such a device description is produced in YAML and 
      lists the registers of the device each with  information like name, 
      the address where it is accessed,size. The register is associated 
      with a class that provides convenient transformation of the 
      information in the registers in an external format. Developers have 
      access to sevaral common classes in ``roboglia`` but it is also very 
      simple to extend the framework by writing custom register classes.
    * once the setup of the device is ready the robot defintion can provide 
      details about a syncronization loop that will be run in a separate 
      thread in order to read / write information to the physical device 
      leveraging those devices and protocols that provide improved efficiency 
      when accessing data in bulk. Of course it is still possible and the 
      framework will default to this, to read / write synchronously each 
      time when we are interested to access the information a register.  
    
All in all the approach described above makes it possible to define and run 
a complete robot only by preparing or reusing existing defintion files without 
writing any code!

In the next sections we will take you step by step through the modeling of a 
robot and explain the functionality provided by ``roboglia`` to help you with 
this activity.

Creating a robot
----------------

A ``robot`` is ultimatelly a collection of devices that are either providing or are provided information. A higher level control mechanism uses the information provided by the devices and produces control sequences that are passed to the device.

You would normally create a robot instance by instantiating a ``BaseRobot`` class. There is very little reasons why would need to subclass ``BaseRobot`` as we will see shortly. You will normally create this by providing a YAML description of the structure of your robot.

.. code-block:: python
   :linenos:

    from roboglia.base.robot import BaseRobot

    robot = BaseRobot.from_yaml('my_robot_definition.yml')
    ...

This class method simply loads the YAML definition into a dictionary and passes it to the ``BaseRobot`` constructor who parses it and instantiate the various components of the robot. This makes it very easy to adapt the particulars of your robot without needing to change the source code. 

You might have noticed that the ``BaseRobot`` constructor takes a single parameter, a  dictionary:

.. code-block:: python
   :linenos:

    class BaseRobot():

        def __init__(self, init_dict):
            ...

This is a common pattern in ``roboglia`` and before we look at the work that the particular constructor for ``BaseRobot`` does, let's make a short detour to discuss this  approach of using just one ``init_dict`` by most of the classes in ``roboglia``.


The use of ``init_dict`` in class constructors
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Most of the times when a constructor is defined in Python a list of parameters is provided in the signature like this:

.. code-block:: python
   :linenos:

    def __init__(self, name, path, min, max):
        ...

In ``roboglia`` the objects tend to be very complex with 10-15 parameters, some times even more, translating into long signatures for constructors. That makes it very hard to use and maintain code, with an added necessity to provide named parameters in calls to avoid confusions. When making changes to the framework (as is it very easy to decide to add an additional component for one object) a lot of refactoring is needed in the subclasses and calling code to keep things alogned. 

In addition, most of the times the construction of these objects is made using data from YAML files that are read in Python standard structures like dictionaries and lists. We therefore used an approach where the information from the description files (typically a ``dict``) is passed alone in the constructor. The constructor then processes the information according to the specific needs, like in the following example from ``BaseRegister``:

.. code-block:: python
   :linenos:

    def __init__(self, init_dict):
        self.name = init_dict['name']
        self.device = init_dict['device']
        if 'address' not in init_dict:
            mess = f'No address specified for register {self.name}. All registers must have an address speficied.'
            logger.critical(mess)
            raise KeyError(mess)
        self.address = init_dict['address']
        # optionals
        self.size = init_dict.get('size', 1)
        if type(self.size) is not int:
            mess = f'Size for register {self.name} of device {self.device.name} must be an integer.'
            logger.critical(mess)
            raise ValueError(mess)
        self.min = init_dict.get('min', 0)
        if type(self.min) is not int:
            mess = f'Min for register {self.name} of device {self.device.name} must be an integer.'
            logger.critical(mess)
            raise ValueError(mess)
        self.max = init_dict.get('max', pow(2, self.size*8)-1)
        if type(self.min) is not int:
            mess = f'Min for register {self.name} of device {self.device.name} must be an integer.'
            logger.critical(mess)
            raise ValueError(mess)
        self.access = init_dict.get('access', 'R')
        if self.access not in ['R', 'RW']:
            mess = f'Access for register {self.name} of device {self.device.name} must be "R" or "RW".'
            logger.critical(mess)
            raise ValueError(mess)
        self.sync = init_dict.get('sync', False)
        if self.sync not in [True, False]:
            mess = f'Sync for register {self.name} of device {self.device.name} must be "True" or "False".'
            logger.critical(mess)
            raise ValueError(mess)
        self.default = init_dict.get('default', 0)
        if type(self.default) is not int:
            mess = f'Default for register {self.name} of device {self.device.name} must be an integer.'
            logger.critical(mess)
            raise ValueError(mess)
        self.int_value = self.default

In the example above `name` and `device` are provided and checkd by the device constructor, so are not rechecked, but you can see that other paramters are checked against their existence (ex. `address`) or their content. In case the data is bad and exception will be raised. This is an acceptable behaviour because these exceptions will be thrown only at the start of the work, when the structure of the robot is built and not during the operation of the robot. This makes it easier as all the logic is processed by the object being instantiated rather than the object calling the constructor.

 This it is possible to adjust the structure of the specification in order to correct the error. For instance if the section in YAML that is used to initialize the object above would be like this we would expect and exception to be thrown:

.. code-block:: YAML
   :linenos:

    name: reg_a
    device: dev_1
    min: 32
    max: 128

The correct form of the specification would be:

.. code-block:: YAML
   :linenos:

    name: reg_a
    device: dev_1
    address: 10
    min: 32
    max: 128

Another convenience introduced by using the ``init_dict`` technique is that the inheritance processing is much simpler. A ``FloatRegisterWithConversion`` is a subclass of the ``BaseRegister`` that introduces a **factor** and an **offset** used to translate the internal value in the register into an external representation (ex. a position in radians). This class constructor will simply call the ``super()`` constructor and then add the specific configuration:

.. code-block:: python
   :linenos:

    def __init__(self, init_dict):
        super().__init__(init_dict)
        if 'factor' not in init_dict:
            mess = f'No factor specified for register {self.name} of device {self.device.name}.'
            logging.critical(mess)
            raise KeyError(mess)
        self.factor = init_dict['factor']
        self.offset = init_dict.get('offset', 0)
        if type(self.offset) is not int:
            mess = f'Offset for register {self.name} of device {self.device.name} must be an integer.'
            logger.critical(mess)
            raise ValueError(mess)

If we decide to change something in the ``BaseRegister`` constructor it will be transparent for the subclass and we will not need to change anything here. The ``init_dict`` that is passed to the subclass will be passed to the ``BaseRegister`` and this will handle the additional logic.

What a robot contains
^^^^^^^^^^^^^^^^^^^^^

We return now to the initialization of the robot. The ``BaseRobot`` constructor will parse the ``init_dict`` and build the components. To make things easier to understand the components of a robot can be organised in two main groups: 

* **Downstream**: these are objects that sit between the robot and the actual physical elements of the robot

* **Upstream**: these are objects that provide additional layers of abstractization producing a uniform representation of the robot for the benefit of higher processing functions. For instance a ``Device`` will represent a physical servomotor (downstream) while a ``Joint`` will represent an abstractization of a robot DOF, connected to that ``Device``. This makes it very easy to define structures that present a heterogeneous higher representation (joints) even if the devices that are used in downstream are very different (for instance some could be servomotors, some could be steppers, etc.)

Here are the elements that ``BaseRobot`` identifies in an ``init_dict`` and initializes:

* **Buses**: are the physical communication medium that the robot uses to interact with devices. It includes protocol management and communication error handling.

* **Devices**: are the actual physical devices that the robot uses and they can come in many forms: actuators, sensors, imaging devices, etc.

* **Joints**: an upstream representation of a DOF of a robot. Allows you to decouple the higher representation of the DOF from the physical implementation and construct homogeneous joints sets based on heterogenous devices.

* **Groups**: are collections of objects that are defined for convenience. Some objects that will be mentioned bellow use groups for their processing. It is interesting to notice that the implementation of these in code is with ``sets`` and that when creating groups there are no limitations in groupping object; you can group devices and joints together if you want, although it is very unlikely you will find a use for that. Most of the object that use groups (ex. syncs) will check that the objects in the groups fulfill certain rules before accepting them.

* **Syncs**: are background processing tasks that exploit highly efficient functionalities to syncronize the information from the ``Device`` instances with the actual physical objects. Very often there are significant overheads in calling buses' methods to read / write information for a single register and using them in a loop over all the registers and all devices. Some communication methods allow bulk read and write of data for multiple devices and registers in one go, making it very suitable for replicating information at high speed.

Because the purpose of a robot is to make use of physical devices, the minimum you can have in a robot defintion is a bus and a device.

As mentioned above you would use the ``BaseRobot.from_yaml`` to construct the robot. Let's see how the YAML file would be structured.

Robot definition YAML
^^^^^^^^^^^^^^^^^^^^^

For starters we will use a minimal YAML file that uses one bus and device:

.. code-block:: YAML
   :linenos:

    buses:
        - name: busA
          class: FileBus
          post: /tmp/busA.log

    devices:
        - name: d01
          class: DynamixelDevice
          bus: busA
          id: 1
          model: AX-12A

The YAML contains two major parts: the bus list and the device list. When Python reads that YAML file it will represent the content in a dictionary with two elements with keys 'buses' and 'devices'. These are exactly the keys that the constructors are looking for in order to extract the information needed for initialization. The detail API provides more detail for each class that is build dynamically from an ``init_dict`` as to what keys are exepcted and which are defaulted.

Also notice that almost always one of the attributes that we need to specify for the objects is the ``class``. This is the name a of a class that is dynamically instantiable. What does this mean? It means that the class can be created by any piece of code without ``include``ing the module where the class was defined using a concept of **class factory**.

Class factory
^^^^^^^^^^^^^

Consider the following scenario: for the robot defintion file above the ``BaseRobot`` constructor will need to creare an instance of a ``FileBus`` and a ``DynamixelDevice``. Typically that means the module where ``BaseRobot`` sits needs to import the modules where these two classes are defined. What happens if you want to use a custom device class that you have written for some devices that are not covered in ``roboglia``? Well. since you cannot use the constructor of ``BaseReobot`` you will need to create a subclass of it, include the defintion of your device class and somehow handle that new device class. The framework would have needed to have a stub method to instantiate a class by name and your subclass will do the processing for the own classes or pass it to the ``super()`` to process the 'standard' ones. Although this is a perfectly possible scenario, it makes for a complex impementation: there are several classes that need to dynamically build from YAML (robot, device, move, etc.), so each would have to provide this stub method and will require subclassing in case of custom components.

Instead ``roboglia`` uses the concept of a ``class factory``. This is a very simple idea: in a common module (``factory.py``) we maintain a dictionary (initially empty) with classes that we want to be able to instantiate by name. The module then provides 2 global functions: 

* ``register_class(cls)`` this adds a class to the dictionary using the class name as key
* ``get_registered_class(class_name)`` this retrieves a class from the dictionary using the class name as key

The code looks like this:

.. code-block:: python
   :linenos:

    __registered_classes = {}

    def register_class(cls):
        if cls.__name__ not in __registered_classes:
            __registered_classes[cls.__name__] = cls

    def unregister_class(class_name):
        if class_name not in __registered_classes:
            raise KeyError(f'class {class_name} not registered with the factory')
        else:
            del __registered_classes[class_name]

    def get_registered_class(class_name):
        if class_name in __registered_classes:
            return __registered_classes[class_name]
        else:
            raise KeyError(f'class {class_name} not registered with the factory')

    def registered_classes():
        return __registered_classes

Now, when constructing an instance of an object we can be in a module that has no idea about the class. All we need is access to the class factory and the name of the class. The following example is from the code that creates the registers of a device after reading the structure of the registers from the device's file description:

.. code-block:: python
   :linenos:

    def __init__(self, init_dict):
        ...
        self.registers = {}
        for reginfo in model_ini['registers']:
            reg_class_name = reginfo.get('class', self.default_register())
            register_class = get_registered_class(reg_class_name)
            reginfo['device'] = self
            new_register = register_class(reginfo)
            self.__dict__[reginfo['name']] = new_register
            self.registers[reginfo['name']] = new_register

In the code above you can see that the actual register is constructed by retrieving a class reference from the class factory by name and then invoking it with the initializing dictionary. If the structure of the registers would be the following:

.. code-block:: YAML
   :linenos:

    - name: reg_1
      class: BaseRegister
      ...
    - name: reg_2
      class: BaseRegister
      ...
    - name: reg_3
      class: MySpecialRegister
      ...

``BaseRegister`` is a class in ``roboglia`` that represents a generic simple register. ``MySpecialRegister`` is a custom register defined by me and impementing some spcial handling of the data, maybe some bitwise interpretation that is specific to that device and register. The only thing that I would need is that in the main code **before** the initialization of the robot is done, I will have to register this class with the ``class factory`` like this:

.. code-block:: python
   :linenos:

    from myregister import MySpecialRegister
    from roboglia.base.factory import register_class
    from roboglia.base.robot import BaseRobot

    ...
    ...
    register_class(MySpecialRegister)

    ...
    ...
    robot = BaseRobot.from_yaml('my_robot_def.yml')
    ...
    ...

And that is all! The framework will simply integrate the custom register class without needing to subclass the device class to handle it and then the robot class to handle the new device class. It makes the extension of the code much more simple and leverages much more the code from the core ``roboglia`` without the need to subclass and invoke super class implementations.

The classes that are subject to be used for this dynamic allocation pattern are registered in the ``__ini__.py`` file of the modules in ``roboglia``, for instance the one for the ``base`` submodule looks like this:

.. code-block:: python
   :linenos:

    from .factory import register_class
    from .bus import  FileBus
    from .register import BaseRegister, FloatRegisterWithConversion, \
                        FloatRegisterWithThreshold, BoolRegister

    register_class(FileBus)
    register_class(BaseRegister)
    register_class(FloatRegisterWithConversion)
    register_class(FloatRegisterWithThreshold)
    register_class(BoolRegister)

When ``roboglia.base`` is imported, the classes will be registered automatically with the class factory and can be reused. This is a technique that can be used for custom classes too by placing the code in a module and setting up a ``__init__.py`` file where, similar to the approach above the desired classes are registered. 

Now it becomes quite clear why you would very rarely need to subclass ``BaseRobot`` and you can relly on the processing this class provides even if you include custom defined objects.

Let us now review each of the type of objects supported by the robot and understand the functionality they provide.

Buses
-----

Buses are the physical communication channels with the actual devices connected to the robot.

The robot identifies them in the initialization file 


Devices
-------

What are devices.

Registers
^^^^^^^^^

What are registers and what they do.

Groups
------

How to create groups and nest them. 

Syncs
-----

What are syncs and how you're supposed to use them.


Schedules
---------

How to use schedules and the relation to syncs.