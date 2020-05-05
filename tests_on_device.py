import unittest
import sys
import logging
import yaml
import time

#
# Testing of functionality on device. This will not work on CI in a virtual
# machine because it will need to interogate actual devices and get responses
#

logging.basicConfig(level=60)           # silent
logger = logging.getLogger(__name__)     # need for checks

from roboglia.base import BaseRobot
from roboglia.dynamixel import DynamixelDevice
from roboglia.utils import register_class, unregister_class, \
    get_registered_class, registered_classes
from roboglia.utils import check_key, check_type, check_options


class TestDynamixelRobot(unittest.TestCase):

    def setUp(self):
        self.robot = BaseRobot.from_yaml('tests/dynamixel_robot.yml')
        self.robot.start()

    def test_mock_robot_members(self):
        self.assertListEqual(list(self.robot.buses.keys()), ['ttySC1', 'ttySC0'])
        self.assertListEqual(list(self.robot.devices.keys()), ['d01', 'd02', 'd03', 'd04'])
        self.assertListEqual(list(self.robot.groups.keys()), ['head', 'shoulders', 'all_servos'])
        # self.assertListEqual(list(self.robot.joints.keys()), ['pan', 'tilt'])
        self.assertListEqual(list(self.robot.syncs.keys()), ['leds'])

    def test_mock_robot_registers_simple(self):
        d01 = self.robot.devices['d01']
        # model number
        self.assertEqual(d01.model_number.value, 12)
    
    def test_mock_robot_registers_read_write(self):
        d01 = self.robot.devices['d01']
        # R/W on return delay time
        d01.return_delay_time.value = 100
        self.assertAlmostEqual(d01.return_delay_time.value, 100, places=2)
        d01.return_delay_time.value = 0
        self.assertAlmostEqual(d01.return_delay_time.value, 0, places=2)
    
    def test_mock_robot_registers_boolean(self):  
        d01 = self.robot.devices['d01']
        # boolean register
        self.assertFalse(d01.moving.value)

    def test_mock_robot_registers_conversion(self):  
        d01 = self.robot.devices['d01']
        # conversion register
        self.assertAlmostEqual(d01.present_speed.value, 0, places=2)
        self.assertAlmostEqual(d01.present_load.value, 0, places=2)
        # setting conversion register
        d01.goal_position.value = 20
        self.assertAlmostEqual(d01.goal_position.value, 20.0, delta=0.2)
        d01.moving_speed.value = 30
        self.assertAlmostEqual(d01.moving_speed.value, 30.0, delta=0.1)

    def test_mock_robot_registers_baud_rate(self):  
        d01 = self.robot.devices['d01']
        # baud_rate conversions and handling of wrong values
        d01.baud_rate.value = 1000000
        self.assertEqual(d01.baud_rate.value, 1000000)
        d01.baud_rate.value = 42
        self.assertEqual(d01.baud_rate.value, 1000000)

    def test_mock_robot_registers_compliance(self):  
        d01 = self.robot.devices['d01']
        # baud_rate conversions and handling of wrong values
        current = d01.cw_compliance_slope.value
        d01.cw_compliance_slope.value = 3
        self.assertEqual(d01.cw_compliance_slope.value, 3)
        self.assertEqual(d01.cw_compliance_slope.int_value, 8)
        d01.cw_compliance_slope.value = 5
        self.assertEqual(d01.cw_compliance_slope.value, 5)
        self.assertEqual(d01.cw_compliance_slope.int_value, 32)
        # reset to default
        d01.cw_compliance_slope.value = current

    # def test_mock_robot_joints_properties(self):
    #     pan = self.robot.joints['pan']
    #     d01 = self.robot.devices['d01']
    #     self.assertEqual(pan.name, 'pan')
    #     self.assertEqual(pan.device, d01)
    #     self.assertEqual(pan.position_read_register, d01.current_pos)
    #     self.assertEqual(pan.position_write_register, d01.desired_pos)
    #     self.assertEqual(pan.activate_register, d01.enable)
    #     self.assertFalse(pan.active)
    #     pan.active = True
    #     self.assertTrue(pan.active)
    #     self.assertFalse(pan.inverse)
    #     self.assertEqual(pan.offset, 0)
    #     self.assertEqual(pan.range, (None, None))

    # def test_mock_robot_joints_position(self):
    #     pan = self.robot.joints['pan']
    #     tilt = self.robot.joints['tilt']
    #     self.assertAlmostEqual(pan.position,
    #         pan.position_read_register.value + pan.offset,
    #         places=3)
    #     self.assertAlmostEqual(tilt.position,
    #         - tilt.position_read_register.value + pan.offset,
    #         places=3)
    #     pan.position = 10.0
    #     tilt.position = 20.0
    #     self.assertAlmostEqual(pan.desired_position, 10.0, delta=0.5)
    #     self.assertAlmostEqual(tilt.desired_position, 20.0, delta=0.5)

    # def test_mock_robot_joints_velocity(self):
    #     pan = self.robot.joints['pan']
    #     tilt = self.robot.joints['tilt']
    #     self.assertAlmostEqual(pan.velocity,
    #         pan.velocity_read_register.value,
    #         places=3)
    #     self.assertAlmostEqual(tilt.velocity,
    #         - tilt.velocity_read_register.value,
    #         places=3)
    #     pan.velocity = 10.0
    #     tilt.velocity = 20.0
    #     self.assertAlmostEqual(pan.desired_velocity, 10.0, delta=0.5)
    #     self.assertAlmostEqual(tilt.desired_velocity, 20.0, delta=0.5)

    # def test_mock_robot_joints_load(self):
    #     pan = self.robot.joints['pan']
    #     tilt = self.robot.joints['tilt']
    #     self.assertAlmostEqual(pan.load,
    #         pan.load_read_register.value,
    #         places=3)
    #     self.assertAlmostEqual(tilt.load,
    #         - tilt.load_read_register.value,
    #         places=3)
    #     pan.load = 25.0
    #     tilt.load = 50.0
    #     self.assertAlmostEqual(pan.desired_load, 25.0, delta=0.5)
    #     self.assertAlmostEqual(tilt.desired_load, 50.0, delta=0.5)

    def test_mock_robot_devices(self):
        d02 = self.robot.devices['d02']
        regs = d02.registers
        self.assertIn('baud_rate', regs)
        self.assertIn('[model_number]: 12 (12)', str(d02))

    def tearDown(self):
        self.robot.stop()


class TestDynamixelLoops(unittest.TestCase):

    def setUp(self):
        self.robot = BaseRobot.from_yaml('tests/dynamixel_robot.yml')
        self.robot.start()

    def test_start_syncs(self):
        logging.basicConfig(level=logging.WARNING)
        syncwrite = self.robot.syncs['leds']
        # check devices registers are flagged for sync
        self.assertTrue(self.robot.devices['d03'].led.sync)
        self.assertTrue(self.robot.devices['d03'].led.sync)
        syncwrite.start()
        time.sleep(0.5)

    # def test_pause_syncs(self):
    #     logging.basicConfig(level=logging.WARNING)
    #     read_sync = self.robot.syncs['read']
    #     read_sync.start()
    #     time.sleep(0.2)
    #     read_sync.pause()
    #     time.sleep(0.2)
    #     self.assertTrue(read_sync.started)
    #     self.assertFalse(read_sync.stopped)
    #     self.assertFalse(read_sync.running)
    #     self.assertTrue(read_sync.paused)
    #     read_sync.resume()
    #     time.sleep(0.2)
    #     self.assertTrue(read_sync.started)
    #     self.assertFalse(read_sync.stopped)
    #     self.assertTrue(read_sync.running)
    #     self.assertFalse(read_sync.paused)
    #     read_sync.stop()
    #     time.sleep(0.2)
    #     logging.basicConfig(level=60)

    # def test_sync_underrun(self):
    #     write_sync = self.robot.syncs['write']
    #     # check warning < 2
    #     write_sync.warning = 1.05
    #     self.assertEqual(write_sync.warning, 1.05)
    #     # warning < 110
    #     write_sync.warning = 105
    #     self.assertEqual(write_sync.warning, 1.05)
    #     # warning > 110
    #     write_sync.warning = 200
    #     self.assertEqual(write_sync.warning, 1.05)
    #     logging.basicConfig(level=logging.WARNING)
    #     write_sync.start()
    #     time.sleep(1.5)
    #     write_sync.stop()
    #     time.sleep(0.2)
    #     logging.basicConfig(level=60)

    # def test_sync_small_branches(self):
    #     write_sync = self.robot.syncs['write']
    #     # resume a not paused thread
    #     write_sync.resume()
    #     # pause a non running thread
    #     write_sync.pause()
    #     # start an already started thread
    #     write_sync.start()
    #     write_sync.start()

    def tearDown(self):
        self.robot.stop()

if __name__ == '__main__':
    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite()
    suite.addTest(loader.loadTestsFromTestCase(TestDynamixelRobot))
    suite.addTest(loader.loadTestsFromTestCase(TestDynamixelLoops))
    # suite.addTest(loader.loadTestsFromTestCase(TestFactoryNegative))
    # suite.addTest(loader.loadTestsFromTestCase(TestChecksNegative))
    runner = unittest.TextTestRunner(stream=sys.stdout, verbosity=2)
    runner.run(suite)
