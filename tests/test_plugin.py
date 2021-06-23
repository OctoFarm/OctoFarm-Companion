import unittest

from octofarm_companion import __plugin_load__


class TestPlugin(unittest.TestCase):
    def test_load(self):
        __plugin_load__()
