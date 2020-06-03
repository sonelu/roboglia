import pytest
import logging
import time
import yaml
from math import nan

from roboglia.utils import register_class, unregister_class, registered_classes, get_registered_class
from roboglia.utils import check_key, check_options, check_type, check_not_empty

from roboglia.base import BaseRobot, BaseDevice, BaseBus, BaseRegister
from roboglia.base import RegisterWithConversion, RegisterWithThreshold
from roboglia.base import RegisterWithMapping
from roboglia.base import BaseThread
from roboglia.base import PVL, PVLList

from roboglia.dynamixel import DynamixelBus
from roboglia.dynamixel import DynamixelAXBaudRateRegister
from roboglia.dynamixel import DynamixelAXComplianceSlopeRegister
from roboglia.dynamixel import DynamixelXLBaudRateRegister

from roboglia.i2c import SharedI2CBus



from roboglia.move import Script

# format = '%(asctime)s %(levelname)-7s %(threadName)-18s %(name)-32s %(message)s'
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
    
    @pytest.fixture
    def dummy_device(self):
        bus = BaseBus(robot='robot', port='dev')
        return BaseDevice(name='device', bus=bus, dev_id=42, model='DUMMY',
                          robot='robot')

    def test_incomplete_robot(self, caplog):
        with pytest.raises(ValueError) as excinfo:
            _ = BaseRobot.from_yaml('tests/no_buses.yml')
        assert 'you need at least one bus for the robot' in str(excinfo.value)

        with pytest.raises(ValueError) as excinfo:
            _ = BaseRobot.from_yaml('tests/no_devices.yml')
        assert 'you need at least one device for the robot' in str(excinfo.value)

        caplog.clear()
        _ = BaseRobot.from_yaml('tests/dummy_robot.yml')
        assert 'Only the first robot will be considered' in caplog.text

    def test_robot_from_yaml(self, mock_robot):
        mock_robot.stop()       # to avoid conflicts on the bus
        new_robot = BaseRobot.from_yaml('tests/dummy_robot.yml')
        new_robot.start()
        new_robot.syncs['write'].start()
        time.sleep(2)           # for loops to run
        new_robot.stop()
        mock_robot.start()      # restart for other cases
        assert mock_robot.name == 'dummy'

    def test_device_str(self, mock_robot):
        rep = str(mock_robot.devices['d01'])
        assert 'd01' in rep
        assert 'busA' in rep
        assert 'enable_device' in rep

    def test_register_bool(self, mock_robot):
        device = mock_robot.devices['d03']
        assert not device.status.clone
        assert device.status_unmasked.clone
        assert device.status_one.clone
        assert device.status_2and3.clone
        assert device.status_2or3.clone
        # values
        assert device.status_unmasked.value
        assert device.status_one.value
        assert not device.status_2and3.value
        assert device.status_2or3.value
        # setting
        device.status_unmasked.value = False
        assert not device.status_unmasked.value
        device.status_2and3.value = True
        assert device.status_2and3.value
        assert device.status_2and3.int_value == 0b00000110

    def test_register_bool_with_mask(self, mock_robot):
        device = mock_robot.devices['d03']
        assert not device.status_masked.value
        device.status_masked.value = True
        assert device.status_masked.value
        assert device.status_masked.int_value == 0b10100101

    def test_register_with_conversion(self, mock_robot, caplog):
        reg = mock_robot.devices['d03'].desired_pos
        assert isinstance(reg, RegisterWithConversion)
        reg.value = 100
        assert abs(reg.value - 100) < 0.1
        exp_int = 100 * reg.factor + reg.offset
        assert (reg.int_value - exp_int) <=1
        assert reg.range == (0,1023)
        exp_min_ext = - 150.0
        exp_max_ext = 150.0
        assert (reg.min_ext - exp_min_ext) < 1
        assert (reg.max_ext - exp_max_ext) < 1
        ext_range = reg.range_ext
        assert (ext_range[0] - exp_min_ext) < 1
        assert (ext_range[1] - exp_max_ext) < 1
        # try changing the internal value directly
        # removed after bug #64
        # 
        # caplog.clear()
        # reg.int_value = 1
        # assert len(caplog.records) >= 1
        # assert 'only BaseSync subclasses can change' in caplog.text

    def test_register_with_threshold(self, mock_robot):
        reg = mock_robot.devices['d03'].writeable_current_load
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

    def test_register_with_mapping(self, dummy_device, caplog):
        reg = RegisterWithMapping(
            name='test',
            device=dummy_device,
            address=42,
            mask=0b00000011,
            sync=True,        # avoids calling read / write
            access='RW',      # so we can change it!
            mapping={1:100, 2:2000, 3:30000}
        )
        reg.value = 100
        assert reg.value == 100
        assert reg.int_value == 1
        # wrong value > log error
        caplog.clear()
        reg.value = 99
        assert len(caplog.records) == 1
        assert 'when converting to internal for register' in caplog.text

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
        assert read_sync.frequency == 100

    def test_sync_with_closed_bus(self, mock_robot, caplog):
        write_sync = mock_robot.syncs['write']
        assert write_sync.stopped
        bus = write_sync.bus
        caplog.clear()
        if bus.is_open:
            bus.close()
        assert len(caplog.records) >= 1
        assert 'that is used by running syncs' in caplog.text
        assert bus.is_open
        read_sync = mock_robot.syncs['read']
        read_sync.stop()
        if bus.is_open:
            bus.close()
        assert not bus.is_open
        caplog.clear()
        write_sync.start()
        assert len(caplog.records) == 1
        assert 'attempt to start with a bus not open' in caplog.text
        assert write_sync.stopped
        # now set things back
        bus.open()
        assert bus.is_open

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

    def test_joint_no_activate(self, mock_robot, caplog):
        joint = mock_robot.joints['no_activate']
        assert joint.active
        caplog.clear()
        joint.active = True
        assert len(caplog.records) >= 1
        assert 'attempted to change activation of joint' in caplog.text

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

    def test_sensor_info(self, mock_robot):
        s = mock_robot.sensors['bus_voltage']
        d = mock_robot.devices['d01']
        assert s.device == d
        assert s.read_register == d.current_voltage
        assert s.activate_register is None
        assert s.active
        # assert s.bits is None
        assert s.offset == 0
        assert not s.inverse
        assert s.auto_activate

    def test_sensor_value(self, mock_robot):
        s = mock_robot.sensors['bus_voltage']
        d = mock_robot.devices['d01']
        assert s.value == d.current_voltage.value

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
        dev = mock_robot.devices['d01']
        for register in dev.registers.values():
            register.read()
        str_repr = str(mock_robot.buses['busA'])
        assert f'Device {dev.dev_id}' in str_repr
        for register in dev.registers.values():
            if not register.sync:
                assert str(register.address) in str_repr
                assert str(register.int_value) in str_repr

    def test_bus_acquire(self, mock_robot, caplog):
        dev = mock_robot.devices['d01']
        bus = mock_robot.buses['busA']
        # stop syncs to avoid interference (additional messages)
        for sync in mock_robot.syncs.values():
            sync.stop()
        bus.can_use()      # lock the bus
        # read
        caplog.clear()
        bus.read(dev.current_pos)
        assert len(caplog.records) == 1
        assert 'failed to acquire bus busA' in caplog.text
        # write
        caplog.clear()
        bus.write(dev.current_pos, 10)
        assert len(caplog.records) >= 1
        assert 'failed to acquire bus busA' in caplog.text        
        # release bus
        bus.stop_using()
        mock_robot.stop()

    def test_bus_small_branches(self, mock_robot, caplog):
        bus = mock_robot.buses['busA']
        # close bus used by syncs
        caplog.clear()
        bus.close()
        assert len(caplog.records) == 1
        assert 'attempted to close bus' in caplog.text
        # open bus already open
        caplog.clear()
        bus.open()
        assert len(caplog.records) == 1
        assert 'bus busA already open' in caplog.text
        # read from closed bus
        device = mock_robot.devices['d04']
        caplog.clear()
        device.delay.write()
        assert len(caplog.records) == 1
        assert 'attempt to write to closed bus' in caplog.text
        caplog.clear()
        device.model.read()
        assert len(caplog.records) == 1
        assert 'attempt to read from closed bus' in caplog.text
        # timeout
        assert bus.timeout == 0.5

    def test_thread_crash(self):
        class CrashAtRun(BaseThread):
            def run(self):
                time.sleep(0.25)
                raise OSError

        class CrashAtSetup(BaseThread):
            def setup(self):
                time.sleep(.25)
                raise OSError

        class CrashLongSetup(BaseThread):
            def setup(self):
                time.sleep(1)
                raise OSError

        thread = CrashAtRun(name='my_thread')
        thread.start()
        time.sleep(0.5)
        assert not thread.started
        assert not thread.paused

        thread = CrashAtSetup(name='my_thread', patience=0.3)
        with pytest.raises(RuntimeError):
            thread.start()
            time.sleep(0.5)
        assert not thread.started
        assert not thread.paused       

        thread = CrashLongSetup(name='my_thread', patience=0.3)
        with pytest.raises(RuntimeError):
            thread.start()
            time.sleep(0.5)
        assert not thread.started
        assert not thread.paused      

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

    def test_get_registered_class_not_available(self):
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
        with pytest.raises(ValueError) as excinfo:
            check_type('10', [int, float], 'object', 10, logger)        

    def test_check_options(self):
        mess = 'should be one of'
        with pytest.raises(ValueError) as excinfo:
            check_options(10, ['a', 'b'], 'object', 10, logger)
        assert mess in str(excinfo.value)
        with pytest.raises(ValueError) as excinfo:
            check_options(10, ['a', 'b'], 'object', 10, logger, 'custom')
        assert 'custom' in str(excinfo.value)

    def test_check_not_empty(self):
        mess = 'should not be empty'
        # string
        with pytest.raises(ValueError) as excinfo:
            check_not_empty('', 'string', 'object', 10, logger)
        assert mess in str(excinfo.value)
        # number
        with pytest.raises(ValueError) as excinfo:
            check_not_empty(0, 'integer', 'object', 10, logger)
        assert mess in str(excinfo.value)
        # list
        with pytest.raises(ValueError) as excinfo:
            check_not_empty([], 'list', 'object', 10, logger)
        assert mess in str(excinfo.value)
        # dict
        with pytest.raises(ValueError) as excinfo:
            check_not_empty({}, 'dict', 'object', 10, logger)
        assert mess in str(excinfo.value)
        # custom message
        with pytest.raises(ValueError) as excinfo:
            check_not_empty('', 'string', 'object', 10, logger, 'custom')
        assert 'custom' in str(excinfo.value)


class TestDynamixelRobot:

    @pytest.fixture
    def mock_robot_init(self):
        with open('tests/dynamixel_robot.yml', 'r') as f:
            info_dict = yaml.load(f, Loader=yaml.FullLoader)
        yield info_dict

    @pytest.fixture
    def dummy_device(self):
        bus = BaseBus(robot='robot', port='dev')
        return BaseDevice(name='device', bus=bus, dev_id=42, model='DUMMY',
                          robot='robot')

    def test_dynamixel_robot(self, mock_robot_init):
        for name, init_dict in mock_robot_init.items():
            break
        robot = BaseRobot(name=name, **init_dict)
        robot.start()
        robot.stop()

    def test_dynamixel_write(self, mock_robot_init):
        robot = BaseRobot(**mock_robot_init['dynamixel'])
        robot.start()
        dev = robot.devices['d11']
        for _ in range(100):           # so that we also hit some comm errors
            dev.temperature_limit.value = 85
            assert dev.temperature_limit.value == 85
            dev.cw_angle_limit_deg.value = 10
            assert (dev.cw_angle_limit_deg.value - 10) < 0.2
        robot.stop()

    def test_dynamixel_register_4Bytes(self, mock_robot_init):
        robot = BaseRobot(**mock_robot_init['dynamixel'])
        robot.start()
        dev = robot.devices['d11']
        register = BaseRegister(name='test', device=dev, address=150, size=4,
                 access='RW')
        register.value = 100
        assert register.value == 100

    def test_dynamixel__AXBaudRateRegister(self, dummy_device, caplog):
        reg = DynamixelAXBaudRateRegister(
            name='test',
            device=dummy_device,
            address=42,
            minim=33,        # for testing branches
            maxim=66,        # for testing branches
            sync=True,       # avoids calling read / write
            access='RW'      # so we can change it!
        )
        reg.value = 1000000
        assert reg.value == 1000000
        assert reg.int_value == 1
        # wrong value > log error
        caplog.clear()
        reg.value = 99
        assert len(caplog.records) == 1
        assert 'attempt to write a non supported for AX baud' in caplog.text


    def test_dynamixel__AXComplianceSlopeRegister(self, dummy_device):
        reg = DynamixelAXComplianceSlopeRegister(
            name='test',
            device=dummy_device,
            address=42,
            maxim=66,        # for testing branches
            sync=True,       # avoids calling read / write
            access='RW'      # so we can change it!
        )
        reg.value = 7
        assert reg.value == 7
        assert reg.int_value == 128


    def test_dynamixel__XLBaudRateRegister(self, dummy_device, caplog):
        reg = DynamixelXLBaudRateRegister(
            name='test',
            device=dummy_device,
            address=42,
            minim=33,        # for testing branches
            maxim=66,        # for testing branches
            sync=True,       # avoids calling read / write
            access='RW'      # so we can change it!
        )
        reg.value = 1000000
        assert reg.value == 1000000
        assert reg.int_value == 3
        # wrong value > log error
        caplog.clear()
        reg.value = 99
        assert len(caplog.records) == 1
        assert 'attempt to write a non supported for XL baud' in caplog.text

    def test_open_device_with_sync_items(self, mock_robot_init):
        robot = BaseRobot(**mock_robot_init['dynamixel'])
        robot.start()
        dev = robot.devices['d11']
        dev.present_position_deg.sync = True
        dev.open()
        robot.stop()

    def test_dynamixel_syncwrite(self, mock_robot_init):
        robot = BaseRobot(**mock_robot_init['dynamixel'])
        robot.start()
        robot.syncs['syncwrite'].start()
        time.sleep(1)
        robot.stop()

    def test_dynamixel_syncread(self, mock_robot_init):
        robot = BaseRobot(**mock_robot_init['dynamixel'])
        robot.start()
        robot.syncs['syncread'].start()
        time.sleep(1)
        robot.stop()

    def test_dynamixel_bulkwrite(self, mock_robot_init):
        robot = BaseRobot(**mock_robot_init['dynamixel'])
        robot.start()
        robot.syncs['bulkwrite'].start()
        time.sleep(1)
        robot.stop()

    def test_dynamixel_bulkread(self, mock_robot_init):
        robot = BaseRobot(**mock_robot_init['dynamixel'])
        robot.start()
        robot.syncs['bulkread'].start()
        time.sleep(1)
        robot.stop()

    def test_dynamixel_rangeread(self, mock_robot_init):
        robot = BaseRobot(**mock_robot_init['dynamixel'])
        robot.start()
        robot.syncs['rangeread'].start()
        time.sleep(1)
        robot.stop()

    def test_protocol1_syncread(self, mock_robot_init):
        mock_robot_init['dynamixel']['buses']['ttys1']['protocol'] = 1.0
        # we remove the bulkwrite so that the error will refer to syncread
        del mock_robot_init['dynamixel']['syncs']['bulkwrite']
        with pytest.raises(ValueError) as excinfo:
            _ = BaseRobot(**mock_robot_init['dynamixel'])
        assert 'SyncRead only supported for Dynamixel Protocol 2.0' \
            in str(excinfo.value)

    def test_protocol1_bulkwrite(self, mock_robot_init):
        mock_robot_init['dynamixel']['buses']['ttys1']['protocol'] = 1.0
        # we remove the bulkwrite so that the error will refer to syncread
        del mock_robot_init['dynamixel']['syncs']['syncread']
        with pytest.raises(ValueError) as excinfo:
            _ = BaseRobot(**mock_robot_init['dynamixel'])
        assert 'BulkWrite only supported for Dynamixel Protocol 2.0' \
            in str(excinfo.value)

    def test_dynamixel_scan(self, mock_robot_init):
        robot = BaseRobot(**mock_robot_init['dynamixel'])
        robot.start()
        ids = robot.buses['ttys1'].scan()
        assert 11 in ids
        assert 12 in ids
        robot.stop()

    def test_dynamixel_ping(self, mock_robot_init):
        robot = BaseRobot(**mock_robot_init['dynamixel'])
        robot.start()
        assert robot.buses['ttys1'].ping(11) == True
        robot.stop()

    # def test_dynamixel_bus_set_port_handler(self, mock_robot_init):
    #     robot = BaseRobot(mock_robot_init)
    #     mess = 'you can use the setter only with MockBus'
    #     with pytest.raises(ValueError) as excinfo:
    #         robot.buses['ttys1'].port_handler = 'dummy'
    #     assert mess in str(excinfo.value)
    #     robot.stop()
    
    # def test_dynamixel_bus_set_packet_handler(self, mock_robot_init):
    #     robot = BaseRobot(mock_robot_init)
    #     mess = 'you can use the setter only with MockPacketHandler'
    #     with pytest.raises(ValueError) as excinfo:
    #         robot.buses['ttys1'].packet_handler = 'dummy'
    #     assert mess in str(excinfo.value)
    #     robot.stop()

    def test_dynamixel_bus_params(self, mock_robot_init):
        robot = BaseRobot(**mock_robot_init['dynamixel'])
        assert robot.buses['ttys1'].baudrate == 19200
        assert not robot.buses['ttys1'].rs485
        robot.stop()

    def test_dynamixel_bus_closed(self, mock_robot_init, caplog):
        robot = BaseRobot(**mock_robot_init['dynamixel'])
        bus = robot.buses['ttys1']
        # ping
        caplog.clear()
        bus.ping(11)
        assert len(caplog.records) == 1
        assert 'Ping invoked with a bus not opened' in caplog.text
        # scan
        caplog.clear()
        bus.scan(range(10))
        assert len(caplog.records) == 1
        assert 'Scan invoked with a bus not opened' in caplog.text
        # read
        dev = robot.devices['d11']
        caplog.clear()
        bus.read(dev.return_delay_time)
        assert len(caplog.records) == 1
        assert 'Attempt to use closed bus "ttys1"' in caplog.text
        # write
        caplog.clear()
        bus.write(dev.return_delay_time, 10)
        assert len(caplog.records) == 1
        assert 'Attempt to use closed bus "ttys1"' in caplog.text
        robot.stop()


    def test_dynamixel_bus_acquire(self, mock_robot_init, caplog):
        robot = BaseRobot(**mock_robot_init['dynamixel'])
        robot.start()
        dev = robot.devices['d11']
        bus = robot.buses['ttys1']
        bus.can_use()      # lock the bus
        # read
        caplog.clear()
        bus.read(dev.return_delay_time)
        assert len(caplog.records) >= 1
        assert 'failed to acquire bus ttys1' in caplog.text
        # write
        caplog.clear()
        bus.write(dev.return_delay_time, 10)
        assert len(caplog.records) >= 1
        assert 'failed to acquire bus ttys1' in caplog.text
        # release bus
        bus.stop_using()
        robot.stop()

    def test_dynamixel_bus_acquire_syncwrite(self, mock_robot_init, caplog):
        # syncs
        robot = BaseRobot(**mock_robot_init['dynamixel'])
        robot.start()
        robot.buses['ttys1'].can_use()      # lock the bus
        caplog.clear()
        robot.syncs['syncwrite'].start()
        time.sleep(1)
        assert len(caplog.records) >= 1
        assert 'failed to acquire bus ttys1' in caplog.text
        robot.syncs['syncwrite'].stop()
        # release bus
        robot.buses['ttys1'].stop_using()
        robot.stop()

    def test_dynamixel_bus_acquire_syncread(self, mock_robot_init, caplog):
        # syncs
        robot = BaseRobot(**mock_robot_init['dynamixel'])
        robot.start()
        robot.buses['ttys1'].can_use()      # lock the bus
        caplog.clear()
        robot.syncs['syncread'].start()
        time.sleep(1)
        assert len(caplog.records) >= 1
        assert 'failed to acquire bus ttys1' in caplog.text
        robot.syncs['syncread'].stop()
        # release bus
        robot.buses['ttys1'].stop_using()
        robot.stop()

    def test_dynamixel_bus_acquire_bulkwrite(self, mock_robot_init, caplog):
        # syncs
        robot = BaseRobot(**mock_robot_init['dynamixel'])
        robot.start()
        robot.buses['ttys1'].can_use()      # lock the bus
        caplog.clear()
        robot.syncs['bulkwrite'].start()
        time.sleep(1)
        assert len(caplog.records) >= 1
        assert 'failed to acquire bus ttys1' in caplog.text
        robot.syncs['bulkwrite'].stop()
        # release bus
        robot.buses['ttys1'].stop_using()
        robot.stop()

    def test_dynamixel_bus_acquire_bulkread(self, mock_robot_init, caplog):
        # syncs
        robot = BaseRobot(**mock_robot_init['dynamixel'])
        robot.start()
        robot.buses['ttys1'].can_use()      # lock the bus
        caplog.clear()
        robot.syncs['bulkread'].start()
        time.sleep(1)
        assert len(caplog.records) >= 1
        assert 'failed to acquire bus ttys1' in caplog.text
        robot.syncs['bulkread'].stop()
        # release bus
        robot.buses['ttys1'].stop_using()
        robot.stop()

    def test_dynamixel_register_low_endian(self, mock_robot_init, caplog):
        robot = BaseRobot(**mock_robot_init['dynamixel'])
        dev = robot.devices['d11']
        assert dev.register_low_endian(123, 4) == [123, 0, 0, 0]
        num = 12 * 256 + 42
        assert dev.register_low_endian(num, 4) == [42, 12, 0, 0]
        num = 39 * 65536 + 12 * 256 + 42
        assert dev.register_low_endian(num, 4) == [42, 12, 39, 0]
        num = 45 * 16777216 + 39 * 65536 + 12 * 256 + 42
        assert dev.register_low_endian(num, 4) == [42, 12, 39, 45]
        caplog.clear()
        _ = dev.register_low_endian(num, 6)
        assert len(caplog.records) == 1
        assert 'Unexpected register size' in caplog.text

class TestI2CRobot:

    @pytest.fixture
    def mock_robot_init(self):
        with open('tests/i2c_robot.yml', 'r') as f:
            info_dict = yaml.load(f, Loader=yaml.FullLoader)
        yield info_dict

    def test_i2c_robot_bus_error(self, mock_robot_init, caplog):
        mock_robot_init['i2crobot']['buses']['i2c2']['mock'] = False
        mock_robot_init['i2crobot']['buses']['i2c2']['auto'] = False
        mock_robot_init['i2crobot']['buses']['i2c2']['port'] = 42
        robot = BaseRobot(**mock_robot_init['i2crobot'])
        caplog.clear()
        robot.buses['i2c2'].open()
        assert len(caplog.records) >= 2
        assert 'failed to open I2C bus' in caplog.text
        # caplog.clear()
        # robot.buses['i2c2'].close()
        # assert len(caplog.records) == 2
        # assert 'failed to close I2C bus' in caplog.text

    def test_i2c_robot(self, mock_robot_init, caplog):
        robot = BaseRobot(**mock_robot_init['i2crobot'])
        robot.start()
        dev = robot.devices['imu']
        # 1 Byte registers
        for _ in range(5):              # to account for possible comm errs
            dev.byte_xl_x.value = 20
            assert dev.byte_xl_x.value == 20
            # word register
            dev.word_xl_x.value = 12345
            assert dev.word_xl_x.value == 12345      
        robot.stop()

    def test_i2c_register_with_sign(self, mock_robot_init):
        robot = BaseRobot(**mock_robot_init['i2crobot'])
        robot.start()
        d = robot.devices['imu']
        # no factor
        d.word_xl_x.value = 10
        assert d.word_xl_x.value == 10
        assert d.word_xl_x.int_value == 10
        d.word_xl_x.value = -10
        assert d.word_xl_x.value == -10
        assert d.word_xl_x.int_value == (65536 - 10)
        # with factor
        d.word_xl_y.value = 100
        assert d.word_xl_y.value == 100
        assert d.word_xl_y.int_value == 1000
        d.word_xl_y.value = -100
        assert d.word_xl_y.value == -100
        assert d.word_xl_y.int_value == (65536 - 1000)

    def test_i2c_sensor(self, mock_robot_init, caplog):
        robot = BaseRobot(**mock_robot_init['i2crobot'])
        robot.start()
        s = robot.sensors['temp']
        d = robot.devices['imu']
        assert s.device == d
        assert s.read_register == d.temp
        assert s.activate_register == d.activate_temp
        assert not s.active
        # removed the masking in sensor
        # assert s.bits is None
        assert s.offset == 0
        assert s.inverse
        assert s.auto_activate
        s.active = True
        assert s.active
        assert s.value == -10.0
        # masks
        assert robot.sensors['status0'].value 
        assert not robot.sensors['status1'].value
        # setting active for register w/o active register
        caplog.clear()
        robot.sensors['status0'].active = True
        assert len(caplog.records) == 1
        assert 'attempted to change activation of sensor' in caplog.text

    def test_i2c_sensorXYZ(self, mock_robot_init):
        robot = BaseRobot(**mock_robot_init['i2crobot'])
        robot.start()
        s = robot.sensors['gyro']
        d = robot.devices['imu']
        assert s.device == d
        assert s.x_register == d. word_g_x
        assert s.y_register == d. word_g_y
        assert s.z_register == d. word_g_z
        assert s.activate_register == d.activate_g
        assert not s.active
        assert s.x_offset == 0
        assert s.x_inverse
        assert s.y_offset == 256
        assert not s.y_inverse
        assert s.z_offset == 1024
        assert s.z_inverse        
        assert s.auto_activate
        s.active = True
        assert s.active

    def test_i2c_sensorXYZ_value(self, mock_robot_init, caplog):
        robot = BaseRobot(**mock_robot_init['i2crobot'])
        robot.start()
        s = robot.sensors['gyro']
        d = robot.devices['imu']
        exp_x = - d.word_g_x.value
        exp_y = d.word_g_y.value + 256
        exp_z = - d.word_g_z.value + 1024
        assert s.x == exp_x
        assert s.y == exp_y
        assert s.z == exp_z
        assert s.value == (exp_x, exp_y, exp_z)
        # byte sensor
        s = robot.sensors['accel_byte']
        exp_x = d.byte_xl_x.value + 128
        exp_y = - d.byte_xl_y.value -128
        exp_z = d.byte_xl_z.value + 64
        assert s.x == exp_x
        assert s.y == exp_y
        assert s.z == exp_z
        assert s.value == (exp_x, exp_y, exp_z)
        assert s.active
        # activate w/o register
        caplog.clear()
        s.active = True
        assert len(caplog.records) == 1
        assert 'attempted to change activation of sensor' in caplog.text

    def test_i2c_bus_closed(self, mock_robot_init, caplog):
        robot = BaseRobot(**mock_robot_init['i2crobot'])
        dev = robot.devices['imu']
        # write to closed bus
        caplog.clear()
        dev.byte_xl_x.value = 20
        assert len(caplog.records) >= 1
        assert 'attempted to write to a closed bus' in caplog.text
        # read from closed bus
        caplog.clear()
        _ = dev.byte_xl_x.value
        assert len(caplog.records) >= 1
        assert 'attempted to read from a closed bus' in caplog.text

    def test_i2c_read_loop(self, mock_robot_init):
        robot = BaseRobot(**mock_robot_init['i2crobot'])
        robot.start()
        robot.syncs['read_g'].start()
        time.sleep(1)
        robot.stop()

    def test_i2c_write_loop(self, mock_robot_init):
        robot = BaseRobot(**mock_robot_init['i2crobot'])
        robot.start()
        robot.syncs['write_xl'].start()
        time.sleep(1)
        robot.stop()

    def test_i2c_loop_failed_acquire(self, mock_robot_init, caplog):
        robot = BaseRobot(**mock_robot_init['i2crobot'])
        robot.start()
        # lock the bus
        robot.buses['i2c2'].can_use()
        # read
        caplog.clear()
        robot.syncs['read_g'].start()
        time.sleep(1)
        assert len(caplog.records) >= 1
        assert 'failed to acquire bus' in caplog.text
        robot.syncs['read_g'].stop()    
        # write
        caplog.clear()
        robot.syncs['write_xl'].start()
        time.sleep(1)
        assert len(caplog.records) >= 1
        assert 'failed to acquire bus' in caplog.text
        robot.syncs['read_g'].stop()    

    def test_i2c_sharedbus_closed(self, mock_robot_init, caplog):
        robot = BaseRobot(**mock_robot_init['i2crobot'])
        # we haven't started the bus
        # read
        caplog.clear()
        robot.syncs['read_g'].start()
        assert len(caplog.records) == 1
        assert 'attempt to start with a bus not open' in caplog.text
        robot.syncs['read_g'].stop()    
        # write
        caplog.clear()
        robot.syncs['write_xl'].start()
        assert len(caplog.records) == 1
        assert 'attempt to start with a bus not open' in caplog.text
        robot.syncs['read_g'].stop()

    def test_i2c_write2_with_errors(self, mock_robot_init, caplog):
        robot = BaseRobot(**mock_robot_init['i2crobot'])
        robot.start()
        device = robot.devices['imu']
        for _ in range(20):     # so that we also get some errors
            device.word_control_2.value = 0x2121
        assert device.word_control_2.value == 0x2121

    def test_i2c_closed_bus(self, mock_robot_init, caplog):
        robot = BaseRobot(**mock_robot_init['i2crobot'])
        device = robot.devices['imu']
        caplog.clear()
        _ = device.word_control_2.value
        assert len(caplog.records) >= 1
        assert 'attempted to read from a closed bus' in caplog.text
        caplog.clear()
        device.word_control_2.value = 0x4242
        assert len(caplog.records) >= 1
        assert 'attempted to write to a closed bus' in caplog.text
        bus = robot.buses['i2c2']
        caplog.clear()
        _ = bus.read_block_data(1, 1, 6)
        assert len(caplog.records) >= 1
        assert 'attempted to read from a closed bus' in caplog.text
        caplog.clear()
        bus.write_block_data(1, 1, 6, [1,2,3,4,5,6])
        assert len(caplog.records) >= 1
        assert 'attempted to write to a closed bus' in caplog.text


class TestMove:

    @pytest.fixture
    def mock_robot(self):   
        robot = BaseRobot.from_yaml('tests/move_robot.yml')
        robot.start()
        yield robot
        robot.stop()

    def test_pvl(self):
        list1 = PVLList(p=[1,2,3], v=[nan], ld=[nan, 10, 10, nan])
        assert len(list1) == 4
        list1.append(p=10, v=20, ld=nan)
        assert len(list1) == 5
        assert list1.positions == [1, 2, 3, nan, 10]
        assert list1.velocities == [nan, nan, nan, nan, 20]
        assert list1.loads == [nan, 10, 10, nan, nan]
        list1.append(p_list=[20, nan], v_list=[nan, nan, nan], l_list=[])
        assert len(list1) == 8
        list2 = PVLList(p=[3,4,5], v=[1,1,1], ld=[5,5,5])
        list1.append(pvl_list=list2)
        assert len(list1) == 11
        list1.append(pvl=PVL(p=4, v=5, ld=6))
        assert len(list1) == 12
        assert list1.positions == [1, 2, 3, nan, 10, 20, nan, nan, 3, 4, 5, 4]
        # func with one item
        list3 = PVLList()
        list3.append(pvl=PVL(10,10,10))
        avg = list3.process()
        assert avg == PVL(10,10,10)
        assert avg != 10
        # adition
        pvl1 = PVL(10, nan, nan)
        assert pvl1 + 10 == PVL(20, nan, nan)
        assert pvl1 - 10 == PVL(0, nan, nan)
        assert pvl1 + PVL(5, 10, nan) == PVL(15, nan, nan)
        assert pvl1 - PVL(5, 10, nan) == PVL(5, nan, nan)
        assert pvl1 + [10, 20, 30] == PVL(20, nan, nan)
        assert pvl1 - [10, 20, 30] == PVL(0, nan, nan)
        assert -pvl1 == PVL(-10, nan, nan)
        assert  not pvl1 == PVL(nan, nan, nan)
        # raise errors
        with pytest.raises(RuntimeError):
            _ = pvl1 + [1,2]
        with pytest.raises(RuntimeError):
            _ = pvl1 + 'string'
        with pytest.raises(RuntimeError):
            _ = pvl1 - [1,2]
        with pytest.raises(RuntimeError):
            _ = pvl1 - 'string'
        
        
    def test_move_load_robot(self, mock_robot):
        manager = mock_robot.manager
        assert len(manager.joints) == 3
        p = PVL(100)
        pv = PVL(100, 10)
        pvl = PVL(100, 10, 50)
        all_comm = [p, pv, pvl]
        for joint in manager.joints:
            for comm in all_comm:
                joint.value = comm
        assert mock_robot.joints['j01'].value == PVL(0,nan,nan)
        assert mock_robot.joints['j02'].value == PVL(0,57.05,nan)
        assert mock_robot.joints['j03'].value == PVL(0,57.05,-50.0)
        assert mock_robot.joints['j01'].desired == PVL(100, nan, nan)
        assert mock_robot.joints['j02'].desired == PVL(100, 10.03, nan)
        assert mock_robot.joints['j03'].desired == PVL(100, 10.03, 50.0)


    def test_move_load_script(self, mock_robot, caplog):
        caplog.set_level(logging.DEBUG, logger='roboglia.move.moves')
        caplog.clear()
        script = Script.from_yaml(robot=mock_robot, file_name='tests/moves/script_1.yml')
        assert len(script.joints) == 4
        assert len(script.frames) == 6
        assert len(script.sequences) == 4
        c = list(script.scenes['greet'].play())
        assert len(c) == 28
        assert len(caplog.records) >= 49

    def test_move_execute_script(self, mock_robot, caplog):
        script = Script.from_yaml(robot=mock_robot, file_name='tests/moves/script_1.yml')
        script.start()
        time.sleep(1)
        script.pause()
        time.sleep(0.5)
        script.resume()
        while script.running:
            time.sleep(0.5)
        caplog.set_level(logging.DEBUG)

    def test_move_execute_script_with_stop(self, mock_robot, caplog):
        script = Script.from_yaml(robot=mock_robot, file_name='tests/moves/script_1.yml')
        script.start()
        time.sleep(1)
        script.stop()
        while script.running:
            time.sleep(0.5)

    def test_move_execute_two_scripts(self, mock_robot):
        script1 = Script.from_yaml(robot=mock_robot, file_name='tests/moves/script_1.yml')
        script2 = Script.from_yaml(robot=mock_robot, file_name='tests/moves/script_2.yml')
        script1.start()
        script2.start()
        while script1.running and script2.running:
            time.sleep(0.5)
        time.sleep(0.5)
        assert True

    def test_move_execute_two_scripts_stop_robot(self, mock_robot):
        script1 = Script.from_yaml(robot=mock_robot, file_name='tests/moves/script_1.yml')
        script2 = Script.from_yaml(robot=mock_robot, file_name='tests/moves/script_2.yml')
        script1.start()
        script2.start()
        time.sleep(0.5)
        mock_robot.stop()
        assert True     

    def test_lock_joint_manager(self, mock_robot, caplog):
        script1 = Script.from_yaml(robot=mock_robot, file_name='tests/moves/script_1.yml')
        script1.start()
        manager = mock_robot.manager
        caplog.clear()
        lock = manager._JointManager__lock
        lock.acquire()
        time.sleep(0.5)
        lock.release()        
        assert len(caplog.records) >= 1
        assert 'failed to acquire manager for stream' in caplog.text
        assert 'failed to acquire lock for atomic processing' in caplog.text
