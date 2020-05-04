import unittest
import sys
import logging
import yaml
import time

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
        self.robot = BaseRobot.from_yaml('tests/dummy_robot.yml')
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

    def test_mock_robot_joints_properties(self):
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

    def test_mock_robot_joints_position(self):
        pan = self.robot.joints['pan']
        tilt = self.robot.joints['tilt']
        self.assertAlmostEqual(pan.position,
            pan.position_read_register.value + pan.offset,
            places=3)
        self.assertAlmostEqual(tilt.position,
            - tilt.position_read_register.value + pan.offset,
            places=3)
        pan.position = 10.0
        tilt.position = 20.0
        self.assertAlmostEqual(pan.desired_position, 10.0, delta=0.5)
        self.assertAlmostEqual(tilt.desired_position, 20.0, delta=0.5)

    def test_mock_robot_joints_velocity(self):
        pan = self.robot.joints['pan']
        tilt = self.robot.joints['tilt']
        self.assertAlmostEqual(pan.velocity,
            pan.velocity_read_register.value,
            places=3)
        self.assertAlmostEqual(tilt.velocity,
            - tilt.velocity_read_register.value,
            places=3)
        pan.velocity = 10.0
        tilt.velocity = 20.0
        self.assertAlmostEqual(pan.desired_velocity, 10.0, delta=0.5)
        self.assertAlmostEqual(tilt.desired_velocity, 20.0, delta=0.5)

    def test_mock_robot_joints_load(self):
        pan = self.robot.joints['pan']
        tilt = self.robot.joints['tilt']
        self.assertAlmostEqual(pan.load,
            pan.load_read_register.value,
            places=3)
        self.assertAlmostEqual(tilt.load,
            - tilt.load_read_register.value,
            places=3)
        pan.load = 25.0
        tilt.load = 50.0
        self.assertAlmostEqual(pan.desired_load, 25.0, delta=0.5)
        self.assertAlmostEqual(tilt.desired_load, 50.0, delta=0.5)

    def test_mock_robot_devices(self):
        d02 = self.robot.devices['d02']
        regs = d02.registers
        self.assertIn('current_pos', regs)
        self.assertIn('[model]: 42 (42)', str(d02))

    def tearDown(self):
        self.robot.stop()


class TestBaseLoops(unittest.TestCase):

    def setUp(self):
        self.robot = BaseRobot.from_yaml('tests/dummy_robot.yml')
        self.robot.start()

    def test_start_syncs(self):
        logging.basicConfig(level=logging.WARNING)
        read_sync = self.robot.syncs['read']
        read_sync.start()
        write_sync = self.robot.syncs['write']
        write_sync.start()
        time.sleep(0.5)
        self.assertTrue(read_sync.started)
        self.assertFalse(read_sync.stopped)
        self.assertTrue(read_sync.running)
        self.assertFalse(read_sync.paused)
        read_sync.stop()
        write_sync.stop()
        time.sleep(0.5)
        self.assertFalse(read_sync.started)
        self.assertTrue(read_sync.stopped)
        self.assertFalse(read_sync.running)
        self.assertFalse(read_sync.paused)
        logging.basicConfig(level=60)

    def test_pause_syncs(self):
        logging.basicConfig(level=logging.WARNING)
        read_sync = self.robot.syncs['read']
        read_sync.start()
        time.sleep(0.2)
        read_sync.pause()
        time.sleep(0.2)
        self.assertTrue(read_sync.started)
        self.assertFalse(read_sync.stopped)
        self.assertFalse(read_sync.running)
        self.assertTrue(read_sync.paused)
        read_sync.resume()
        time.sleep(0.2)
        self.assertTrue(read_sync.started)
        self.assertFalse(read_sync.stopped)
        self.assertTrue(read_sync.running)
        self.assertFalse(read_sync.paused)
        read_sync.stop()
        time.sleep(0.2)
        logging.basicConfig(level=60)


if __name__ == '__main__':
    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite()
    suite.addTest(loader.loadTestsFromTestCase(TestRobot))
    suite.addTest(loader.loadTestsFromTestCase(TestBaseLoops))
    suite.addTest(loader.loadTestsFromTestCase(TestFactoryNegative))
    suite.addTest(loader.loadTestsFromTestCase(TestChecksNegative))
    runner = unittest.TextTestRunner(stream=sys.stdout, verbosity=2)
    runner.run(suite)
