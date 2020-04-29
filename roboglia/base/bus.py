import logging

logger = logging.getLogger(__name__)

class BaseBus():
    """A base abstract class for handling an arbitrary bus.

    You will normally subclass ``BaseBus`` and define particular functionality
    specific to the bus by impementing the methods of the ``BaseBus``.
    This class only stores the name of the bus and the access to the
    physical object. Your subclass can add additional attributes and 
    methods to deal with the particularities of the real bus represented.

    Parameters
    ----------
    init_dict : dict
        Dictionary with the initializations values. At least `name` and
        `port` keys must be present otherwise the constructor will throw
        an exception.

    """
    def __init__(self, init_dict):
        # these will throw exceptions if info not provided in the init dict
        self.name = init_dict['name']
        self.port = init_dict['port']

    def open(self):
        """Opens the actual physical bus. Must be overriden by the
        subclass.
        """
        pass

    def close(self):
        """Closes the actual physical bus. Must be overriden by the
        subclass.
        """
        pass

    def isOpen(self):
        """Returns `True` or `False` if the bus is open. Must be overriden 
        by the subclass.
        """
        return False

    def read(self, dev, reg):
        """Reads one standrd information from the bus. Must be overwriden.
        """
        pass

    def write(self, dev, reg, val):
        """Writes one standrd information from the bus. Must be overwriden.
        """
        pass


class FileBus(BaseBus):
    """A bus that writes to a file. Read returns the last writen data.
    Provided for testing purposes.
    """
    def __init__(self, init_dict):
        super().__init__(init_dict)
        self.__fp = None
        self.__last = {}
        logger.debug(f'FileBus {self.name} initialized')

    def open(self):
        self.__fp = open(self.port, 'w')
        logger.debug(f'FileBus {self.name} opened')

    def close(self):
        self.__fp.close()
        logger.debug(f'FileBus {self.name} closed')

    def isOpen(self):
        return not self.__fp.closed

    def write(self, dev, reg, value):
        self.__last[(dev.dev_id, reg.address)] = value
        text = f'written {value} in register {reg.address} of device {dev.dev_id}'
        self.__fp.write(text+'\n')
        self.__fp.flush()
        logger.debug(f'FileBus {self.name} {text}')

    def read(self, dev, reg):
        if (dev.dev_id, reg.address) not in self.__last:
            self.__last[(dev.dev_id, reg.address)] = reg.default            
        val = self.__last[(dev.dev_id,reg.address)]
        text = f'read {val} from register {reg.address} of device {dev.dev_id}'
        self.__fp.write(text+'\n')
        self.__fp.flush()
        logger.debug(f'FileBus {self.name} {text}')
        return val
        
    def __str__(self):
        result = ''
        for (dev_id, reg_address), value in self.__last.items():
            result += f'Device {dev_id}, Register ID {reg_address}: VALUE {value}\n'
        return result