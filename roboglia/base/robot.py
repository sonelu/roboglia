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

from ..utils import get_registered_class, check_key

logger = logging.getLogger(__name__)


class BaseRobot():
    """A complete representation of a robot.

    A robot has at minimum a ``Bus`` and a ``Device``.
    """
    def __init__(self, init_dict):
        logger.info('***** Initializing robot *************')
        self.__init_buses(init_dict)
        self.__init_devices(init_dict)
        self.__init_joints(init_dict)
        self.__init_groups(init_dict)
        self.__init_syncs(init_dict)
        logger.info('***** Initialization complete ********')

    @classmethod
    def from_yaml(cls, file_name):
        logger.info(f'Instantiating robot from YAML file {file_name}')
        with open(file_name, 'r') as f:
            info_dict = yaml.load(f, Loader=yaml.FullLoader)
            return BaseRobot(info_dict)

    def __init_buses(self, init_dict):
        """Called by ``__init__`` to parse and instantiate buses."""
        self.__buses = {}
        logger.info(f'Initializing buses...')
        check_key('buses', init_dict, 'robot', '', logger)
        for index, bus_info in enumerate(init_dict['buses']):
            check_key('name', bus_info, 'bus', index, logger)
            # add the robot as the parent of the bus
            bus_info['robot'] = self
            check_key('class', bus_info, 'bus', bus_info['name'], logger)
            bus_class = get_registered_class(bus_info['class'])
            new_bus = bus_class(bus_info)
            self.__buses[bus_info['name']] = new_bus
            logger.debug(f'\tbus {bus_info["name"]} added')

    def __init_devices(self, init_dict):
        """Called by ``__init__`` to parse and instantiate devices."""
        self.__devices = {}
        logger.info(f'Initializing devices...')
        check_key('devices', init_dict, 'robot', '', logger)
        for index, dev_info in enumerate(init_dict['devices']):
            check_key('name', dev_info, 'device', index, logger)
            check_key('bus', dev_info, 'device', dev_info['name'], logger)
            check_key(dev_info['bus'], self.buses,
                      'device', dev_info['name'],
                      logger, f'bus {dev_info["bus"]} does not exist')
            check_key('class', dev_info, 'device', dev_info['name'], logger)
            # convert the parent to object reference
            dev_bus = self.buses[dev_info['bus']]
            dev_info['bus'] = dev_bus
            dev_class = get_registered_class(dev_info['class'])
            new_dev = dev_class(dev_info)
            self.__devices[dev_info['name']] = new_dev
            logger.debug(f'\tdevice {dev_info["name"]} added')

    def __init_joints(self, init_dict):
        """Called by ``__init__`` to parse and instantiate joints."""
        self.__joints = {}
        logger.info(f'Initializing joints...')
        for index, joint_info in enumerate(init_dict.get('joints', [])):
            check_key('name', joint_info, 'joint', index, logger)
            check_key('device', joint_info, 'joint',
                      joint_info['name'], logger)
            check_key(joint_info['device'], self.devices, 'joint',
                      joint_info['name'], logger,
                      f'device {joint_info["device"]} does not exist')
            check_key('class', joint_info, 'joint', joint_info['name'], logger)
            # convert device reference from name to object
            dev_name = joint_info['device']
            device = self.devices[dev_name]
            joint_info['device'] = device
            joint_class = get_registered_class(joint_info['class'])
            new_joint = joint_class(joint_info)
            self.__joints[joint_info['name']] = new_joint
            logger.debug(f'\tjoint {joint_info["name"]} added')

    def __init_groups(self, init_dict):
        """Called by ``__init__`` to parse and instantiate groups."""
        self.__groups = {}
        logger.info(f'Initializing groups...')
        for index, grp_info in enumerate(init_dict.get('groups', [])):
            check_key('name', grp_info, 'group', index, logger)
            new_grp = set()
            # groups of devices
            for dev_name in grp_info.get('devices', []):
                check_key(dev_name, self.devices, 'group', grp_info['name'],
                          logger, f'device {dev_name} does not exist')
                new_grp.add(self.devices[dev_name])
            # groups of joints
            for joint_name in grp_info.get('joints', []):
                check_key(joint_name, self.joints, 'group', grp_info['name'],
                          logger, f'joint {joint_name} does not exist')
                new_grp.add(self.joints[joint_name])
            # groups of groups
            for grp_name in grp_info.get('groups', []):
                check_key(grp_name, self.groups, 'group', grp_info['name'],
                          logger, f'group {grp_name} does not exist')
                new_grp.update(self.groups[grp_name])
            self.__groups[grp_info['name']] = new_grp
            logger.debug(f'\tgroup {grp_info["name"]} added')

    def __init_syncs(self, init_dict):
        """Called by ``__init__`` to parse and instantiate syncs."""
        self.__syncs = {}
        logger.info(f'Initializing syncs...')
        for index, sync_info in enumerate(init_dict.get('syncs', [])):
            check_key('name', sync_info, 'sync', index, logger)
            check_key('group', sync_info, 'sync', sync_info['name'], logger)
            check_key(sync_info['group'], self.groups, 'sync',
                      sync_info['name'], logger,
                      f'group {sync_info["group"]} does not exist')
            check_key('class', sync_info, 'sync', sync_info['name'], logger)
            # convert group references
            group_name = sync_info['group']
            sync_info['group'] = self.groups[group_name]
            sync_class = get_registered_class(sync_info['class'])
            new_sync = sync_class(sync_info)
            self.__syncs[sync_info['name']] = new_sync
            logger.debug(f'\tsync {sync_info["name"]} added')

    @property
    def buses(self):
        """(read-only) the buses of the robot as a dict."""
        return self.__buses

    @property
    def devices(self):
        """(read-only) the devices of the robot as a dict."""
        return self.__devices

    @property
    def joints(self):
        """(read-only) the joints of the robot as a dict."""
        return self.__joints

    @property
    def groups(self):
        """(read-only) the groups of the robot as a dict."""
        return self.__groups

    @property
    def syncs(self):
        """(read-ony) the syncs of the robot as a dict."""
        return self.__syncs

    def start(self):
        """Starts the robot operation. It will:

        * call the ``open()`` method on all buses
        * call the ``open()`` method on all devices
        * call the ``start()`` method on all syncs

        """
        logger.info('***** Starting robot *****************')
        logger.info(f'Opening buses...')
        for bus in self.buses.values():
            if bus.auto_open:
                logger.debug(f'--> Opening bus: {bus.name}')
                bus.open()
            else:
                logger.debug(f'--> Opening bus: {bus.name} - skipped')
        logger.info(f'Opening devices...')
        for device in self.devices.values():
            if device.auto_open:
                logger.debug(f'--> Opening device: {device.name}')
                device.open()
            else:
                logger.debug(f'--> Opening device: {device.name} - skipped')
        logger.info(f'Activating joints...')
        for joint in self.joints.values():
            if joint.auto_activate:
                logger.debug(f'--> Activating joint: {joint.name}')
                joint.active = True
            else:
                logger.debug(f'--> Activating joint: {joint.name} - skipped')
        logger.info(f'Starting syncs...')
        for sync in self.syncs.values():
            if sync.auto_start:
                logger.debug(f'--> Starting sync: {sync.name}')
                sync.start()
            else:
                logger.debug(f'--> Starting sync: {sync.name} - skipped')
        logger.info('***** Robot started ******************')

    def stop(self):
        """Stops the robot operation. It will:

        * call the ``stop()`` method on all syncs
        * call the ``close()`` method on all devices
        * call the ``close()`` method on all buses

        """
        logger.info('***** Stopping robot *****************')
        logger.info(f'Stopping syncs...')
        for sync in self.syncs.values():
            logger.debug(f'--> Stopping sync: {sync.name}')
            sync.stop()
        for joint in self.joints.values():
            logger.debug(f'--> Deactivating joint: {joint.name}')
        logger.info(f'Closing devices...')
        for device in self.devices.values():
            logger.debug(f'--> Closing device: {device.name}')
            device.close()
        logger.info(f'Closing buses...')
        for bus in self.buses.values():
            logger.debug(f'--> Closing bus: {bus.name}')
            bus.close()
        logger.info('***** Robot stopped ******************')
