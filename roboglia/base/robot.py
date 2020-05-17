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

from ..utils import get_registered_class, check_key, check_type

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
                 joints={}, sensors={}, groups={}, syncs={}):
        logger.info('***** Initializing robot *************')
        self.__name = name
        if not buses:
            message = 'you need at least one bus for the robot'
            logger.critical(message)
            raise ValueError(message)
        self.__init_buses(buses)
        check_type(inits, dict, 'robot', name, logger)
        self.__inits = inits
        if not devices:
            message = 'you need at least one device for the robot'
            logger.critical(message)
            raise ValueError(message)
        self.__init_devices(devices)
        self.__init_joints(joints)
        self.__init_sensors(sensors)
        self.__init_groups(groups)
        self.__init_syncs(syncs)
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
        logger.info(f'Instantiating robot from YAML file {file_name}')
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
        logger.info('Initializing buses...')
        for bus_name, bus_info in buses.items():
            # add the name in the dict
            bus_info['name'] = bus_name
            # add the robot as the parent of the bus
            bus_info['robot'] = self
            check_key('class', bus_info, 'bus', bus_name, logger)
            bus_class = get_registered_class(bus_info['class'])
            new_bus = bus_class(**bus_info)
            self.__buses[bus_name] = new_bus
            logger.debug(f'bus {bus_name} added')

    def __init_devices(self, devices):
        """Called by ``__init__`` to parse and instantiate devices."""
        self.__devices = {}
        self.__dev_by_id = {}
        logger.info('Initializing devices...')
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
            logger.debug(f'device {dev_name} added')

    def __init_joints(self, joints):
        """Called by ``__init__`` to parse and instantiate joints."""
        self.__joints = {}
        logger.info('Initializing joints...')
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
            logger.debug(f'joint {joint_name} added')

    def __init_sensors(self, sensors):
        """Called by ``__init__`` to parse and instantiate sensors."""
        self.__sensors = {}
        logger.info('Initializing sensors...')
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
            logger.debug(f'sensor {sensor_name} added')

    def __init_groups(self, groups):
        """Called by ``__init__`` to parse and instantiate groups."""
        self.__groups = {}
        logger.info('Initializing groups...')
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
            logger.debug(f'group {grp_name} added')

    def __init_syncs(self, syncs):
        """Called by ``__init__`` to parse and instantiate syncs."""
        self.__syncs = {}
        logger.info('Initializing syncs...')
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
            new_sync = sync_class(**sync_info)
            self.__syncs[sync_name] = new_sync
            logger.debug(f'sync {sync_name} added')

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
        logger.info('Opening buses...')
        for bus in self.buses.values():
            if bus.auto_open:
                logger.info(f'--> Opening bus: {bus.name}')
                bus.open()
            else:
                logger.info(f'--> Opening bus: {bus.name} - skipped')
        logger.info('Opening devices...')
        for device in self.devices.values():
            logger.info(f'--> Opening device: {device.name}')
            device.open()
        logger.info('Activating joints...')
        for joint in self.joints.values():
            if joint.auto_activate:
                logger.info(f'--> Activating joint: {joint.name}')
                joint.active = True
            else:
                logger.info(f'--> Activating joint: {joint.name} - skipped')
        logger.info('Starting syncs...')
        for sync in self.syncs.values():
            if sync.auto_start:
                logger.info(f'--> Starting sync: {sync.name}')
                sync.start()
            else:
                logger.info(f'--> Starting sync: {sync.name} - skipped')
        logger.info('***** Robot started ******************')

    def stop(self):
        """Stops the robot operation. It will:

        * call the :py:meth:`~BaseSync.stop` method on all syncs
        * call the :py:meth:`~BaseDevice.close` method on all devices
        * call the :py:meth:`~BaseBus.close` method on all buses

        """
        logger.info('***** Stopping robot *****************')
        logger.info('Stopping syncs...')
        for sync in self.syncs.values():
            logger.debug(f'--> Stopping sync: {sync.name}')
            sync.stop()
        for joint in self.joints.values():
            logger.debug(f'--> Deactivating joint: {joint.name}')
        logger.info('Closing devices...')
        for device in self.devices.values():
            logger.debug(f'--> Closing device: {device.name}')
            device.close()
        logger.info('Closing buses...')
        for bus in self.buses.values():
            logger.debug(f'--> Closing bus: {bus.name}')
            bus.close()
        logger.info('***** Robot stopped ******************')
