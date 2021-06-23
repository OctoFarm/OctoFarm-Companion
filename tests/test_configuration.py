import unittest
import unittest.mock as mock

from octoprint.util import RepeatedTimer

from octofarm_companion import OctoFarmCompanionPlugin
from octofarm_companion.constants import Config, Keys


class TestPluginConfiguration(unittest.TestCase):
    @classmethod
    @mock.patch('octofarm_companion.RepeatedTimer')
    def setUp(cls, mock_repeated_timer):
        cls.settings = mock.MagicMock()  # Replace or refine with set/get
        cls.logger = mock.MagicMock()

        cls.mock_repeated_timer = mock_repeated_timer
        cls.mock_repeated_timer .start = lambda *args: None

        cls.plugin = OctoFarmCompanionPlugin()
        cls.plugin._settings = cls.settings
        cls.plugin._logger = cls.logger
        # Nice way to test persisted data
        cls.plugin._data_folder = "test_data"

    def test_persisted_data(self):
        # State has already been set
        device_uuid = self.plugin._get_device_uuid()
        data_path = self.plugin.get_excluded_persistence_datapath()
        self.plugin._fetch_persisted_data()
        persistence_uuid = self.plugin._persisted_data[Keys.persistence_uuid_key]

        assert device_uuid is not None
        # MagicMock is returned - not useful yet
        # assert len(device_uuid) > 15
        assert ".json" in Config.persisted_data_file
        assert Config.persisted_data_file in data_path and "test_data" in data_path
        assert len(persistence_uuid) > 20

    def test_startup_without_ping(self):
        self.plugin._ping_worker = self.mock_repeated_timer
        self.plugin.on_after_startup()

        self.logger.error.assert_called_with("'ping' config value not set. Aborting")

    def test_on_settings_cleanup(self):
        """Tests that after cleanup only minimal config is left in storage."""
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

        # execute

        self.plugin.on_settings_cleanup()

        # assert

        # minimal config (current without redundant value) should have been set
        expected = {
            "foo": {"l1": ["some", "other", "list"], "l3": ["a", "third", "list"]},
            "fnord": {"c": 3, "d": 4},
        }
        self.settings.set.assert_called_once_with([], expected)

    def test_settings_default(self):
        defaults = self.plugin.get_settings_defaults()
        assert defaults["octofarm_host"] is None
        assert defaults["octofarm_port"] is None
        assert defaults["oidc_client_id"] is None
        assert defaults["oidc_client_secret"] is None
        assert defaults["ping"] == 120

    def test_template_vars(self):
        template_vars_dict = self.plugin.get_template_vars()
        assert "url" in template_vars_dict.keys()
        assert "of_favicon" in template_vars_dict.keys()

    def test_template_configs(self):
        template_config = self.plugin.get_template_configs()

        assert any(config["type"] == "settings" for config in template_config)
        assert any(config["type"] == "navbar" for config in template_config)

    def assert_state(self, state):
        assert self.plugin._state is state

    # TODO assert __init__
    # TODO __plugin_load__ and version
    # TODO get_update_information
    # TODO get_excluded_persistence_datapath path
    # TODO get_settings_defaults
    # TODO data/config mocked initialize
    # TODO _fetch_persisted_data
    # TODO _write_new_access_token
    # TODO _write_new_device_uuid
    # TODO _write_persisted_data
    # TODO get_template_vars
    # TODO _get_device_uuid
    # TODO additional_excludes_hook

    # Optional
    # TODO _start_periodic_check
