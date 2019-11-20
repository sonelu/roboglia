from .comm import DynamixelBus
from .utils import readIniFile
from .device import DynamixelServo

class Robot():

    def __init__(self, ini_file):
        config = readIniFile(ini_file)
        self.ports = {}
        self.devices = {}

        # load the port configuration
        for portconfig in config['ports']:
            PortClass = globals()[portconfig['Class']]
            new_port = PortClass(name=portconfig['Name'],
                                 port=portconfig['Port'])
            self.ports[portconfig['Name']] = new_port
        
        # load the devices
        for device in config['devices']:
            DevClass = globals()[device['Class']]
            new_device = DevClass(name=device['Name'],
                                  model=device['Type'],
                                  bus=self.ports[device['Bus']])
            new_device.id = device['Id']
            self.devices[device['Name']] = new_device
            self.ports[device['Bus']].devices.append(new_device)

    def __getattr__(self, attr):
        if attr in self.devices:
            return self.devices[attr]
        else:
            raise AttributeError(f'{self.__class__.__name__}.{attr} is invalid.')        