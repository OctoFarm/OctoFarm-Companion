from octofarm_companion import Config


def mock_settings_get(accessor):
    if accessor[0] == "octofarm_host":
        return Config.default_octofarm_host
    if accessor[0] == "octofarm_port":
        return Config.default_octofarm_port
    if accessor[0] == "ping":
        return Config.default_octofarm_port
    return None


def mock_settings_get_int(accessor):
    if accessor[0] == "octofarm_port":
        return Config.default_octofarm_port
    if accessor[0] == "ping":
        return Config.default_ping_secs
    return None
