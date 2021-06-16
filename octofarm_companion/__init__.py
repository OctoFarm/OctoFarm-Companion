# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import io
import json
import os
import uuid
from datetime import datetime

import octoprint.plugin
import requests
from octoprint.util import RepeatedTimer


def is_docker():
    path = '/proc/self/cgroup'
    return (
            os.path.exists('/.dockerenv') or
            os.path.isfile(path) and any('docker' in line for line in open(path))
    )


octofarm_announce_route = 'plugins/announce'
octofarm_access_token_route = 'oidc/token'
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
        defaults = self.get_settings_defaults()
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

    def get_template_configs(self):
        return [
            dict(type="settings", custom_bindings=False),
            dict(type="navbar", custom_bindings=False)
        ]

    # TODO make http://https:// slash robust
    def get_settings_defaults(self):
        return {
            "octofarm_host": None, # Without adjustment this config value is OFTEN useless
            "octofarm_port": None, # Without adjustment this config value is OFTEN useless
            "port_override": None, # Without adjustment this config value is SOMETIMES useless
            "device_uuid": None, # Auto-generated and unique
            "oidc_client_id": None, # Without adjustment this config value is ALWAYS useless
            "oidc_client_secret": None, # Without adjustment this config value is ALWAYS useless
            "ping": 30
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
        self._persisted_data['access_token'] = at_data.access_token
        self._persisted_data['expires_in'] = at_data.expires_in
        self._persisted_data['requested_at'] = int(datetime.utcnow().timestamp())
        self._persisted_data['token_type'] = at_data.token_type
        self._persisted_data['scope'] = at_data.scope
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

        # Announced data
        port = self._settings.get(["port_override"])
        host = self._settings.global_get(["server", "host"])
        # TODO maybe let OctoFarm decide instead of swapping ourselves?
        if port is None:
            # Risk of failure when behind proxy (docker, vm, vpn, rev-proxy)
            port = self._settings.global_get(["server", "port"])

        # TODO rectify CORS on the spot?
        allow_cross_origin = self._settings.global_get(["api", "allowCrossOrigin"])

        if octofarm_host is not None and octofarm_port is not None:
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
                success = self._query_access_token(octofarm_host, octofarm_port)
                if not success:
                    return False

            at = self._persistence_data.access_token
            if at is None:
                raise Exception(
                    "Conditional error: 'access_token' was not saved properly. Please report a bug to the plugin developers. Aborting")

            self._query_announcement(octofarm_host, octofarm_port, access_token)

        else:
            raise Exception("Configuration error: 'oidc_client_id' or 'oidc_client_secret' not set")
            self._logger.error("Error connecting to OctoFarm")

    def _query_access_token(self, host, port):
        oidc_client_id = self._settings.get(["oidc_client_id"])
        oidc_client_secret = self._settings.get(["oidc_client_secret"])

        if not oidc_client_id or not oidc_client_secret:
            self._logger.error("Configuration error: 'oidc_client_id' or 'oidc_client_secret' not set")
            self._state = "crash"
            return False
        try:
            data = {'grant_type': 'client_credentials', 'scope': requested_scopes}
            response = requests.post(f"{octofarm_host}:{octofarm_port}/{octofarm_access_token_route}", data=check_data,
                                     verify=False, allow_redirects=False, auth=(client_id, client_secret))

            at_data = json.loads(access_token_response.text)
        except requests.exceptions.ConnectionError:
            self._state = "retry"  # TODO apply this with a backoff scheme
            self._logger.error("ConnectionError: error sending access_token request to OctoFarm")
        except Exception as e:
            self._state = "crash"
            self._logger.error("ConnectionError: error parsing response when sending access_token request to OctoFarm")

        if at_data is not None:
            if at_data.access_token is None:
                raise Exception(
                    "Response error: 'access_token' not received. Check your OctoFarm server logs. Aborting")
            if at_data.expires_in is None:
                raise Exception("Response error: 'expires_in' not received. Check your OctoFarm server logs. Aborting")

            # Saves to file and to this plugin instance self._persistence_data accordingly
            self._write_new_access_token(self._data_path, at_data)
            self._state = "success"
            return True
        else:
            self._state = "crash"
            self._logger.error("Response error: access_token data response was empty. Aborting")

    def _query_announcement(self, host, port, access_token):
        if self._state is not "success" and self._state is not "sleep":
            self._logger.error("State error: tried to announce when state was not 'success'")

        if host is None:
            self._state = "crash"
            raise Exception(
                "The 'host' was not provided. Preventing announcement query to OctoFarm")
        if port is None or isnumeric(port):
            self._state = "crash"
            raise Exception(
                "The 'port' was not provided or was not a number. Preventing announcement query to OctoFarm")
        if len(access_token) < 43:
            self._state = "crash"
            raise Exception(
                "The 'access_token' did not meet the expected length of 43 characters. Preventing announcement query to OctoFarm")

        try:
            # Data folder based
            persisted_data = self._fetch_persisted_data()
            # Config file based
            device_uuid = self._get_device_uuid()

            check_data = {
                "deviceUuid": device_uuid,
                "persistenceUuid": persisted_data.persistence_uuid,
                "host": host,
                "port": int(port),
                "docker": bool(is_docker()),
                "allowCrossOrigin": bool(allow_cross_origin)
            }

            headers = {'Authorization': 'Bearer ' + access_token}
            response = requests.get(f"{octofarm_host}:{octofarm_port}/{octofarm_announce_route}", headers=headers,
                                    json=check_data)

            self._state = "sleep"
            self._logger.debug("Done announcing to OctoFarm server")
        except requests.exceptions.ConnectionError:
            self._state = "crash"
            self._logger.error("ConnectionError: error sending announcement to OctoFarm")

    def additional_excludes_hook(self, excludes, *args, **kwargs):
        return [self._excluded_persistence_data]


__plugin_name__ = "OctoFarm Companion"
__plugin_version__ = "0.1.14"
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
