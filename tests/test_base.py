import unittest
import logging


from roboglia.base.bus import BaseBus, FileBus
from roboglia.base.register import BaseRegister, BoolRegister, \
                                    RegisterWithConversion, RegisterWithThreshold

logging.basicConfig(level=60)       # silent

def test_base_suite():
    suite = unittest.TestSuite()
    suite.addTest(TestBaseRegister('test_base_register_init'))
    suite.addTest(TestBaseRegister('test_base_register_value'))
    suite.addTest(TestBaseBus('test_base_bus_init'))
    suite.addTest(TestFileBus('test_file_bus_init'))
    return suite


class TestBaseRegister(unittest.TestCase):

    def test_base_register_init(self):
        init_dict = {}
        # name
        message = "name"
        with self.assertRaisesRegex(KeyError, message):
            _ = BaseRegister(init_dict)
        init_dict['name'] = 'reg_a'
        # device
        message = "device"
        with self.assertRaisesRegex(KeyError, message):
            _ = BaseRegister(init_dict)
        init_dict['device'] = None
        # address
        message = '"address" specification missing for register: reg_a'
        with self.assertRaisesRegex(KeyError, message):
            _ = BaseRegister(init_dict)
        init_dict['address'] = 12
        # positive test with defaults
        _ = BaseRegister(init_dict)
        # size
        init_dict['size'] = '1'
        message = "value 1 should be of type <class 'int'> for register: reg_a"
        with self.assertRaisesRegex(ValueError, message):
            _ = BaseRegister(init_dict)
        del init_dict['size']
        # min
        init_dict['min'] = '0'
        message = "value 0 should be of type <class 'int'> for register: reg_a"
        with self.assertRaisesRegex(ValueError, message):
            _ = BaseRegister(init_dict)
        del init_dict['min']
        # max
        init_dict['max'] = '255'
        message = "value 255 should be of type <class 'int'> for register: reg_a"
        with self.assertRaisesRegex(ValueError, message):
            _ = BaseRegister(init_dict)
        del init_dict['max']
        # access
        init_dict['access'] = 'RO'
        message = "value RO should be one of \['R', 'RW'\] for register: reg_a"
        with self.assertRaisesRegex(ValueError, message):
            _ = BaseRegister(init_dict)
        # positive tests for access
        init_dict['access'] = 'R'
        _ = BaseRegister(init_dict)
        init_dict['access'] = 'RW'
        _ = BaseRegister(init_dict)
        # sync
        init_dict['sync'] = 10
        message = "value 10 should be one of \[True, False\] for register: reg_a"
        with self.assertRaisesRegex(ValueError, message):
            _ = BaseRegister(init_dict)
        # positive tests for sync
        init_dict['sync'] = True
        _ = BaseRegister(init_dict)
        init_dict['sync'] = False
        _ = BaseRegister(init_dict)
        # default
        init_dict['default'] = '10'
        message = "value 10 should be of type <class 'int'> for register: reg_a"
        with self.assertRaisesRegex(ValueError, message):
            _ = BaseRegister(init_dict)
        del init_dict['default']

    def test_base_register_value(self):
        init_dict = {'name': 'reg_a',
                     'device': None,
                     'address': 12}
        reg = BaseRegister(init_dict)
        #self.assertEqual(reg.value,0)


class TestBaseBus(unittest.TestCase):

    def test_base_bus_init(self):
        # start with blank, "name" expected
        init_dict = {}
        message = "name"
        with self.assertRaisesRegex(KeyError, message):
            _ = BaseBus(init_dict)

        init_dict['name'] = 'test_bus'
        message = '"port" specification missing for bus: test_bus'
        with self.assertRaisesRegex(KeyError, message):
            _ = BaseBus(init_dict)

        init_dict['port'] = '/tmp/test.log'
        bus = BaseBus(init_dict)
       
        self.assertEqual(bus.name, 'test_bus')
        self.assertEqual(bus.port, '/tmp/test.log')
        self.assertFalse(bus.isOpen)

class TestFileBus(unittest.TestCase):

    def test_file_bus_init(self):
        init_dict = {'name': 'file_bus',
                     'port': '/non_existent_path/test.log'}
        message = "No such file or directory" #
        bus = FileBus(init_dict)
        with self.assertRaisesRegex(FileNotFoundError, message):
            bus.open()

        init_dict['port'] = '/tmp/test.log'
        bus = FileBus(init_dict)
        self.assertFalse(bus.isOpen)
        bus.open()
        self.assertTrue(bus.isOpen)
        bus.close()
        self.assertFalse(bus.isOpen)

    def test_file_write(self):
        init_dict = {'name': 'file_bus',
                     'port': '/tmp/test.log'}
        bus = FileBus(init_dict)
        bus.open()
