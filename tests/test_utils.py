import unittest
import logging
from roboglia.utils import get_registered_class, register_class, \
                                  registered_classes, unregister_class
from roboglia.utils import check_key, check_type, check_options

logger = logging.getLogger(__name__)
logger.setLevel(60)     # silent

class dummy():
    def __init__(self):
        self.val = 0

def test_utils_suite():
    suite = unittest.TestSuite()
    suite.addTest(TestFactory('test_register_class'))
    suite.addTest(TestFactory('test_reregister_class'))
    suite.addTest(TestFactory('test_allocate_class'))
    suite.addTest(TestFactory('test_unregistered_class'))

    suite.addTest(TestChecks('test_check_key'))
    suite.addTest(TestChecks('test_check_type_int'))
    suite.addTest(TestChecks('test_check_type_float'))
    suite.addTest(TestChecks('test_check_type_class'))

    return suite


class TestFactory(unittest.TestCase):

    def test_register_class(self):
        register_class(dummy)
        self.assertTrue('dummy' in registered_classes())
        # cleanup
        unregister_class('dummy')
        self.assertTrue('dummy' not in registered_classes())

    def test_reregister_class(self):
        register_class(dummy)
        self.assertTrue('dummy' in registered_classes())
        old_list = registered_classes()
        register_class(dummy)
        new_list = registered_classes()
        self.assertDictEqual(old_list, new_list)
        # cleanup
        unregister_class('dummy')
        self.assertTrue('dummy' not in registered_classes())

    def test_allocate_class(self):
        register_class(dummy)
        self.assertTrue('dummy' in registered_classes())
        new_class = get_registered_class('dummy')
        instance = new_class()
        self.assertIsInstance(instance, new_class)
        # cleanup
        unregister_class('dummy')
        self.assertTrue('dummy' not in registered_classes())

    def test_unregistered_class(self):
        with self.assertRaises(KeyError):
            _ = get_registered_class('missing')

class TestChecks(unittest.TestCase):

    def test_check_key(self):
        message = '"name" specification missing for device: 10'
        with self.assertRaisesRegex(KeyError, message):
            check_key('name', {}, 'device', 10, logger)
        check_key('name', {'name':'d01'}, 'context', 10, logger)

    def test_check_type_int(self):
        message = "value 10 should be of type <class 'int'> for register: position"
        with self.assertRaisesRegex(ValueError, message):
            check_type('10', int, 'register', 'position', logger)
        check_type(10, int, 'register', 'position', logger)

    def test_check_type_float(self):
        message = "value 10.0 should be of type <class 'float'> for register: position"
        with self.assertRaisesRegex(ValueError, message):
            check_type('10.0', float, 'register', 'position', logger)
        check_type(10.0, float, 'register', 'position', logger)

    def test_check_type_class(self):
        d = dummy()
        message = "value d should be of type <class 'test_utils.dummy'> for register: position"
        with self.assertRaisesRegex(ValueError, message):
            check_type('d', dummy, 'register', 'position', logger)
        check_type(d, dummy, 'register', 'position', logger)

       
