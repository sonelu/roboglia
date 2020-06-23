# Copyright (C) 2020  Alex Sonea

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import yaml
import logging
import threading
import statistics
import time

from ..utils import get_registered_class, check_key, check_type, check_options
from .thread import BaseLoop
from .joint import Joint, PVL, PVLList

logger = logging.getLogger(__name__)


class BaseRobot():
    """A complete representation of a robot.

    A robot has at minimum one ``Bus`` and one ``Device``. You can create
    a robot programatically by calling the constructor and providing all
    the parameters required or use an initialization dictionary or a YAML
    file. The last option is the preferred one considering the volume of
    information usually needed to describe a robot.

    For initializing a robot from a dictionary definition use
    :py:meth:`~BaseRobot.from_dict` class method. For instantiating from a
    YAML file use :py:meth:`~BaseRobot.from_yaml` class method.

    Parameters
    ----------
    name: str
        the name of the robot; will default to **ROBOT**

    buses: dict
        a dictionary with buses definitions; the components
        of the buses are defined by the attributes of the particular
        class of the bus

    inits: dict
        a dictionary of register initialization; should have the following
        form::

            inits:
                init_template_1:
                    register_1: value
                    register_2: None     # this indicates 'read initialization'
                init_template_2:
                    register_3: value
                    register_4: value

        see also the :py:class:`BaseDevice` where the details of the
        initialization process are described

    devices: dict
        a dictionary with the device definitions; the
        components of devices are defined by the attributes of the
        particular class of device

    joints: dict
        a dictionary with the joint definitions; the
        components of the joints are defined by the attributes of the
        particular class of joint

    sensors: dict
        a dictionary with the sensors defintion; the components of the
        sensor are defined by the attributes of the particular class of
        sensor

    groups: dict
        a dictionary with the group definitions; the groups
        end up unwind in the robot as sets (eliminates duplication) and
        they are defined by the following components (keys in the
        dictionary defintion): ``devices``  a list of device names
        in no particular order, ``joints`` a list of joint names in
        no particular order, ``sensors`` a list of sensors in no
        particular order and ``groups`` a list of sub-groups that were
        previously defined and will be included in the current group.
        Technically it is possible to mix and match the components of
        a group (for instance create groups that contain devices, sensors,
        and joints).

    syncs: dict
        a dictionary with sync loops definitions; the components
        of syncs are defined by the attributes of the particular class of
        sync.
    """
    def __init__(self, name='ROBOT', buses={}, inits={}, devices={},
                 joints={}, sensors={}, groups={}, syncs={}, manager={}):
        logger.info('***** Initializing robot *************')
        self.__name = name
        # if not buses:
        #     message = 'you need at least one bus for the robot'
        #     logger.critical(message)
        #     raise ValueError(message)
        self.__init_buses(buses)
        check_type(inits, dict, 'robot', name, logger)
        self.__inits = inits
        # if not devices:
        #     message = 'you need at least one device for the robot'
        #     logger.critical(message)
        #     raise ValueError(message)
        self.__init_devices(devices)
        self.__init_joints(joints)
        self.__init_sensors(sensors)
        self.__init_groups(groups)
        self.__init_syncs(syncs)
        self.__init_manager(manager)
        logger.info('***** Initialization complete ********')

    @classmethod
    def from_yaml(cls, file_name):
        """Initializes the robot from a YAML file. It will attempt to
        read the file and parse it with ``yaml`` library (PyYaml) and
        then passes it to the :py:meth:`~BaseRobot.from_dict` class method
        to do further initialization.

        Parameters
        ----------
        file_name: str
            The name of the YAML file with the robot definition

        Raises
        ------
        FileNotFoundError
            in case the file is not available

        """
        logger.info(f'Creating robot from YAML file {file_name}')
        with open(file_name, 'r') as f:
            init_dict = yaml.load(f, Loader=yaml.FullLoader)
            if len(init_dict) > 1:
                logger.warning('Only the first robot will be considered.')
            name = list(init_dict)[0]
            components = init_dict[name]
            return BaseRobot(name=name, **components)

    def __init_buses(self, buses):
        """Called by ``__init__`` to parse and instantiate buses."""
        self.__buses = {}
        if buses is None:
            return
        logger.info('Settting up buses...')
        for bus_name, bus_info in buses.items():
            # add the name in the dict
            bus_info['name'] = bus_name
            # add the robot as the parent of the bus
            bus_info['robot'] = self
            check_key('class', bus_info, 'bus', bus_name, logger)
            bus_class = get_registered_class(bus_info['class'])
            del bus_info['class']
            new_bus = bus_class(**bus_info)
            self.__buses[bus_name] = new_bus
            logger.info(f'Bus "{bus_name}" added')

    def add_bus(self, bus_obj):
        """Adds an already instantiated Bus object to the robot. Raises
        an error in the log if a bus with the same name is already
        registered and does not register it.

        Parameters
        ----------
        bus_obj: BaseBus or subclass
            The bus to be added
        """
        if bus_obj.name not in self.__buses:
            self.__buses[bus_obj.name] = bus_obj
        else:
            logger.error(f'Bus {bus_obj.name} already registered '
                         'with the robot')

    def __init_devices(self, devices):
        """Called by ``__init__`` to parse and instantiate devices."""
        self.__devices = {}
        self.__dev_by_id = {}
        if devices is None:
            return
        logger.info('Setting up devices...')
        for dev_name, dev_info in devices.items():
            # add the name in the dev_info
            dev_info['name'] = dev_name
            check_key('bus', dev_info, 'device', dev_name, logger)
            check_key(dev_info['bus'], self.buses,
                      'device', dev_name,
                      logger, f'bus {dev_info["bus"]} does not exist')
            check_key('class', dev_info, 'device', dev_name, logger)
            # convert bus names to bus objects
            bus_name = dev_info['bus']
            dev_bus = self.buses[bus_name]
            dev_info['bus'] = dev_bus
            # convert init names to objects
            list_of_inits = dev_info.get('inits', [])
            check_type(list_of_inits, list, 'device', dev_name, logger)
            for index, init_name in enumerate(list_of_inits):
                check_key(init_name, self.inits, 'device', dev_name, logger)
                list_of_inits[index] = self.inits[init_name]
            dev_class = get_registered_class(dev_info['class'])
            new_dev = dev_class(**dev_info)
            self.__devices[dev_name] = new_dev
            self.__dev_by_id[dev_info['dev_id']] = new_dev
            logger.info(f'Device "{dev_name}" added')

    def add_device(self, dev_obj):
        """Adds an already instantiated Device object to the robot. Raises
        an error in the log if a device with the same name is already
        registered and does not register it.

        Parameters
        ----------
        dev_obj: BaseDevice or subclass
            The device to be added
        """
        if dev_obj.name not in self.__devices:
            self.__devices[dev_obj.name] = dev_obj
            self.__dev_by_id[dev_obj.dev_id] = dev_obj
        else:
            logger.error(f'Device {dev_obj.name} already registered '
                         'with the robot')

    def __init_joints(self, joints):
        """Called by ``__init__`` to parse and instantiate joints."""
        self.__joints = {}
        logger.info('Setting up joints...')
        for joint_name, joint_info in joints.items():
            # add the name in the joint_info
            joint_info['name'] = joint_name
            check_key('device', joint_info, 'joint',
                      joint_name, logger)
            check_key(joint_info['device'], self.devices, 'joint',
                      joint_name, logger,
                      f'device {joint_info["device"]} does not exist')
            check_key('class', joint_info, 'joint', joint_name, logger)
            # convert device reference from name to object
            dev_name = joint_info['device']
            device = self.devices[dev_name]
            joint_info['device'] = device
            joint_class = get_registered_class(joint_info['class'])
            new_joint = joint_class(**joint_info)
            self.__joints[joint_name] = new_joint
            logger.info(f'Joint "{joint_name}" added')

    def __init_sensors(self, sensors):
        """Called by ``__init__`` to parse and instantiate sensors."""
        self.__sensors = {}
        logger.info('Setting up sensors...')
        for sensor_name, sensor_info in sensors.items():
            # add the name in the joint_info
            sensor_info['name'] = sensor_name
            check_key('device', sensor_info, 'sensor',
                      sensor_name, logger)
            check_key(sensor_info['device'], self.devices, 'senor',
                      sensor_name, logger,
                      f'device {sensor_info["device"]} does not exist')
            check_key('class', sensor_info, 'sensor', sensor_name, logger)
            # convert device reference from name to object
            dev_name = sensor_info['device']
            device = self.devices[dev_name]
            sensor_info['device'] = device
            sensor_class = get_registered_class(sensor_info['class'])
            new_sensor = sensor_class(**sensor_info)
            self.__sensors[sensor_name] = new_sensor
            logger.info(f'Sensor "{sensor_name}" added')

    def __init_groups(self, groups):
        """Called by ``__init__`` to parse and instantiate groups."""
        self.__groups = {}
        logger.info('Setting up groups...')
        for grp_name, grp_info in groups.items():
            new_grp = set()
            # groups of devices
            for dev_name in grp_info.get('devices', []):
                check_key(dev_name, self.devices, 'group', grp_name,
                          logger, f'device {dev_name} does not exist')
                new_grp.add(self.devices[dev_name])
            # groups of joints
            for joint_name in grp_info.get('joints', []):
                check_key(joint_name, self.joints, 'group', grp_name,
                          logger, f'joint {joint_name} does not exist')
                new_grp.add(self.joints[joint_name])
            # groups of groups
            for sub_grp_name in grp_info.get('groups', []):
                check_key(sub_grp_name, self.groups, 'group', grp_name,
                          logger, f'group {sub_grp_name} does not exist')
                new_grp.update(self.groups[sub_grp_name])
            self.__groups[grp_name] = new_grp
            logger.info(f'Group "{grp_name}" added')

    def __init_syncs(self, syncs):
        """Called by ``__init__`` to parse and instantiate syncs."""
        self.__syncs = {}
        logger.info('Setting up syncs...')
        for sync_name, sync_info in syncs.items():
            sync_info['name'] = sync_name
            check_key('group', sync_info, 'sync', sync_name, logger)
            check_key(sync_info['group'], self.groups, 'sync',
                      sync_name, logger,
                      f'group {sync_info["group"]} does not exist')
            check_key('class', sync_info, 'sync', sync_name, logger)
            # convert group references
            group_name = sync_info['group']
            sync_info['group'] = self.groups[group_name]
            sync_class = get_registered_class(sync_info['class'])
            del sync_info['class']
            new_sync = sync_class(**sync_info)
            self.__syncs[sync_name] = new_sync
            logger.info(f'Sync "{sync_name}" added')

    def __init_manager(self, manager):
        """Called by ``__init__`` to parse and instantiate the robot
        manager."""
        # process joints and replace names with objects
        logger.info('Setting up manager...')
        joints = manager.get('joints', [])
        for index, joint_name in enumerate(joints):
            check_key(joint_name, self.joints, 'manager', self.name, logger)
            joints[index] = self.joints[joint_name]
        group_name = manager.get('group', '')
        if group_name:
            check_key(group_name, self.groups, 'manager', self.name, logger)
            group = self.groups[group_name]
            for joint in group:
                check_type(joint, Joint, 'manager', self.name, logger)
        else:
            group = set()
        if 'joints' in manager:
            del manager['joints']
        if 'group' in manager:
            del manager['group']
        name = manager.get('name', self.name+'-manager')
        self.__manager = JointManager(name=name, joints=joints,
                                      group=group, **manager)
        logger.info(f'Manager "{self.manager.name}" added')

    @property
    def name(self):
        """(read-only) The name of the robot."""
        return self.__name

    @property
    def buses(self):
        """(read-only) The buses of the robot as a dict."""
        return self.__buses

    @property
    def inits(self):
        """The initialization templates defined for the robot."""
        return self.__inits

    @property
    def devices(self):
        """(read-only) The devices of the robot as a dict."""
        return self.__devices

    def device_by_id(self, dev_id):
        """Returns a device by it's ID.

        Parameters
        ----------
        dev_id: int
            the ID or device to be returned

        Returns
        -------
        BaseRegister
            the register with that ID in the device. If no register
            with that ID exists, returns ``None``.
        """
        return self.__dev_by_id.get(dev_id, None)

    @property
    def joints(self):
        """(read-only) The joints of the robot as a dict."""
        return self.__joints

    @property
    def sensors(self):
        """The sensors of the robot as a dict."""
        return self.__sensors

    @property
    def groups(self):
        """(read-only) The groups of the robot as a dict."""
        return self.__groups

    @property
    def syncs(self):
        """(read-only) The syncs of the robot as a dict."""
        return self.__syncs

    @property
    def manager(self):
        """The RobotManager of the robot."""
        return self.__manager

    def start(self):
        """Starts the robot operation. It will:

        * call the :py:meth:`~BaseBus.open` method on all buses except the ones
          that have ``auto`` set to ``False``
        * call the :py:meth:`~BaseDevice.open` method on all devices except
          the ones that have ``auto`` set to ``False``
        * call the :py:meth:`~BaseSync.start` method on all syncs except the
          ones that have ``auto`` set to ``False``

        """
        logger.info('***** Starting robot *****************')
        # buses
        logger.info('Opening buses...')
        for bus in self.buses.values():
            if bus.auto_open:
                logger.info(f'Opening bus: "{bus.name}"')
                bus.open()
            else:
                logger.info(f'Opening bus: "{bus.name}" - skipped')
        # devices
        logger.info('Opening devices...')
        for device in self.devices.values():
            logger.info(f'Opening device: "{device.name}"')
            # TODO: should there be an Auto attribute for devices?
            device.open()
        # joint manager; this will also start the joints
        logger.info('Starting joint manager...')
        self.manager.start()
        # syncs
        # we start syncs latest to make sure that the joint manager
        # has properly initialized the joints before starting to replicate
        # the internal devices
        logger.info('Starting syncs...')
        for sync in self.syncs.values():
            if sync.auto_start:
                logger.info(f'Starting sync: "{sync.name}"')
                sync.start()
            else:
                logger.info(f'Starting sync: "{sync.name}" - skipped')
        # finished
        logger.info('***** Robot started ******************')

    def stop(self):
        """Stops the robot operation. It will:

        * call the :py:meth:`~BaseSync.stop` method on all syncs
        * call the :py:meth:`~BaseDevice.close` method on all devices
        * call the :py:meth:`~BaseBus.close` method on all buses

        """
        logger.info('***** Stopping robot *****************')
        logger.info('Stopping joint manager...')
        self.manager.stop()
        logger.info('Stopping syncs...')
        for sync in self.syncs.values():
            logger.info(f'Stopping sync: "{sync.name}"')
            sync.stop()
        logger.info('Closing devices...')
        for device in self.devices.values():
            logger.info(f'Closing device: "{device.name}"')
            device.close()
        logger.info('Closing buses...')
        for bus in self.buses.values():
            logger.info(f'Closing bus: "{bus.name}"')
            bus.close()
        logger.info('***** Robot stopped ******************')


class JointManager(BaseLoop):
    """Implements the management of the joints by alowing multiple movement
    streams to submit position commands to the robot.

    The ``JointManager`` inherits the constructor paramters from
    :py:class:`BaseLoop`. Please refer to that class for mote details.

    In addition the class introduces the following additional paramters:

    Parameters
    ----------
    joints: list of :py:class:roboglia.Base.`Joint` or subclass
        The list of joints that the manager is having under control.
        Alternatively you can use the parameter ``group`` (see below)

    group: set of :py:class:roboglia.Base.`Joint` or subclass
        A group of joints that was defined earlier with a ``group``
        statement in the robot definition file.

    function: str
        The function used to produce the blended command for the joints. If
        specific functions for position (``p_function``), velocity (
        ``v_function``) or load (``ld_function``) are not supplied, then
        this function is used.
        Allowed values are 'mean', 'median', 'min', 'max'.

    p_function: str
        A specific function to be used for aggregating the position values.
        Allowed values are 'mean', 'median', 'min', 'max'.

    v_function: str
        A specific function to be used for aggregating the velocity values.
        Allowed values are 'mean', 'median', 'min', 'max'.

    ld_function: str
        A specific function to be used for aggregating the load values.
        Allowed values are 'mean', 'median', 'min', 'max'.

    timeout: float
        Is a time in seconds an accessor will wait before issuing a timeout
        when trying to submit data to the manager or the manager preparing
        the data for the joints.
    """
    def __init__(self, name='JointManager', frequency=100.0, joints=[],
                 group=None, function='mean', p_function=None,
                 v_function=None, ld_function=None, timeout=0.5, **kwargs):
        super().__init__(name=name, frequency=frequency, **kwargs)
        temp_joints = []
        if joints:
            temp_joints.extend(joints)
        if group:
            temp_joints.extend(group)
        # eliminate duplicates
        self.__joints = list(set(temp_joints))
        if len(self.__joints) == 0:
            logger.warning('Joint manager does not have any joints '
                           'attached to it')
        check_options(function, ['mean', 'median', 'min', 'max'],
                      'JointManager', name, logger)
        # aggregate functions
        func = self.__check_function(function, 'default')
        self.__p_func = self.__check_function(p_function, 'p_function', func)
        self.__v_func = self.__check_function(v_function, 'v_function', func)
        self.__ld_func = self.__check_function(ld_function, 'ld_function',
                                               func)
        # processing queues
        self.__submissions = {}
        self.__adjustments = {}
        self.__streams = {}
        self.__lock = threading.Lock()

    def __check_function(self, func_name, context, default=statistics.mean):
        """Checks the function provided and returns a reference to it.
        Supported functions: ``mean``, ``median``, ``min`` and ``max``.

        Parameters
        ----------
        func_name: str
            A name of a function to be checked and retrieved. Supported
            values: ``mean``, ``median``, ``min`` and ``max``.

        default: function
            A function that will be used to default to in case the supplied
            one is not supported.

        Returns
        -------
        func:
            If the function is one of the supported ones, it returns a
            reference to it, otherwise returns ``default`` function.
        """
        supported = {
            'mean': statistics.mean,
            'median': statistics.median,
            'min': min,
            'max': max
        }
        if func_name in supported:
            return supported[func_name]

        logger.info(f'Function "{func_name}" for {context} not supported. '
                    f'Using {default}')
        return default

    @property
    def joints(self):
        return self.__joints

    @property
    def p_func(self):
        """Aggregate function for positions."""
        return self.__p_func

    @property
    def v_func(self):
        """Aggregate function for positions."""
        return self.__v_func

    @property
    def ld_func(self):
        """Aggregate function for positions."""
        return self.__ld_func

    def submit(self, stream, commands, adjustments=False):
        """Used by a stream of commands to notify the Joint Manager they
        joint commands they want.

        Parameters
        ----------
        stream: BaseThread or subclass
            The stream providing the data. It is used to keep the
            request separate and be able to merge later.

        commands: dict
            A dictionary with the commands requests in the format::

                {joint_name: (values)}

            Where ``values`` is a tuple with the command for that joint. It
            is acceptable to send partial commands to a joint, for instance
            you can send only (100,) meaning position 100 to a JointPVL.
            Submitting more information to a joint will have no effect, for
            instance (100, 20, 40) (position, velocity, load) to a Joint will
            only use the position part of the request.

        adjustments: bool
            Indicates that the values are to be treated as adjustments to
            the other requests instead of absolute requests. This is
            convenient for streams that request postion correction like
            an accelerometer based balance control. Internally the
            JointManger keeps the commands separate between the absolute
            and the adjustments ones and calculates separate averages then
            adjusts the absolute results with the ones from the adjustments
            to produce the final numbers.

        Returns
        -------
        bool:
            ``True`` if the operation was successful. False if there was an
            error (most likely the lock was not acquired). Caller needs to
            review this and decide if they should retry to send data.
        """
        if not self.__lock.acquire(timeout=self.period):
            logger.warning(f'failed to acquire manager for '
                           f'stream {stream.name}')
            return False

        # add the new stream
        if stream.name not in self.__streams:
            self.__streams[stream.name] = stream
        # record adjustments request
        if adjustments:
            self.__adjustments[stream.name] = commands
        # record submission request
        else:
            self.__submissions[stream.name] = commands
        self.__lock.release()
        return True

    def stop_submit(self, stream, adjustments=False):
        """Notifies the ``JointManager`` that the stream has finished
        sending data and as a result the data in the ``JointManager`` cache
        should be removed.

        .. warning:: If the stream does not call this method when it
            finished with a routine the last submission will remain in
            the cache and will continue to be averaged with the other
            requests, creating problems. Don't forget to call this method
            when your move finishes!

        Parameters
        ----------
        stream: BaseThread or subclass
            The name of the move sending the data

        adjustments: bool
            Indicates the move submitted to the adjustment stream.

        Returns
        -------
        bool:
            ``True`` if the operation was successful. False if there was an
            error (most likely the lock was not acquired). Caller needs to
            review this and decide if they should retry to send data. In the
            case of this method it is advisable to try resending the request,
            otherwise stale data will stay in the cache.
        """
        if not self.__lock.acquire(timeout=self.period):
            logger.warning(f'failed to acquire manager for '
                           f'stream {stream.name}')
            return False

        # delete the stream
        if stream.name in self.__streams:              # pragma: no branch
            del self.__streams[stream.name]
        # remove any adjustment requests
        if adjustments:
            if stream.name in self.__adjustments:      # pragma: no branch
                del self.__adjustments[stream.name]
        # remove any submission requests
        else:
            if stream.name in self.__submissions:      # pragma: no branch
                del self.__submissions[stream.name]
        self.__lock.release()
        return True

    def start(self):
        """Starts the JointManager. Before calling the
        :py:meth:`BaseThread.start` it activates the joints if they
        indicate they have the ``auto`` flag set.
        """
        for joint in self.joints:
            if joint.auto_activate and not joint.active:
                logger.info(f'Activating joint: "{joint.name}"')
                joint.active = True
            else:
                logger.info(f'Activating joint: "{joint.name}" - skipped')
        super().start()

    def stop(self):
        """Stops the JointManager. After calling the
        :py:meth:`BaseThread.stop` it deactivates the joints if they
        indicate they have the ``auto`` flag set.
        """
        # stop the streams
        logger.info('Stopping streams...')
        start = time.time()
        duration = 0
        while self.__streams and duration < 2.0:
            stream = list(self.__streams.values())[0]
            if stream.running:
                stream.stop()
            duration = time.time() - start

            # while stream.running:
            #     time.sleep(0.1)
        super().stop()
        for joint in self.joints:
            if joint.auto_activate and joint.active:
                logger.info(f'Deactivating joint: "{joint.name}"')
                joint.active = False
            else:
                logger.info(f'Deactivating joint: "{joint.name}" - skipped')

    def atomic(self):
        if not self.__lock.acquire(timeout=self.period):
            logger.warning('failed to acquire lock for atomic processing')
        else:
            for joint in self.joints:
                comm = self.__process_request(joint, self.__submissions)
                adj = self.__process_request(joint, self.__adjustments)
                value = comm + adj
                if not value == PVL():          # pragma: no branch
                    logger.debug(f'Setting joint {joint.name}: value={value}')
                    joint.value = value
            self.__lock.release()

    def __process_request(self, joint, requests):
        """Processes a list of requests and returns the processed command
        for that joint. The processed command applies an aggregation function
        (default ``mean``) to the command parameters.

        Parameters
        ----------
        joint: Joint or subclass
            The joint being processed

        requests: dict
            A dictionary that contains all the requests submitted by streams.
            They are normally either the :py:class:`JointManager`'s
            ``submissions`` or ``adjustments``, the two buffers with requests
            for joint positions. The dictionary has as key the submitter's
            name and the data is another dict of {joint : (pos, vel, load)}
            records.

        Returns
        -------
        PVLList:
            A list of PVL items selected from the requests. If there are no
            commands for that joint it returns a list with
        """
        req = PVLList()
        for request in requests.values():
            values = request.get(joint.name, None)
            if not values:
                continue
            else:
                req.append(pvl=values)
        if len(req) == 0:
            return PVL()        # will be with ``nan```
        if len(req) == 1:
            return req.items[0]
        return req.process(p_func=self.p_func,
                           v_func=self.v_func,
                           ld_func=self.ld_func)
