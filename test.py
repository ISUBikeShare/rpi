import unittest
from mock import patch, Mock


class ServerConnectorTestCase(unittest.TestCase):
    def setUp(self):
        self.addCleanup(patch.stopall)

    def test_check_out(self):
        self.assertEqual('asdf', 'asdf')
