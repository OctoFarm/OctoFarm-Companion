import unittest
import unittest.mock as mock
from random import choice
from string import ascii_uppercase

import pytest

from octofarm_companion import OctoFarmCompanionPlugin
from octofarm_companion.constants import Errors, Config, State, Keys


class TestPluginAnnouncing(unittest.TestCase):
    def setUp(self):
        self.settings = mock.MagicMock()  # Replace or refine with set/get
        self.logger = mock.MagicMock()

        self.plugin = OctoFarmCompanionPlugin()
        self.plugin._settings = self.settings
        self.plugin._logger = self.logger
        # Nice way to test persisted data
        self.plugin._data_folder = "test_data"

    def assert_state(self, state):
        assert self.plugin._state is state

    def test_call_mocked_announcement_improperly(self):
        """Call the query announcement, make sure it validates 'access_token'"""

        self.assert_state(State.BOOT)

        with pytest.raises(Exception) as e:
            self.plugin._query_announcement("asd", "asd")

        assert e.value.args[0] == Errors.access_token_too_short
        self.assert_state(State.CRASHED)

    def test_announcement_without_baseurl(self):
        """Call the query announcement, make sure it doesnt crash"""

        fake_token = ''.join(choice(ascii_uppercase) for i in range(Config.access_token_length))
        self.assert_state(State.BOOT)

        with pytest.raises(Exception) as e:
            self.plugin._query_announcement(None, access_token=fake_token)

        assert e.value.args[0] == Errors.base_url_not_provided
        self.assert_state(State.CRASHED)

    # This method will be used by the mock to replace requests.get
    def mocked_requests_get(*args, **kwargs):
        class MockResponse:
            def __init__(self, json_data, status_code, text):
                self.json_data = json_data
                self.status_code = status_code
                self.text = text

            def json(self):
                return self.json_data

        if args[0] == 'http://someurl.com/test.json':
            return MockResponse({"key1": "value1"}, 200, "{}")
        elif args[0] == 'http://someotherurl.com/anothertest.json':
            return MockResponse({"key2": "value2"}, 200, "{}")

        return MockResponse(None, 404, "{}")

    @mock.patch('requests.post', side_effect=mocked_requests_get)
    def test_announcement_with_proper_data(self, mock_post):
        """Call the query announcement properly"""

        fake_token = ''.join(choice(ascii_uppercase) for i in range(Config.access_token_length))
        url = "testwrong_url"
        self.assert_state(State.BOOT)

        # TODO wrong url is not prevented
        self.plugin._query_announcement(url, fake_token)

        # assert e.value.args[0] == Errors.base_url_not_provided
        self.assert_state(State.SLEEP)

    # TODO _check_octofarm
    # TODO _query_access_token
    # TODO test_octofarm_connection
    # TODO test_octofarm_openid
