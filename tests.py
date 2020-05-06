import unittest
import sys
import logging
import yaml
import time
import argparse

format = '%(asctime)s %(levelname)-7s %(threadName)-18s %(name)-32s %(message)s'
logging.basicConfig(format=format, 
                    # file = 'test.log', 
                    level=60)    # silent
#logging.getLogger('roboglia.base.robot').setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)     # need for checks

from roboglia.base import BaseRobot
from roboglia.dynamixel import DynamixelBus
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

    def test_mock_robot_members(self):
        self.assertListEqual(list(dummy.buses.keys()), ['busA'])
        self.assertListEqual(list(dummy.devices.keys()), ['d01', 'd02'])
        self.assertListEqual(list(dummy.joints.keys()), ['pan', 'tilt'])
        self.assertListEqual(list(dummy.groups.keys()), ['devices', 'joints', 'all'])
        self.assertListEqual(list(dummy.syncs.keys()), ['read', 'write'])

    def test_mock_robot_registers(self):  
        d01 = dummy.devices['d01']
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
        pan = dummy.joints['pan']
        d01 = dummy.devices['d01']
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
        # reset back
        pan.active = False

    def test_mock_robot_joints_position(self):
        pan = dummy.joints['pan']
        tilt = dummy.joints['tilt']
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
        pan = dummy.joints['pan']
        tilt = dummy.joints['tilt']
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
        pan = dummy.joints['pan']
        tilt = dummy.joints['tilt']
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
        d02 = dummy.devices['d02']
        regs = d02.registers
        self.assertIn('current_pos', regs)
        self.assertIn('[model]: 42 (42)', str(d02))


class TestMH2Robot(unittest.TestCase):

    def test_mh2_robot_members(self):
        self.assertListEqual(list(mh2.buses.keys()), ['ttyUSB0', 'ttyUSB1', 'ttyUSB2', 'ttyUSB3'])
        self.assertListEqual(list(mh2.devices.keys()), ['d11', 'd12', 'd13', 'd14', 'd15', 'd16',
                                                               'd21', 'd22', 'd23', 'd24', 'd25', 'd26',
                                                               'd36', 'd37'])
        self.assertListEqual(list(mh2.groups.keys()), ['head', 'right_leg', 'left_leg', 'all_servos'])
        # self.assertListEqual(list(mh2.joints.keys()), ['pan', 'tilt'])
        self.assertListEqual(list(mh2.syncs.keys()), ['leds', 'volt_temp'])

    def test_mh2_robot_registers_simple(self):
        d11 = mh2.devices['d11']
        # model number
        self.assertEqual(d11.model_number.value, 350)
    
    def test_mh2_robot_registers_read_write(self):
        d11 = mh2.devices['d11']
        # R/W on return delay time
        d11.return_delay_time.value = 100
        self.assertAlmostEqual(d11.return_delay_time.value, 100, places=2)
        d11.return_delay_time.value = 0
        self.assertAlmostEqual(d11.return_delay_time.value, 0, places=2)
    
    def test_mh2_robot_registers_boolean(self):  
        d11 = mh2.devices['d11']
        # boolean register
        self.assertFalse(d11.moving.value)

    def test_mh2_robot_registers_conversion(self):  
        d36 = mh2.devices['d36']
        # conversion register
        self.assertAlmostEqual(d36.present_speed_rpm.value, 0, places=2)
        voltage = d36.present_voltage.value
        self.assertTrue(6 < voltage < 9)
        # setting conversion register
        d36.goal_position_deg.value = 20
        self.assertAlmostEqual(d36.goal_position_deg.value, 20.0, delta=0.2)
        d36.moving_speed_rpm.value = 30
        self.assertAlmostEqual(d36.moving_speed_rpm.value, 30.0, delta=0.1)
        d36.goal_position_deg.value = 0
        d36.moving_speed_rpm.value = 0


    def test_mh2_robot_registers_baud_rate(self):  
        d11 = mh2.devices['d11']
        # baud_rate conversions and handling of wrong values
        d11.baud_rate.value = 1000000
        self.assertEqual(d11.baud_rate.value, 1000000)
        d11.baud_rate.value = 42
        self.assertEqual(d11.baud_rate.value, 1000000)

    def test_mh2_robot_registers_pid(self):  
        d21 = mh2.devices['d21']
        # d-gain
        #self.assertEqual(d21.d_gain.value, 0)
        d21.d_gain.value = 0.5
        self.assertAlmostEqual(d21.d_gain.value, 0.5, places=3)
        self.assertAlmostEqual(d21.d_gain.int_value, 125, places=3)
        d21.d_gain.value = 0
        # i-gain
        #self.assertEqual(d21.i_gain.value, 0)
        d21.i_gain.value = 100
        self.assertAlmostEqual(d21.i_gain.value, 100, delta=0.2)
        self.assertEqual(d21.i_gain.int_value, 205)
        d21.i_gain.value = 0
        # p-gain
        #self.assertEqual(d21.p_gain.value, 4)
        d21.p_gain.value = 20
        self.assertAlmostEqual(d21.p_gain.value, 20, delta=0.2)
        self.assertEqual(d21.p_gain.int_value, 160)
        d21.p_gain.value = 4

    # def test_mh2_robot_joints_properties(self):
    #     pan = mh2.joints['pan']
    #     d01 = mh2.devices['d01']
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

    # def test_mh2_robot_joints_position(self):
    #     pan = mh2.joints['pan']
    #     tilt = mh2.joints['tilt']
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

    # def test_mh2_robot_joints_velocity(self):
    #     pan = mh2.joints['pan']
    #     tilt = mh2.joints['tilt']
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

    # def test_mh2_robot_joints_load(self):
    #     pan = mh2.joints['pan']
    #     tilt = mh2.joints['tilt']
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

    def test_mh2_robot_devices(self):
        d22 = mh2.devices['d22']
        regs = d22.registers
        self.assertIn('baud_rate', regs)
        self.assertIn('[model_number]: 350 (350)', str(d22))


class TestMH2Loops(unittest.TestCase):

    def test_mh2_start_syncwrite(self):
        syncwrite = mh2.syncs['leds']
        # check devices registers are flagged for sync
        for dev in ['d11', 'd12', 'd13', 'd14', 'd15', 'd16']:
            self.assertTrue(mh2.devices[dev].led.sync)
        syncwrite.start()

    def test_mh2_start_syncread(self):
        syncread = mh2.syncs['volt_temp']
        # check devices registers are flagged for sync
        for dev in ['d21', 'd22', 'd23', 'd24', 'd25', 'd26']:
            self.assertTrue(mh2.devices[dev].present_voltage.sync)
            self.assertTrue(mh2.devices[dev].present_temperature.sync)
        syncread.start()
        

    def test_mh2_pause_syncs(self):
        # logging.basicConfig(level=logging.WARNING)
        read_sync = mh2.syncs['volt_temp']
        read_sync.start()       # may restart
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
        # logging.basicConfig(level=60)

    # def test_sync_underrun(self):
    #     write_sync = mh2.syncs['write']
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
    #     write_sync = mh2.syncs['write']
    #     # resume a not paused thread
    #     write_sync.resume()
    #     # pause a non running thread
    #     write_sync.pause()
    #     # start an already started thread
    #     write_sync.start()
    #     write_sync.start()



class TestBaseLoops(unittest.TestCase):


    def test_mock_start_syncs(self):
        logging.basicConfig(level=logging.WARNING)
        read_sync = dummy.syncs['read']
        read_sync.start()
        write_sync = dummy.syncs['write']
        write_sync.start()
        time.sleep(1.5)         # we need more than 1s to check statistics
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

    def test_mock_pause_syncs(self):
        logging.basicConfig(level=logging.WARNING)
        read_sync = dummy.syncs['read']
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

    def test_mock_sync_underrun(self):
        write_sync = dummy.syncs['write']
        # check warning < 2
        write_sync.warning = 1.05
        self.assertEqual(write_sync.warning, 1.05)
        # warning < 110
        write_sync.warning = 105
        self.assertEqual(write_sync.warning, 1.05)
        # warning > 110
        write_sync.warning = 200
        self.assertEqual(write_sync.warning, 1.05)
        logging.basicConfig(level=logging.WARNING)
        write_sync.start()
        time.sleep(1.5)
        write_sync.stop()
        time.sleep(0.2)
        logging.basicConfig(level=60)

    def test_mock_sync_small_branches(self):
        write_sync = dummy.syncs['write']
        # resume a not paused thread
        write_sync.resume()
        # pause a non running thread
        write_sync.pause()
        # start an already started thread
        write_sync.start()
        write_sync.start()


class TestMH4Robot(unittest.TestCase):

    def test_mh4_robot_members(self):
        self.assertListEqual(list(mh4.buses.keys()), ['ttySC1', 'ttySC0'])
        self.assertListEqual(list(mh4.devices.keys()), ['d01', 'd02', 'd03', 'd04'])
        self.assertListEqual(list(mh4.groups.keys()), ['head', 'shoulders', 'all_servos'])
        # self.assertListEqual(list(mh4.joints.keys()), ['pan', 'tilt'])
        self.assertListEqual(list(mh4.syncs.keys()), ['leds'])

    def test_mh4_robot_registers_simple(self):
        d01 = mh4.devices['d01']
        # model number
        self.assertEqual(d01.model_number.value, 12)
    
    def test_mh4_robot_registers_read_write(self):
        d01 = mh4.devices['d01']
        # R/W on return delay time
        d01.return_delay_time.value = 100
        self.assertAlmostEqual(d01.return_delay_time.value, 100, places=2)
        d01.return_delay_time.value = 0
        self.assertAlmostEqual(d01.return_delay_time.value, 0, places=2)
    
    def test_mh4_robot_registers_boolean(self):  
        d01 = mh4.devices['d01']
        # boolean register
        self.assertFalse(d01.moving.value)

    def test_mh4_robot_registers_conversion(self):  
        d01 = mh4.devices['d01']
        # conversion register
        self.assertAlmostEqual(d01.present_speed.value, 0, places=2)
        self.assertAlmostEqual(d01.present_load.value, 0, places=2)
        # setting conversion register
        d01.goal_position.value = 20
        self.assertAlmostEqual(d01.goal_position.value, 20.0, delta=0.2)
        d01.moving_speed.value = 30
        self.assertAlmostEqual(d01.moving_speed.value, 30.0, delta=0.1)

    def test_mh4_robot_registers_baud_rate(self):  
        d01 = mh4.devices['d01']
        # baud_rate conversions and handling of wrong values
        d01.baud_rate.value = 1000000
        self.assertEqual(d01.baud_rate.value, 1000000)
        d01.baud_rate.value = 42
        self.assertEqual(d01.baud_rate.value, 1000000)

    def test_mh4_robot_registers_compliance(self):  
        d01 = mh4.devices['d01']
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

    # def test_mh4_robot_joints_properties(self):
    #     pan = mh4.joints['pan']
    #     d01 = mh4.devices['d01']
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

    # def test_mh4_robot_joints_position(self):
    #     pan = mh4.joints['pan']
    #     tilt = mh4.joints['tilt']
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

    # def test_mh4_robot_joints_velocity(self):
    #     pan = mh4.joints['pan']
    #     tilt = mh4.joints['tilt']
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

    # def test_mh4_robot_joints_load(self):
    #     pan = mh4.joints['pan']
    #     tilt = mh4.joints['tilt']
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

    def test_mh4_robot_devices(self):
        d02 = mh4.devices['d02']
        regs = d02.registers
        self.assertIn('baud_rate', regs)
        self.assertIn('[model_number]: 12 (12)', str(d02))


class TestMH4Loops(unittest.TestCase):

    def test_start_syncs(self):
        logging.basicConfig(level=logging.WARNING)
        syncwrite = mh4.syncs['leds']
        # check devices registers are flagged for sync
        self.assertTrue(mh4.devices['d03'].led.sync)
        self.assertTrue(mh4.devices['d03'].led.sync)
        syncwrite.start()
        time.sleep(0.5)

    # def test_pause_syncs(self):
    #     logging.basicConfig(level=logging.WARNING)
    #     read_sync = mh4.syncs['read']
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
    #     write_sync = mh4.syncs['write']
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
    #     write_sync = mh4.syncs['write']
    #     # resume a not paused thread
    #     write_sync.resume()
    #     # pause a non running thread
    #     write_sync.pause()
    #     # start an already started thread
    #     write_sync.start()
    #     write_sync.start()

mh4 = None
mh2 = None

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Unittest robglia')
    parser.add_argument('--mh2', 
                        action='store_true', 
                        help='include on-device tests with MH2 (Dynamixel 2.0)')
    parser.add_argument('--mh4', 
                        action='store_true', 
                        help='include on-device tests with MH4 (Dynamixel 1.0)')


    args = vars(parser.parse_args())


    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite()

    # generic tests
    print('Loading and initializing DUMMY robot. This might take a while...', end='')
    dummy = BaseRobot.from_yaml('tests/dummy_robot.yml')
    dummy.start()
    print('Init finished...')
    suite.addTest(loader.loadTestsFromTestCase(TestRobot))
    suite.addTest(loader.loadTestsFromTestCase(TestBaseLoops))
    suite.addTest(loader.loadTestsFromTestCase(TestFactoryNegative))
    suite.addTest(loader.loadTestsFromTestCase(TestChecksNegative))

    if args['mh4']:

        suite.addTest(loader.loadTestsFromTestCase(TestMH4Robot))
        suite.addTest(loader.loadTestsFromTestCase(TestMH4Loops))

    if args['mh2']:
        print('Loading and initializing MH2 robot. This might take a while...', end='')
        mh2 = BaseRobot.from_yaml('tests/MH2_robot.yml')
        mh2.start()
        print('Init finished...')
        suite.addTest(loader.loadTestsFromTestCase(TestMH2Robot))
        suite.addTest(loader.loadTestsFromTestCase(TestMH2Loops))

    runner = unittest.TextTestRunner(stream=sys.stdout, verbosity=2)
    runner.run(suite)

    if mh2:
        mh2.stop()
    if mh4:
        mh4.stop()
