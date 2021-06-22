import unittest
import unittest.mock as mock
from octofarm_companion import OctoFarmCompanionPlugin


class TestPluginFeatureOpenIDConnect(unittest.TestCase):
    def setUp(self):
        self.settings = mock.MagicMock()

        self.plugin = OctoFarmCompanionPlugin()
        self.plugin._settings = self.settings

    def test_on_settings_cleanup(self):
        """Tests that after cleanup only minimal config is left in storage."""

        ### setup

        # settings defaults
        defaults = {
            "foo": {"a": 1, "b": 2, "l1": ["some", "list"], "l2": ["another", "list"]},
            "bar": True,
            "fnord": None,
        }
        self.plugin.get_settings_defaults = mock.MagicMock()
        self.plugin.get_settings_defaults.return_value = defaults

        # stored config, containing one redundant entry (bar=True, same as default)
        in_config = {
            "foo": {
                "l1": ["some", "other", "list"],
                "l2": ["another", "list"],
                "l3": ["a", "third", "list"],
            },
            "bar": True,
            "fnord": {"c": 3, "d": 4},
        }
        self.settings.get_all_data.return_value = in_config

        ### execute

        self.plugin.on_settings_cleanup()

        ### assert

        # minimal config (current without redundant value) should have been set
        expected = {
            "foo": {"l1": ["some", "other", "list"], "l3": ["a", "third", "list"]},
            "fnord": {"c": 3, "d": 4},
        }
        self.settings.set.assert_called_once_with([], expected)
