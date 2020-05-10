import pytest
import logging
import time
import yaml

from roboglia.utils import register_class, unregister_class, registered_classes, get_registered_class
from roboglia.utils import check_key, check_options, check_type

from roboglia.base import BaseRobot, BaseDevice
from roboglia.base import RegisterWithConversion, RegisterWithThreshold

from roboglia.dynamixel import DynamixelBus
from roboglia.dynamixel import DynamixelAXBaudRateRegister
from roboglia.dynamixel import DynamixelAXComplianceSlopeRegister
from roboglia.dynamixel import DynamixelXLBaudRateRegister


# logging.basicConfig(format=format, 
#                     # file = 'test.log', 
#                     level=60)    # silent
logger = logging.getLogger(__name__)



class TestMockRobot:

    @pytest.fixture
    def mock_robot(self):   
        robot = BaseRobot.from_yaml('tests/dummy_robot.yml')
        robot.start()
        yield robot
        robot.stop()

    def test_robot_from_yaml(self, mock_robot):
        mock_robot.stop()       # to avoid conflicts on the bus
        new_robot = BaseRobot.from_yaml('tests/dummy_robot.yml')
        new_robot.start()
        new_robot.syncs['write'].start()
        time.sleep(2)           # for loops to run
        new_robot.stop()
        mock_robot.start()      # restart for other cases

    def test_device_str(self, mock_robot):
        rep = str(mock_robot.devices['d01'])
        assert 'd01' in rep
        assert 'busA' in rep
        assert 'enable_device' in rep

    def test_register_with_conversion(self, mock_robot):
        reg = mock_robot.devices['d03'].desired_pos
        assert isinstance(reg, RegisterWithConversion)
        reg.value = 100
        assert abs(reg.value - 100) < 0.1
        exp_int = 100 * reg.factor + reg.offset
        assert (reg.int_value - exp_int) <=1

    def test_register_with_threshold(self, mock_robot):
        reg = mock_robot.devices['d03'].writtable_current_load
        assert isinstance(reg, RegisterWithThreshold)
        assert not reg.sync
        reg.value = 50
        assert abs(reg.value - 50) < 0.1
        exp_int = 100 * reg.factor
        assert (reg.int_value - exp_int) <=1
        reg.value = -50
        assert abs(reg.value + 50) < 0.1
        exp_int = 100 * reg.factor + reg.threshold
        assert (reg.int_value - exp_int) <=1
         

    def test_register_read_only(self, mock_robot, caplog):
        reg = mock_robot.devices['d03'].current_pos
        assert isinstance(reg, RegisterWithConversion)
        caplog.clear()
        reg.value = 100
        assert len(caplog.records) == 1
        assert 'attempted to write in RO register current_pos' in caplog.text

    def test_sync_pause_resume(self, mock_robot):
        write_sync = mock_robot.syncs['write']
        write_sync.start()
        assert write_sync.started
        assert write_sync.running
        assert not write_sync.paused
        assert not write_sync.stopped
        write_sync.pause()
        assert write_sync.started
        assert not write_sync.running
        assert write_sync.paused
        assert not write_sync.stopped
        time.sleep(0.5)
        write_sync.resume()
        assert write_sync.started
        assert write_sync.running
        assert not write_sync.paused
        assert not write_sync.stopped        
        write_sync.stop()
        assert not write_sync.started
        assert not write_sync.running
        assert not write_sync.paused
        assert write_sync.stopped          

    def test_sync_start_restart(self, mock_robot):
        write_sync = mock_robot.syncs['write']
        assert not write_sync.started
        assert not write_sync.running
        assert not write_sync.paused
        assert write_sync.stopped 
        # re-stop
        write_sync.stop()
        assert not write_sync.started
        assert not write_sync.running
        assert not write_sync.paused
        assert write_sync.stopped
        # start
        write_sync.start()
        assert write_sync.started
        assert write_sync.running
        assert not write_sync.paused
        assert not write_sync.stopped
        # re-start
        write_sync.start()
        assert write_sync.started
        assert write_sync.running
        assert not write_sync.paused
        assert not write_sync.stopped
        write_sync.stop()

    def test_loop_warning_review(self, mock_robot):
        read_sync = mock_robot.syncs['read']
        assert read_sync.warning == 0.9     # default
        read_sync.warning = 0.95
        assert read_sync.warning == 0.95
        # percentage set
        read_sync.warning = 90
        assert read_sync.warning == 0.9
        assert read_sync.review == 1.0      # default

    # def test_sync_with_closed_bus(self, mock_robot, caplog):
    #     write_sync = mock_robot.syncs['write']
    #     assert write_sync.stopped
    #     bus = write_sync.bus
    #     if bus.is_open:
    #         bus.close()
    #     assert not bus.is_open
    #     caplog.clear()
    #     write_sync.start()
    #     assert len(caplog.records) == 1
    #     assert 'attempt to start with a bus not open' in caplog.text
    #     assert write_sync.stopped
    #     # now set things back
    #     bus.open()
    #     assert bus.is_open

    # def test_thread_crash(self, mock_robot):
    #     read_sync = mock_robot.syncs['read']
    #     # save the current setup() function
    #     setup = read_sync.setup
    #     read_sync.setup = 'text'
    #     # now try to start; will raise error
    #     read_sync.start()

    def test_joint_info(self, mock_robot):
        j = mock_robot.joints['pan']
        d = mock_robot.devices['d01']
        assert j.position_read_register == d.current_pos
        assert j.position_write_register == d.desired_pos
        assert j.activate_register == d.enable_device
        assert j.velocity_read_register == d.current_speed
        assert j.velocity_write_register == d.desired_speed
        assert j.load_read_register == d.current_load
        assert j.load_write_register == d.desired_load
        assert j.active

    def test_joint_value(self, mock_robot):
        tilt = mock_robot.joints['tilt']
        d02 = mock_robot.devices['d02']
        # joint is 'inverse'
        assert tilt.position == - d02.current_pos.value + tilt.offset
        assert tilt.velocity ==  - d02.current_speed.value
        assert tilt.load == - d02.current_load.value
        # setter
        tilt.position = 10
        tilt.velocity = 20
        tilt.load = 50
        assert abs(tilt.desired_position - 10) < 0.2
        assert abs(tilt.desired_velocity - 20) < 0.2
        assert abs(tilt.desired_load - 50) < 0.2

    def test_joint_min_max(self, mock_robot):
        # check min and max
        pan = mock_robot.joints['pan']
        minv, maxv = pan.range
        pan.position = 50
        assert abs(pan.desired_position - maxv) < 0.2
        pan.position = -50
        assert abs(pan.desired_position - minv) < 0.2

    def test_joint_repr(self, mock_robot):
        pan = mock_robot.joints['pan']
        pan_str = str(pan)
        assert pan.name in pan_str
        assert 'p=' in pan_str
        assert 'v=' in pan_str
        assert 'l=' in pan_str

        """This doesn't work fine as closing a bus will crash a
        sync run that is using it."""
    # def test_bus_operate_on_close(self, mock_robot, caplog):
    #     bus = mock_robot.buses['busA']
    #     if bus.is_open:
    #         bus.close()
    #     assert not bus.is_open
    #     dev = mock_robot.devices['d01']
    #     caplog.clear()
    #     bus.read(dev, dev.current_pos)
    #     assert len(caplog.records) == 1
    #     assert 'attempt to read from a closed bus' in caplog.text
    #     bus.write(dev, dev.desired_pos, 10)
    #     assert len(caplog.records) == 2
    #     assert ('attempt to write to closed bus' in caplog.text)
    #     # reset bus
    #     bus.open()
    #     assert bus.is_open
 
    def test_bus_repr(self, mock_robot):
        str_repr = str(mock_robot.buses['busA'])
        dev = mock_robot.devices['d01']
        assert f'Device {dev.dev_id}' in str_repr
        for register in dev.registers.values():
            assert str(register.address) in str_repr
            assert str(register.int_value) in str_repr


class TestUtilsFactory:

    def test_register_not_class(self):
        mess = 'You must pass a Class not an instance'
        with pytest.raises(ValueError) as excinfo:
            register_class(10)
        assert mess in str(excinfo.value)

    def test_unregister_missing_class(self):
        mess = 'not registered with the factory'
        with pytest.raises(KeyError) as excinfo:
            unregister_class('dummy')
        assert mess in str(excinfo.value)

    def test_unregister_class(self):
        class Test: pass
        register_class(Test)
        assert 'Test' in registered_classes()
        unregister_class('Test')
        assert 'Test' not in registered_classes()

    def test_get_registered_class_not_avaialable(self):
        mess = 'not registered with the factory'
        with pytest.raises(KeyError) as excinfo:
            get_registered_class('dummy')
        assert mess in str(excinfo.value)

    def test_register_class_existing(self):
        class Test: pass
        register_class(Test)
        # again
        register_class(Test)
        assert 'Test' in registered_classes()
        unregister_class('Test')
        assert 'Test' not in registered_classes()


class TestUtilsChecks:

    def test_check_key(self):
        mess = 'specification missing'
        with pytest.raises(KeyError) as excinfo:
            check_key('key', {}, 'object', 10, logger)
        assert mess in str(excinfo.value)
        with pytest.raises(KeyError) as excinfo:
            check_key('key', {}, 'object', 10, logger, 'custom')
        assert 'custom' in str(excinfo.value)

    def test_check_type(self):
        mess = 'should be of type'
        with pytest.raises(ValueError) as excinfo:
            check_type('10', int, 'object', 10, logger)
        assert mess in str(excinfo.value)
        with pytest.raises(ValueError) as excinfo:
            check_type('10', int, 'object', 10, logger, 'custom')
        assert 'custom' in str(excinfo.value)

    def test_check_options(self):
        mess = 'should be one of'
        with pytest.raises(ValueError) as excinfo:
            check_options(10, ['a', 'b'], 'object', 10, logger)
        assert mess in str(excinfo.value)
        with pytest.raises(ValueError) as excinfo:
            check_options(10, ['a', 'b'], 'object', 10, logger, 'custom')
        assert 'custom' in str(excinfo.value)


class TestDynamixelRobot:

    @pytest.fixture
    def mock_robot_init(self):
        with open('tests/dynamixel_robot.yml', 'r') as f:
            info_dict = yaml.load(f, Loader=yaml.FullLoader)
        yield info_dict

    @pytest.fixture
    def dummy_device(self):
        return BaseDevice({
            'name': 'device',
            'bus': None,
            'id': 42,
            'model': 'DUMMY'
        })

    def test_dynamixel_robot(self, mock_robot_init):
        robot = BaseRobot(mock_robot_init)
        robot.start()
        robot.stop()

    def test_dynamixel_write(self, mock_robot_init):
        robot = BaseRobot(mock_robot_init)
        robot.start()
        dev = robot.devices['d11']
        dev.temperature_limit.value = 85
        assert dev.temperature_limit.value == 85
        robot.stop()

    def test_dynamixel__AXBaudRateRegister(self, dummy_device, caplog):
        reg = DynamixelAXBaudRateRegister({
            'name': 'test',
            'device': dummy_device,
            'address': 42,
            'sync': True,       # avoids calling read / write
            'access': 'RW'      # so we can change it!
        })
        reg.value = 1000000
        assert reg.value == 1000000
        assert reg.int_value == 1
        # wrong value > log error
        caplog.clear()
        reg.value = 99
        assert len(caplog.records) == 1
        assert 'attempt to write a non supported for AX baud' in caplog.text


    def test_dynamixel__AXComplianceSlopeRegister(self, dummy_device):
        reg = DynamixelAXComplianceSlopeRegister({
            'name': 'test',
            'device': dummy_device,
            'address': 42,
            'sync': True,       # avoids calling read / write
            'access': 'RW'      # so we can change it!
        })
        reg.value = 7
        assert reg.value == 7
        assert reg.int_value == 128


    def test_dynamixel__XLBaudRateRegister(self, dummy_device, caplog):
        reg = DynamixelXLBaudRateRegister({
            'name': 'test',
            'device': dummy_device,
            'address': 42,
            'sync': True,       # avoids calling read / write
            'access': 'RW'      # so we can change it!
        })
        reg.value = 1000000
        assert reg.value == 1000000
        assert reg.int_value == 3
        # wrong value > log error
        caplog.clear()
        reg.value = 99
        assert len(caplog.records) == 1
        assert 'attempt to write a non supported for XL baud' in caplog.text

    def test_open_device_with_sync_items(self, mock_robot_init):
        robot = BaseRobot(mock_robot_init)
        robot.start()
        dev = robot.devices['d11']
        dev.present_position_deg.sync = True
        dev.open()
        robot.stop()

    def test_dynamixel_writesync(self, mock_robot_init):
        robot = BaseRobot(mock_robot_init)
        robot.start()
        robot.syncs['goal'].start()
        time.sleep(0.5)
        robot.stop()

    def test_dynamixel_readsync(self, mock_robot_init):
        robot = BaseRobot(mock_robot_init)
        robot.start()
        robot.syncs['actual'].start()
        time.sleep(0.5)
        robot.stop()

    def test_dynamixel_scan(self, mock_robot_init):
        robot = BaseRobot(mock_robot_init)
        robot.start()
        ids = robot.buses['ttys1'].scan()
        assert 11 in ids
        assert 12 in ids
        robot.stop()

    def test_dynamixel_ping(self, mock_robot_init):
        robot = BaseRobot(mock_robot_init)
        robot.start()
        assert robot.buses['ttys1'].ping(11) == True
        robot.stop()
       

