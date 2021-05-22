# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import io
import json
import os
import uuid

import octoprint.plugin
import requests
from octoprint.util import RepeatedTimer


class OctoFarmCompanionPlugin(
	octoprint.plugin.StartupPlugin,
	octoprint.plugin.ShutdownPlugin,
	octoprint.plugin.BlueprintPlugin,
	octoprint.plugin.SettingsPlugin,
	octoprint.plugin.OctoPrintPlugin,
	octoprint.plugin.AssetPlugin,
	octoprint.plugin.TemplatePlugin
):
	def __init__(self):
		self._ping_worker = None
		self._excluded_file = "device.json"

	def on_after_startup(self):
		self._start_periodic_check()

	def get_settings_defaults(self):
		return {
			"publicHost": "http://localhost",
			"publicPort": 4000,
			"ping": 15
		}

	def get_assets(self):
		# Define your plugin's asset files to automatically include in the
		# core UI here.
		return dict(
			js=["js/octofarm_companion.js"],
			css=["css/octofarm_companion.css"],
			less=["less/octofarm_companion.less"]
		)

	def initialize(self):
		self._get_persistence_uuid()

	def _get_persistence_uuid(self):
		filepath = os.path.join(self.get_plugin_data_folder(), self._excluded_file)

		if os.path.exists(filepath):
			try:
				with io.open(filepath, "r", encoding="utf-8") as f:
					device_uuid_file = f.read()
					device_uuid_json = json.loads(device_uuid_file)
					return device_uuid_json["device_uuid"]
			except json.decoder.JSONDecodeError as e:
				self._logger.warning("OctoFarm persisted device Id file was of invalid format.")
				return self._write_new_device_uuid(filepath)
		else:
			return self._write_new_device_uuid(filepath)

	def _write_new_device_uuid(self, filepath):
		persistedDeviceUuid = str(uuid.uuid4())
		json_data = {'device_uuid': persistedDeviceUuid}

		with io.open(filepath, "w", encoding="utf-8") as f:
			f.write(json.dumps(json_data))

		self._logger.info("OctoFarm persisted device Id file was stored.")

		return persistedDeviceUuid

	def _get_uuid(self):
		deviceUuid = self._settings.get(["deviceUuid"])
		if deviceUuid is None:
			deviceUuid = str(uuid.uuid4())
			self._settings.set(["deviceUuid"], deviceUuid)
			self._settings.save()
		return deviceUuid

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
		octofarm_host = self._settings.get(["publicHost"])
		octofarm_port = self._settings.get(["publicPort"])

		if octofarm_host is not None and octofarm_port is not None:
			persisted_device_uuid = self._get_persistence_uuid()
			deviceUuid = self._get_uuid()

			check_data = {"deviceUuid": deviceUuid,
						  "persistenceUuid": persisted_device_uuid}
			self._logger.info("Checking OctoFarm server")

			response = requests.get(f"{octofarm_host}:{octofarm_port}/plugins/check", data=check_data)
			self._logger.info(response.text)

			self._logger.info("Done checking OctoFarm server")

	def additional_excludes_hook(self, excludes, *args, **kwargs):
		return [self._excluded_file]


__plugin_name__ = "OctoFarm Companion"
__plugin_version__ = "0.1.14"
__plugin_description__ = "The \"OctoFarm\" companion plugin for OctoPrint"
__plugin_pythoncompat__ = ">=3,<4"


def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = OctoFarmCompanionPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
		"octoprint.plugin.backup.additional_excludes": __plugin_implementation__.additional_excludes_hook
	}
