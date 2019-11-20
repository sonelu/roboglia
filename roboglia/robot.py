from .comm import DynamixelBus
from .utils import readIniFile

class Robot():

    def __init__(self, ini_file):
        config = readIniFile(ini_file)
        self.ports = []

        # load the port configuration
        for portconfig in config['ports']:
            PortClass = globals()[portconfig['Class']]
            new_port = PortClass(portconfig)
            self.ports.append(new_port)
        