import json
import unittest
import unittest.mock as mock

from octofarm_companion import OctoFarmCompanionPlugin


class TestPluginConnection(unittest.TestCase):
    @classmethod
    def setUp(cls):
        cls.settings = mock.MagicMock()  # Replace or refine with set/get
        cls.logger = mock.MagicMock()

        cls.plugin = OctoFarmCompanionPlugin()
        cls.plugin._settings = cls.settings
        cls.plugin._logger = cls.logger
        cls.plugin._ping_worker = dict() # disable it

    # This method will be used by the mock to replace requests.get
    def mocked_requests_get(*args, **kwargs):
        class MockResponse:
            def __init__(self, json_data, status_code, text):
                self.json_data = json_data
                self.status_code = status_code
                self.text = text

            def json(self):
                return self.json_data

        return MockResponse({"version": "test-version"}, 200, json.dumps({"version": "test-version"}))

    @mock.patch('requests.get', side_effect=mocked_requests_get)
    def test_octofarm_connection_test(self, mocked_requests_get):
        """Call the OctoFarm connection test properly"""

        m = mock.MagicMock()
        m.data = json.dumps({"url": "http://127.0.0.1"})

        with mock.patch("octofarm_companion.request", m):
            # somefile.method_called_from_route()
            response = self.plugin.test_octofarm_connection()
            assert response["version"] == "test-version"

    # TODO test_octofarm_connection
    # TODO test_octofarm_openid
