import unittest
import sys
import logging
import yaml

logging.basicConfig(level=60)           # silent
logger = logging.getLogger(__name__)     # need for checks

from roboglia.base import BaseRobot
from roboglia.utils import register_class, unregister_class, \
    get_registered_class, registered_classes
from roboglia.utils import check_key, check_type, check_options

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
        self.assertIn('Test', registered_classes())
        unregister_class('Test')
        self.assertNotIn('Test', registered_classes())

    def test_get_registered_class_not_avaialable(self):
        mess = 'not registered with the factory'
        with self.assertRaisesRegex(KeyError, mess):
            get_registered_class('dummy')

    def test_register_class_existing(self):
        class Test: pass
        register_class(Test)
        # again
        register_class(Test)
        self.assertIn('Test', registered_classes())
        unregister_class('Test')
        self.assertNotIn('Test', registered_classes())


class TestChecksNegative(unittest.TestCase):

    def test_check_key(self):
        mess = 'specification missing'
        with self.assertRaisesRegex(KeyError, mess):
            check_key('key', {}, 'object', 10, logger)
        with self.assertRaisesRegex(KeyError, 'custom'):
            check_key('key', {}, 'object', 10, logger, 'custom')

    def test_check_type(self):
        mess = 'should be of type'
        with self.assertRaisesRegex(ValueError, mess):
            check_type('10', int, 'object', 10, logger)
        with self.assertRaisesRegex(ValueError, 'custom'):
            check_type('10', int, 'object', 10, logger, 'custom')

    def test_check_options(self):
        mess = 'should be one of'
        with self.assertRaisesRegex(ValueError, mess):
            check_options(10, ['a', 'b'], 'object', 10, logger)  
        with self.assertRaisesRegex(ValueError, 'custom'):
            check_options(10, ['a', 'b'], 'object', 10, logger, 'custom')

class TestRobot(unittest.TestCase):

    def setUp(self):
        robot_init = yaml.load("""
            buses:
                - name: busA
                  class: ShareableFileBus
                  port: /tmp/busA.log

            devices:
                - name: d01
                  class: BaseDevice
                  bus: busA
                  id: 1
                  model: DUMMY

                - name: d02
                  class: BaseDevice
                  bus: busA
                  id: 2
                  model: DUMMY

            joints:
                - name: pan
                  class: Joint
                  device: d01
                  pos_read: current_pos
                  pos_write: desired_pos
                  activate: enable

                - name: tilt
                  class: Joint
                  device: d02
                  pos_read: current_pos
                  pos_write: desired_pos
                  activate: enable

            groups:
                - name: devices
                  devices: [d01, d02]

                - name: joints
                  joints: [pan, tilt]

                - name: all
                  groups: [devices, joints]

            syncs:
                - name: read
                  class: BaseReadSync
                  frequency: 10.0
                  group: devices
                  registers: ['current_pos', 'current_speed', 'current_load']
                  start: False

                - name: write
                  class: BaseWriteSync
                  frequency: 10.0
                  group: devices
                  registers: ['desired_pos', 'desired_speed', 'desired_load']
                  start: False

        """, Loader=yaml.FullLoader)
        self.robot = BaseRobot(robot_init)
        self.robot.start()

    def test_mock_robot_members(self):
        self.assertListEqual(list(self.robot.buses.keys()), ['busA'])
        self.assertListEqual(list(self.robot.devices.keys()), ['d01', 'd02'])
        self.assertListEqual(list(self.robot.joints.keys()), ['pan', 'tilt'])
        self.assertListEqual(list(self.robot.groups.keys()), ['devices', 'joints', 'all'])
        self.assertListEqual(list(self.robot.syncs.keys()), ['read', 'write'])

    def test_mock_robot_registers(self):  
        d01 = self.robot.devices['d01']
        self.assertEqual(d01.model.value, 42)
        self.assertAlmostEqual(d01.delay.value, 500, places=2)
        d01.delay.value = 100
        self.assertAlmostEqual(d01.delay.value, 100, places=2)
        self.assertFalse(d01.enable.value)
        self.assertAlmostEqual(d01.current_speed.value, 57.0557185, places=2)
        self.assertAlmostEqual(d01.current_load.value, -50.0, places=2)
        d01.desired_pos.value = 20
        self.assertAlmostEqual(d01.desired_pos.value, 20.0, delta=0.2)
        d01.desired_speed.value = 30
        self.assertAlmostEqual(d01.desired_speed.value, 30.0, delta=0.1)

    def test_mock_robot_joints(self):
        pan = self.robot.joints['pan']
        d01 = self.robot.devices['d01']
        self.assertEqual(pan.name, 'pan')
        self.assertEqual(pan.device, d01)
        self.assertEqual(pan.position_read_register, d01.current_pos)
        self.assertEqual(pan.position_write_register, d01.desired_pos)
        self.assertEqual(pan.activate_register, d01.enable)
        self.assertFalse(pan.active)
        pan.active = True
        self.assertTrue(pan.active)
        self.assertFalse(pan.inverse)
        self.assertEqual(pan.offset, 0)
        self.assertEqual(pan.range, (None, None))

    def tearDown(self):
        self.robot.stop()



if __name__ == '__main__':
    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite()
    suite.addTest(loader.loadTestsFromTestCase(TestRobot))
    suite.addTest(loader.loadTestsFromTestCase(TestFactoryNegative))
    suite.addTest(loader.loadTestsFromTestCase(TestChecksNegative))
    runner = unittest.TextTestRunner(stream=sys.stdout, verbosity=2)
    runner.run(suite)
