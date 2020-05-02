import unittest

from test_utils import test_utils_suite
from test_base import test_base_suite

global_message = ''

class d(unittest.TestCase):
    def divider(self):
        print()
        print('*'*80)

suite = unittest.TestSuite()
suite.addTest(d('divider'))
suite.addTest(test_utils_suite())
suite.addTest(d('divider'))
suite.addTest(test_base_suite())
suite.addTest(d('divider'))

if __name__ == '__main__':
    runner = unittest.TextTestRunner(verbosity=2)
