import unittest
import sys
import logging
import yaml

logging.basicConfig(level=60)       # silent

from roboglia.base import BaseRobot
from roboglia.utils import register_class, unregister_class, \
    get_registered_class, registered_classes

class TestFactoryNegative(unittest.TestCase):

    def test_register_not_class(self):
        mess = 'You must pass a Class not an instance'
        with self.assertRaisesRegex(ValueError, mess):
            register_class(10)

    def test_unregister_missing_class(self):
        mess = 'not registered with the factory'
        with self.assertRaisesRegex(KeyError, mess):
            unregister_class('dummy')

    def test_unregister_class(self):
        class Test: pass
        register_class(Test)
        self.assertTrue('Test' in registered_classes())
        unregister_class('Test')
        self.assertFalse('Test' in registered_classes())


class TestRobot(unittest.TestCase):

    def setUp(self):
        self.robot = yaml.load("""
            buses:
                - name: busA
                  class: FileBus
                  port: /tmp/busA.log

            devices:
                - name: d01
                  class: BaseDevice
                  bus: busA
                  id: 1
                  model: DUMMY
        """, Loader=yaml.FullLoader)

    def test_mock_robot(self):
        _ = BaseRobot(self.robot)



if __name__ == '__main__':
    suite = unittest.TestSuite()
    suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(TestFactoryNegative))
    suite.addTest(TestRobot('test_mock_robot'))
    runner = unittest.TextTestRunner(stream=sys.stdout, verbosity=2)
    runner.run(suite)
