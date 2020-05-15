import pytest
import logging
import time
import yaml

from roboglia.utils import register_class, unregister_class, registered_classes, get_registered_class
from roboglia.utils import check_key, check_options, check_type, check_not_empty

from roboglia.base import BaseRobot, BaseDevice, BaseBus, BaseRegister
from roboglia.base import RegisterWithConversion, RegisterWithThreshold
from roboglia.base import BaseThread

from roboglia.dynamixel import DynamixelBus
from roboglia.dynamixel import DynamixelAXBaudRateRegister
from roboglia.dynamixel import DynamixelAXComplianceSlopeRegister
from roboglia.dynamixel import DynamixelXLBaudRateRegister

from roboglia.i2c import SharedI2CBus


class TestMH2Robot:

    @pytest.fixture
    def mh2_robot(self):   
        robot = BaseRobot.from_yaml('tests/MH2_robot.yml')
        robot.start()
        yield robot
        robot.stop()

    def test_basic_test(self, mh2_robot):
        assert 'ttyUSB0' in mh2_robot.buses
        assert 'd11' in mh2_robot.devices
        assert 'imu_g' in mh2_robot.devices

    def test_i2c_read_write(self, mh2_robot):
        device = mh2_robot.devices['imu_g']
        assert device.who_am_i.value == 212
        assert device.ctrl_reg2.value == 0
        device.ctrl_reg1.value = 0x0f
        assert device.ctrl_reg1.value == 0x0f
        assert device.out_x.value != 0
        assert device.out_y.value != 0
        assert device.out_z.value != 0
        device.int1_ths_x.value = 30
        assert device.int1_ths_x.value == 30
        device.int1_ths_x.value = 0

 
