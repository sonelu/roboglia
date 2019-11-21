"""
class I2CBus():

    def __init__(self, params):
        assert params['Class'] == 'I2CBus'
        self.name = params['Name']
        self.port = params['Port']

        self.porthandler = SMBus(self.port)

    def read1byte(self, dev_address, reg_address):
        return self.porthandler.read_byte_data(dev_address, reg_address)

    def read2bytes(self, dev_address, reg_address):
        d0 = self.porthandler.read_byte_data(dev_address, reg_address)
        d1 = self.porthandler.read_byte_data(dev_address, reg_address+1)
        return d1*256 + d0


class I2CDevice()


"""
