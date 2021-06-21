# OctoFarm-Companion

This plugin is your friend when using OctoFarm with one or more OctoPrint instances. The plugin is intended to simplify
the initial connection with OctoFarm. Next to that some more functionality will be built in future.

Current feature(s):
- Auto-registration - send your OctoPrint connection parameters to OctoFarm safely, to make setting up printers a breeze.

Future features:
- Filament Pedometer - send filament usage data to OctoFarm, making the filament manager plugin and its PostGres database unnecessary.
- Http Tunnel - connect to OctoFarm, to make connection to printers a breeze especially over docker, VPN, DMZ, VLAN, the cloud or other complex network setups.
- Single-sign-On - client-to-machine (C2M) and machine-to-machine (M2M) authentication removing the need for more than 1 set of credentials across the farm.

For more feature requests, bugs, or ideas please head over to https://github.com/OctoFarm/OctoFarm/discussions.

## Setup
**!! Work in progress !!**

Install via the bundled [Plugin Manager](https://docs.octoprint.org/en/master/bundledplugins/pluginmanager.html)
or manually using this URL:

    https://github.com/OctoFarm/OctoFarm-Companion/archive/master.zip

Please configure the plugin completely for one or more printers before checking OctoFarm.

## Configuration
**Warning - restoring from a OctoPrint backup can be cause of security weakness due to copied passwords. In the end we are not responsible for your choices, but we advise to change the `accessControl:salt` and to regenerate the main user account for each OctoPrint instance.**

### Configuration - auto-registration
Configuring the auto-registration properly can massively improve the steps you need to undertake to setup your farm.
- `octofarmHost` the host to reach OctoFarm with (IP, localhost, domain name, etc)
- `octofarmPort` the port to approach the OctoFarm server (number)

We understand if you restore OctoPrint backups to install new OctoPrints. For that reason we've introduced two unique ID's (UUID).
- `persistenceUuid` a unique identifier stored in the plugin folder in `device.json`, which is excluded from backups to prevent duplicate printers.
- `deviceUuid` a unique identifier stored in the `config.yaml` at startup.

Periodic updates
- `ping` the time in seconds between each call to OctoFarm (default is 15 * 60, or 15 minutes)

The plugin will use `server:host` and `server:port` to give OctoFarm a handle to connect back to this OctoPrint. This is often incorrect, if your OctoPrint is behind a proxy, in a VM, UnRaid, a different device, DMZ, in a docker container or in a VPN.
At this moment this needs to be rectified in OctoFarm. Later we will allow more advanced ways to fix this, but for now we believe this plugin is going to make it much easier already.
