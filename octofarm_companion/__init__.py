# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import flask
import io
import json
import os
import uuid
from datetime import datetime
from urllib.parse import urljoin

import octoprint.plugin
import requests
from octoprint.util import RepeatedTimer

from octoprint.server import NO_CONTENT
from octoprint.server.util.flask import (
    no_firstrun_access
)


def is_docker():
    path = '/proc/self/cgroup'
    return (
            os.path.exists('/.dockerenv') or
            os.path.isfile(path) and any('docker' in line for line in open(path))
    )


octofarm_announce_route = 'octoprint/announce'
octofarm_access_token_route = 'oidc/token'
octofarm_version_route = 'serverChecks/version'
requested_scopes = 'openid'


class OctoFarmCompanionPlugin(
    octoprint.plugin.StartupPlugin,
    octoprint.plugin.TemplatePlugin,
    octoprint.plugin.ShutdownPlugin,
    octoprint.plugin.BlueprintPlugin,
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.AssetPlugin,
):
    def __init__(self):
        self._ping_worker = None
        # device UUID and OIDC opaque access_token + metadata
        self._persisted_data = dict()
        self._excluded_persistence_data = "backup_excluded_data.json"
        self._excluded_persistence_datapath = None
        self._state = "boot"

    def on_after_startup(self):
        if self._settings.get(["octofarm_host"]) is None:
            self._settings.set(["octofarm_host"], "http://127.0.0.1")
        if self._settings.get(["octofarm_port"]) is None:
            self._settings.set(["octofarm_port"], 4000)
        self._get_device_uuid()
        self._start_periodic_check()

    def get_excluded_persistence_datapath(self):
        self._excluded_persistence_datapath = os.path.join(self.get_plugin_data_folder(),
                                                           self._excluded_persistence_data)
        return self._excluded_persistence_datapath

    def get_template_vars(self):
        octofarm_host = self._settings.get(["octofarm_host"])
        octofarm_port = self._settings.get(["octofarm_port"])
        base_url = f"{octofarm_host}:{octofarm_port}"
        favicon = f"{base_url}/favicon.ico"
        return dict(url=base_url, of_favicon=favicon)

    def get_template_configs(self):
        return [
            dict(type="settings", custom_bindings=False),
            dict(type="navbar", custom_bindings=False)
        ]

    # TODO make http://https:// slash robust
    def get_settings_defaults(self):
        return {
            "octofarm_host": None,  # Without adjustment this config value is OFTEN useless
            "octofarm_port": None,  # Without adjustment this config value is OFTEN useless
            "port_override": None,  # Without adjustment this config value is SOMETIMES useless
            "device_uuid": None,  # Auto-generated and unique
            "oidc_client_id": None,  # Without adjustment this config value is ALWAYS useless
            "oidc_client_secret": None,  # Without adjustment this config value is ALWAYS useless
            "ping": 120
        }

    def get_settings_version(self):
        return 1

    def get_assets(self):
        # Define your plugin's asset files to automatically include in the
        # core UI here.
        return dict(
            js=["js/octofarm_companion.js"],
            css=["css/octofarm_companion.css"],
            less=["less/octofarm_companion.less"]
        )

    def initialize(self):
        self._fetch_persisted_data()

    def _fetch_persisted_data(self):
        filepath = self.get_excluded_persistence_datapath()
        if os.path.exists(filepath):
            try:
                with io.open(filepath, "r", encoding="utf-8") as f:
                    persistence_file = f.read()
                    persistence_json = json.loads(persistence_file)
                    self._persisted_data = persistence_json
            except json.decoder.JSONDecodeError as e:
                self._logger.warning(
                    "OctoFarm persisted device Id file was of invalid format.")
                self._write_new_device_uuid(filepath)
        else:
            self._write_new_device_uuid(filepath)

    def _write_new_access_token(self, filepath, at_data):
        self._persisted_data["access_token"] = at_data["access_token"]
        self._persisted_data["expires_in"] = at_data["expires_in"]
        self._persisted_data["requested_at"] = int(datetime.utcnow().timestamp())
        self._persisted_data["token_type"] = at_data["token_type"]
        self._persisted_data["scope"] = at_data["scope"]
        self._write_persisted_data(filepath)
        self._logger.info("OctoFarm persisted data file was updated (access_token)")

    def _write_new_device_uuid(self, filepath):
        persistence_uuid = str(uuid.uuid4())
        self._persisted_data['persistence_uuid'] = persistence_uuid
        self._write_persisted_data(filepath)
        self._logger.info("OctoFarm persisted data file was updated (device_uuid).")

    def _write_persisted_data(self, filepath):
        with io.open(filepath, "w", encoding="utf-8") as f:
            f.write(json.dumps(self._persisted_data))

    def _get_device_uuid(self):
        device_uuid = self._settings.get(["device_uuid"])
        if device_uuid is None:
            device_uuid = str(uuid.uuid4())
            self._settings.set(["device_uuid"], device_uuid)
            self._settings.save()
        return device_uuid

    def get_update_information(self):
        # Define the configuration for your plugin to use with the Software Update
        # Plugin here. See https://docs.octoprint.org/en/master/bundledplugins/softwareupdate.html
        # for details.
        return dict(
            octofarm_companion=dict(
                displayName="Octofarm-Companion Plugin",
                displayVersion=self._plugin_version,

                # version check: github repository
                type="github_release",
                user="octofarm",
                repo="OctoFarm-Companion",
                current=self._plugin_version,

                # update method: pip
                pip="https://github.com/octofarm/OctoFarm-Companion/archive/{target_version}.zip"
            )
        )

    def _start_periodic_check(self):
        if self._ping_worker is None:
            ping_interval = self._settings.get_int(["ping"])
            if ping_interval:
                self._ping_worker = RepeatedTimer(
                    ping_interval, self._check_octofarm, run_first=True
                )
                self._ping_worker.start()

    def _check_octofarm(self):
        octofarm_host = self._settings.get(["octofarm_host"])
        octofarm_port = self._settings.get(["octofarm_port"])

        if octofarm_host is not None and octofarm_port is not None:
            base_url = f"{octofarm_host}:{octofarm_port}"

            # OIDC client_credentials flow result
            access_token = self._persisted_data.get('access_token', None)
            requested_at = self._persisted_data.get('requested_at', None)
            expires = self._persisted_data.get('expires', None)

            # Token expiry check - prone to time desync
            is_expired = None
            if requested_at is not None and expires is not None:
                current_time = datetime.utcnow().timestamp()
                is_expired = current_time > requested_at + expires

            token_invalid = not access_token or is_expired

            if token_invalid:
                oidc_client_id = self._settings.get(["oidc_client_id"])
                oidc_client_secret = self._settings.get(["oidc_client_secret"])
                success = self._query_access_token(base_url, oidc_client_id, oidc_client_secret)
                if not success:
                    return False
            else:
                self._state = "success"

            at = self._persisted_data["access_token"]
            if at is None:
                raise Exception(
                    "Conditional error: 'access_token' was not saved properly. Please report a bug to the plugin developers. Aborting")

            self._query_announcement(base_url, at)

        else:
            raise Exception("Configuration error: 'oidc_client_id' or 'oidc_client_secret' not set")
            self._logger.error("Error connecting to OctoFarm")

    def _query_access_token(self, base_url, oidc_client_id, oidc_client_secret):
        if not oidc_client_id or not oidc_client_secret:
            self._logger.error("Configuration error: 'oidc_client_id' or 'oidc_client_secret' not set")
            self._state = "crash"
            return False

        at_data = None
        try:
            data = {'grant_type': 'client_credentials', 'scope': requested_scopes}
            self._logger.info("Calling OctoFarm at URL: " + base_url)
            url = urljoin(base_url, octofarm_access_token_route)
            response = requests.post(url, data=data,
                                     verify=False, allow_redirects=False, auth=(oidc_client_id, oidc_client_secret))
            self._logger.info(response.text)
            self._logger.info(response.status_code)
            at_data = json.loads(response.text)
        except requests.exceptions.ConnectionError:
            self._state = "retry"  # TODO apply this with a backoff scheme
            self._logger.error("ConnectionError: error sending access_token request to OctoFarm")
        except Exception as e:
            self._state = "crash"
            self._logger.error(
                "Generic Exception: error requesting access_token request to OctoFarm. Exception: " + str(e))

        if at_data is not None:
            if at_data["access_token"] is None:
                raise Exception(
                    "Response error: 'access_token' not received. Check your OctoFarm server logs. Aborting")
            if at_data["expires_in"] is None:
                raise Exception("Response error: 'expires_in' not received. Check your OctoFarm server logs. Aborting")

            # Saves to file and to this plugin instance self._persistence_data accordingly
            self._write_new_access_token(self.get_excluded_persistence_datapath(), at_data)
            self._state = "success"
            return True
        else:
            self._state = "crash"
            self._logger.error("Response error: access_token data response was empty. Aborting")

    def _query_announcement(self, base_url, access_token):
        if self._state is not "success" and self._state is not "sleep":
            self._logger.error("State error: tried to announce when state was not 'success'")

        if base_url is None:
            self._state = "crash"
            raise Exception(
                "The 'base_url' was not provided. Preventing announcement query to OctoFarm")

        if len(access_token) < 43:
            self._state = "crash"
            raise Exception(
                "The 'access_token' did not meet the expected length of 43 characters. Preventing announcement query to OctoFarm")

        # Announced data
        octoprint_port = self._settings.get(["port_override"])
        octoprint_host = self._settings.global_get(["server", "host"])
        # TODO maybe let OctoFarm decide instead of swapping ourselves?
        if octoprint_port is None:
            # Risk of failure when behind proxy (docker, vm, vpn, rev-proxy)
            octoprint_port = self._settings.global_get(["server", "port"])

        try:
            # Data folder based
            self._fetch_persisted_data()
            # Config file based
            device_uuid = self._get_device_uuid()

            # TODO rectify CORS on the spot?
            allow_cross_origin = self._settings.global_get(["api", "allowCrossOrigin"])

            check_data = {
                "deviceUuid": device_uuid,
                "persistenceUuid": self._persisted_data["persistence_uuid"],
                "host": octoprint_host,
                "port": int(octoprint_port),
                "docker": bool(is_docker()),
                "allowCrossOrigin": bool(allow_cross_origin)
            }

            headers = {'Authorization': 'Bearer ' + access_token}
            url = urljoin(base_url, octofarm_announce_route)
            response = requests.post(url, headers=headers, json=check_data)

            self._state = "sleep"
            self._logger.info(f"Done announcing to OctoFarm server ({response.status_code})")
            self._logger.info(response.text)
        except requests.exceptions.ConnectionError:
            self._state = "crash"
            self._logger.error("ConnectionError: error sending announcement to OctoFarm")

    def additional_excludes_hook(self, excludes, *args, **kwargs):
        return [self._excluded_persistence_data]

    @octoprint.plugin.BlueprintPlugin.route("/test_octofarm_connection", methods=["POST"])
    @no_firstrun_access
    def test_octofarm_connection(self):
        input = json.loads(flask.request.data)
        if "url" not in input:
            flask.abort(400, description="Expected 'url' parameter")

        proposed_url = input["url"]
        self._logger.info("Testing OctoFarm URL " + proposed_url)

        url = urljoin(proposed_url, octofarm_version_route)
        response = requests.get(url)
        version_data = json.loads(response.text)

        self._logger.info("Version response from OctoFarm " + version_data["version"])

        return version_data

    @octoprint.plugin.BlueprintPlugin.route("/test_octofarm_openid", methods=["POST"])
    @no_firstrun_access
    def test_octofarm_openid(self):
        input = json.loads(flask.request.data)
        if not "url" in input:
            flask.abort(400, description="Expected 'url' parameter")
        if not "client_id" in input:
            flask.abort(400, description="Expected 'client_id' parameter")
        if not "client_secret" in input:
            flask.abort(400, description="Expected 'client_secret' parameter")

        proposed_url = input["url"]
        oidc_client_id = input["client_id"]
        oidc_client_secret = input["client_secret"]
        self._query_access_token(proposed_url, oidc_client_id, oidc_client_secret)

        self._logger.info("Queried access_token from Octofarm")

        return {
            "state": self._state,
        }


__plugin_name__ = "OctoFarm Companion"
__plugin_version__ = "0.1.0-rc1-build2"
__plugin_description__ = "The OctoFarm companion plugin for OctoPrint"
__plugin_pythoncompat__ = ">=3,<4"


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = OctoFarmCompanionPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
        "octoprint.plugin.backup.additional_excludes": __plugin_implementation__.additional_excludes_hook
    }
