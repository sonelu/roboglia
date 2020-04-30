import yaml
import logging
from .factory import get_registered_class

logger = logging.getLogger(__name__)

class BaseRobot():
    """A complete representation of a robot.

    A robot has at minimum a ``Bus`` and a ``Device``.
    """ 
    def __init__(self, init_dict):
        self.__init_buses(init_dict)
        self.__init_devices(init_dict)
        self.__init_joints(init_dict)
        self.__init_groups(init_dict)
        self.__init_syncs(init_dict)

    @classmethod
    def from_yaml(cls, file_name):
        logger.info(f'Instantiating robot from YAML file {file_name}')
        with open(file_name, 'r') as f:
            info_dict = yaml.load(f, Loader=yaml.FullLoader)
            return BaseRobot(info_dict)

    def __check_name(self, object, index, init_dict):
        """Helper function, checks if 'name' provided."""
        if 'name' not in init_dict:
            mess = f"{object} index {index} does not have a name."
            logger.critical(mess)
            raise KeyError(mess)

    def __check_attrib(self, object, attrib, init_dict, mess=None):
        """Helper function, checks if 'class' provided."""
        if attrib not in init_dict:
            if mess == None:
                mess = f"{object} {init_dict['name']} does not have a {attrib} assigned."
            logger.critical(mess)
            raise KeyError(mess)

    def __init_buses(self, init_dict):
        """Called by ``__init__`` to parse and instantiate buses."""
        self.buses = {}
        logger.info(f'Initializing buses...')
        self.__check_attrib('robot', 'buses', init_dict,
                            'A robot must have at least one bus defined in the "buses" section')
        for index, bus_info in enumerate(init_dict['buses']):
            self.__check_name('Bus', index, bus_info)
            # add the robot as the parent of the bus
            bus_info['parent'] = self
            self.__check_attrib('Bus', 'class', bus_info)
            bus_class = get_registered_class(bus_info['class'])
            new_bus = bus_class(bus_info)
            self.buses[bus_info['name']] = new_bus
            logger.debug(f'\tbus {bus_info["name"]} added')

    def __init_devices(self, init_dict):
        """Called by ``__init__`` to parse and instantiate devices."""
        self.devices = {}
        logger.info(f'Initializing devices...')
        self.__check_attrib('robot', 'devices', init_dict,
                            'A robot must have at least one device defined in the "devices" section')
        for index, dev_info in enumerate(init_dict['devices']):
            self.__check_name('Device', index, dev_info)
            # convert the parent to object reference
            self.__check_attrib('Device', 'bus', dev_info)
            if dev_info['bus'] not in self.buses:
                mess = f'Bus {dev_info["bus"]} used by device {dev_info["name"]} does not exist.'
                logger.critical(mess)
                raise KeyError(mess)
            dev_bus = self.buses[dev_info['bus']]
            dev_info['bus'] = dev_bus
            self.__check_attrib('Device', 'class', dev_info)
            dev_class = get_registered_class(dev_info['class'])
            new_dev = dev_class(dev_info)
            self.devices[dev_info['name']] = new_dev
            logger.debug(f'\tdevice {dev_info["name"]} added')

    def __init_joints(self, init_dict):
        """Called by ``__init__`` to parse and instantiate joints."""
        self.joints = {}
        logger.info(f'Initializing joints...')
        for index, joint_info in enumerate(init_dict.get('joints', [])):
            self.__check_name('Joint', index, joint_info)
            # convert device reference from name to object
            dev_name = joint_info['device']
            if joint_info['device'] not in self.devices:
                mess = f'Device {joint_info["device"]} used by joint {joint_info["name"]} does not exist.'
                logger.critical(mess)
                raise KeyError(mess)
            device = self.devices[dev_name]
            joint_info['device'] = device
            self.__check_attrib('Joint', 'class', joint_info)
            joint_class = get_registered_class(joint_info['class'])
            new_joint = joint_class(joint_info)
            self.joints[joint_info['name']] = new_joint
            logger.debug(f'\tjoint {joint_info["name"]} added')

    def __init_groups(self, init_dict):
        """Called by ``__init__`` to parse and instantiate groups."""        
        self.groups = {}
        logger.info(f'Initializing groups...')
        for index, grp_info in enumerate(init_dict.get('groups', [])):
            self.__check_name('Group', index, grp_info)
            new_grp = set()
            # groups of devices
            for dev_name in grp_info.get('devices',[]):
                if dev_name not in self.devices:
                    mess = f"Device {dev_name} used in group {grp_info['name']} does not exist."
                    logger.critical(mess)
                    raise KeyError(mess)
                new_grp.add(self.devices[dev_name])
            # groups of joints
            for joint_name in grp_info.get('joints', []):
                if joint_name not in self.joints:
                    mess = f"Joint {joint_name} used in group {grp_info['name']} does not exist."
                    logger.critical(mess)
                    raise KeyError(mess)
                new_grp.add(self.joints[joint_name])
            # groups of groups
            for grp_name in grp_info.get('groups', []):
                if grp_name not in self.groups:
                    mess = f"Group {grp_name} used in group {grp_info['name']} does not exist."
                    logger.critical(mess)
                    raise KeyError(mess)
                new_grp.update(self.groups[grp_name])
            self.groups[grp_info['name']] = new_grp
            logger.debug(f'\tgroup {grp_info["name"]} added')

    def __init_syncs(self, init_dict):
        """Called by ``__init__`` to parse and instantiate syncs."""                
        self.syncs = {}
        logger.info(f'Initializing syncs...')        
        for index, sync_info in enumerate(init_dict.get('syncs', [])):
            self.__check_name('Sync', index, sync_info)
            # convert group references
            self.__check_attrib('Sync', 'group', sync_info)
            group_name = sync_info['group']
            if group_name not in self.groups:
                mess = f"Group {group_name} used in sync {sync_info['name']} does not exist."
                logger.critical(mess)
                raise KeyError(mess)
            sync_info['group'] = self.groups[group_name]
            self.__check_attrib('Sync', 'class', sync_info)
            sync_class = get_registered_class(sync_info['class'])
            new_sync = sync_class(sync_info)
            self.syncs[sync_info['name']] = new_sync
            logger.debug(f'\tsync {sync_info["name"]} added')

    def start(self):
        """Starts the robot operation.

        It will:
        * call the ``open()`` method on all buses
        * call the ``open()`` method on all devices
        * call the ``start()`` method on all syncs
        """
        logger.info(f'Opening buses...')
        for bus in self.buses.values():
            logger.debug(f'\tOpening bus {bus.name}')
            bus.open()
        logger.info(f'Opening devices...')
        for device in self.devices.values():
            logger.debug(f'\tOpening device {device.name}')
            device.open()
        logger.info(f'Starting syncs...')
        for sync in self.syncs.values():
            logger.debug(f'\tStarting sync {sync.name}')
            sync.start()

    def stop(self):
        """Stops the robot operation.

        It will:
        * call the ``stop()`` method on all syncs
        * call the ``close()`` method on all devices
        * call the ``close()`` method on all buses
        """
        logger.info(f'Stopping syncs...')
        for sync in self.syncs.values():
            logger.debug(f'\tStopping sync {sync.name}')
            sync.stop()
        logger.info(f'Closing devices...')
        for device in self.devices.values():
            logger.debug(f'\tClosing device {device.name}')
            device.close()
        logger.info(f'Closing buses...')
        for bus in self.buses.values():
            logger.debug(f'\tClosing bus {bus.name}')
            bus.close()
