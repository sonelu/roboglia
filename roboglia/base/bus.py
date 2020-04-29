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


    def open(self):
        self.__fp = open(self.port, 'w')


    def close(self):
        self.__fp.close()


    def isOpen(self):
        return not self.__fp.closed


    def write(self, dev, reg, value):
        self.__last[(dev.dev_id, reg.address)] = value
        self.__fp.write(f'written {value} in register {reg.address} of device {dev.dev_id}\n')
        self.__fp.flush()


    def read(self, dev, reg):
        if (dev.dev_id, reg.address) not in self.__last:
            self.__last[(dev.dev_id, reg.address)] = reg.default            
        val = self.__last[(dev.dev_id,reg.address)]
        self.__fp.write(f'read {val} from register {reg.address} of device {dev.dev_id}\n')
        self.__fp.flush()
        return val
        

    def __str__(self):
        result = ''
        for (dev_id, reg_address), value in self.__last.items():
            result += f'Device {dev_id}, Register ID {reg_address}: VALUE {value}\n'
        return result
        
    #     self.writeQueue = deque()


    # def writeQueueAdd(self, register):
    #     """Add a register to the write queue.

    #     Parameters
    #     ----------
    #     register : BaseRegister or subclass
    #         Register that is queed for deferred write. 
    #     """
    #     self.writeQueue.append(register)
    #     print('added to queue; len={}'.format(len(self.writeQueue)))

    # def writeQueueExec(self):
    #     """Invokes the register's `write()` method to syncronize the content
    #     of a register for all the requests in the ``writeQueue``. The robot
    #     is responsible for setting up a thread that calls regularly this 
    #     method for each bus owned in order to flush all queued requests
    #     for syncronization.

    #     .. note: This method might be very unperformant depending on the
    #        they of the bus since it will invoke transimtting a communication
    #        packet for each register included in the queue. For certain type
    #        of devices (ex. Dynamixel servos) there are more performant methods
    #        like using SyncWrite or BulkWrite that perform the write in a
    #        single communication packet for a series of devices and registers.

    #     """
    #     while len(self.writeQueue) > 0:
    #         register = self.writeQueue.popleft()
    #         register.write()
