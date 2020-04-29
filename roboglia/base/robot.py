import yaml
import logging
from .factory import get_registered_class

logger = logging.getLogger(__name__)

class BaseRobot():

    def __init__(self, init_dict):
        # buses; mandatory, will raise exception if not provided
        self.buses = {}
        logger.info(f'Initializing buses...')
        if 'buses' not in init_dict:
            logger.critical(f'no "busses" section provided in the robot initialization')
            raise KeyError(f'a robot must have at least one bus defined in the "buses" section')
        for bus_info in init_dict['buses']:
            # add the robot as the parent of the bus
            bus_info['parent'] = self
            bus_class = get_registered_class(bus_info['class'])
            new_bus = bus_class(bus_info)
            self.buses[bus_info['name']] = new_bus
            logger.debug(f'\tbus {bus_info["name"]} added')

        # devices; mandatory, will raise exeption if not provided
        self.devices = {}
        logger.info(f'Initializing devices...')
        if 'devices' not in init_dict:
            logger.critical(f'no "devices" section provided in the robot initialization')
            raise KeyError(f'a robot must have at least one device defined in the "devices" section')
        for dev_info in init_dict['devices']:
            # convert the parent to object reference
            dev_bus = self.buses[dev_info['bus']]
            dev_info['bus'] = dev_bus
            dev_class = get_registered_class(dev_info['class'])
            new_dev = dev_class(dev_info)
            self.devices[dev_info['name']] = new_dev
            logger.debug(f'\tdevice {dev_info["name"]} added')

        # joints
        self.joints = {}
        logger.info(f'Initializing joints...')
        for joint_info in init_dict.get('joints', []):
            # convert object references
            dev_name = joint_info['device']
            device = self.devices[dev_name]
            joint_info['device'] = device
            joint_class = get_registered_class(dev_info['class'])
            new_joint = joint_class(joint_info)
            self.joints[joint_info['name']] = new_joint
            logger.debug(f'\tjoint {joint_info["name"]} added')

        # groups
        self.groups = {}
        logger.info(f'Initializing joints...')
        for grp_info in init_dict.get('groups', []):
            new_grp = set()
            for dev_name in grp_info.get('devices',[]):
                new_grp.add(self.devices[dev_name])
            for joint_name in grp_info.get('joints', []):
                new_grp.add(self.joints[joint_name])
            for grp_name in grp_info.get('groups', []):
                new_grp.update(self.groups[grp_name])
            self.groups[grp_info['name']] = new_grp
            logger.debug(f'\tgroup {grp_info["name"]} added')

        # sync
        self.syncs = {}
        logger.info(f'Initializing syncs...')        
        for sync_info in init_dict.get('syncs', []):
            # convert group references
            group_name = sync_info['group']
            sync_info['group'] = self.groups[group_name]
            sync_class = get_registered_class(sync_info['class'])
            new_sync = sync_class(sync_info)
            self.syncs[sync_info['name']] = new_sync
            logger.debug(f'\tsync {sync_info["name"]} added')

    @classmethod
    def from_yaml(cls, file_name):
        logger.info(f'Instantiating robot from YAML file {file_name}')
        with open(file_name, 'r') as f:
            info_dict = yaml.load(f, Loader=yaml.FullLoader)
            return BaseRobot(info_dict)

    def start(self):
        logger.info(f'Opening buses...')
        for bus in self.buses.values():
            bus.open()
            logger.debug(f'\tbus {bus.name} opened')
        logger.info(f'Opening devices...')
        for device in self.devices.values():
            device.open()
            logger.debug(f'\tdevice {device.name} opened')
        logger.info(f'Starting syncs...')
        for sync in self.syncs.values():
            sync.start()
            logger.debug(f'\tsync {sync.name} started')

    def stop(self):
        logger.info(f'Stopping syncs...')
        for sync in self.syncs.values():
            sync.stop()
            logger.debug(f'\tsync {sync.name} stopped')
        logger.info(f'Closing devices...')
        for device in self.devices.values():
            device.close()
            logger.debug(f'\tdevice {device.name} closed')
        logger.info(f'Closing buses...')
        for bus in self.buses.values():
            bus.close()
            logger.debug(f'\tbus {bus.name} closed')
