import yaml
from .factory import get_registered_class

class BaseRobot():

    def __init__(self, init_dict):
        # buses; mandatory, will raise exception if not provided
        self.buses = {}
        for bus_info in init_dict['buses']:
            # add the robot as the parent of the bus
            bus_info['parent'] = self
            bus_class = get_registered_class(bus_info['class'])
            new_bus = bus_class(bus_info)
            new_bus.open()
            self.buses[bus_info['name']] = new_bus

        # devices; mandatory, will raise exeption if not provided
        self.devices = {}
        for dev_info in init_dict['devices']:
            # convert the parent to object reference
            dev_bus = self.buses[dev_info['bus']]
            dev_info['bus'] = dev_bus
            dev_class = get_registered_class(dev_info['class'])
            new_dev = dev_class(dev_info)
            new_dev.open()
            self.devices[dev_info['name']] = new_dev

        # groups
        self.groups = {}
        for grp_info in init_dict.get('groups', []):
            new_grp = set()
            for dev_name in grp_info.get('devices',[]):
                new_grp.add(self.devices[dev_name])
            for grp_name in grp_info.get('groups', []):
                new_grp.update(self.groups[grp_name])
            self.groups[grp_info['name']] = new_grp


    @classmethod
    def from_yaml(cls, file_name):
        with open(file_name, 'r') as f:
            info_dict = yaml.load(f, Loader=yaml.FullLoader)
            return BaseRobot(info_dict)


    def close(self):
        # close buses
        for bus in self.buses.values():
            bus.close()
