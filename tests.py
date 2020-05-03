import unittest
import sys
import logging
import yaml

logging.basicConfig(level=60)       # silent

from roboglia.base import BaseRobot
from roboglia.dynamixel import DynamixelDevice

class TestRobot(unittest.TestCase):

    def setUp(self):
        self.robot = yaml.load("""
            buses:
                - name: busA
                  class: FileBus
                  port: /tmp/busA.log

            devices:
                - name: d01
                  class: DynamixelDevice
                  bus: busA
                  id: 1
                  model: AX-12A
        """, Loader=yaml.FullLoader)

    def test_mock_robot(self):
        _ = BaseRobot(self.robot)



if __name__ == '__main__':
    suite = unittest.TestSuite()
    suite.addTest(TestRobot('test_mock_robot'))
    runner = unittest.TextTestRunner(stream=sys.stdout, verbosity=2)
    runner.run(suite)
