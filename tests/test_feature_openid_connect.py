import unittest
import unittest.mock as mock
from random import choice
from string import ascii_uppercase

import pytest

from octofarm_companion import OctoFarmCompanionPlugin
from octofarm_companion.constants import Errors, Config


class TestPluginFeatureOpenIDConnect(unittest.TestCase):
    def setUp(self):
        self.settings = mock.MagicMock()
        self.logger = mock.MagicMock()

        self.plugin = OctoFarmCompanionPlugin()
        self.plugin._settings = self.settings
        self.plugin._logger = self.logger

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

    def assert_state(self, state):
        assert self.plugin._state == state

    def test_call_mocked_announcement_improperly(self):
        """Call the query announcement, make sure it validates 'access_token'"""

        with pytest.raises(Exception) as e:
            self.plugin._query_announcement("asd", "asd")

        assert e.value.args[0] == Errors.access_token_too_short

    def test_call_mocked_announcement_improperly(self):
        """Call the query announcement, make sure it doesnt crash"""

        fake_token = ''.join(choice(ascii_uppercase) for i in range(Config.access_token_length))
        with pytest.raises(Exception) as e:
            self.plugin._query_announcement(None, access_token=fake_token)

        assert e.value.args[0] == Errors.base_url_not_provided
        self.assert_state("crash")

    # TODO assert __init__
    # TODO __plugin_load__ and version
    # TODO get_update_information
    # TODO get_excluded_persistence_datapath path
    # TODO get_template_vars
    # TODO get_settings_defaults
    # TODO data/config mocked initialize
    # TODO _fetch_persisted_data
    # TODO _write_new_access_token
    # TODO _write_new_device_uuid
    # TODO _write_persisted_data
    # TODO _get_device_uuid
    # TODO _check_octofarm
    # TODO _query_access_token
    # TODO additional_excludes_hook
    # TODO test_octofarm_connection
    # TODO test_octofarm_openid
    # Optional
    # TODO _start_periodic_check
