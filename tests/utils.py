from octofarm_companion import Config


def mock_settings_get(accessor):
    if accessor[0] == "octofarm_host":
        return Config.default_octofarm_host
    if accessor[0] == "octofarm_port":
        return Config.default_octofarm_port
    if accessor[0] == "ping":
        return Config.default_ping_secs
    return None


def mock_settings_custom(accessor):
    if accessor[0] == "octofarm_host":
        return "https://farm123asdasdasdasd.net"
    if accessor[0] == "octofarm_port":
        return 443
    if accessor[0] == "ping":
        return 300
    if accessor[0] == "oidc_client_id":
        return "ValidAnnoyer123"
    if accessor[0] == "oidc_client_secret":
        return "ValidPawo321"
    return None


def mock_settings_global_get(accessor):
    if accessor[0] == "server" and accessor[1] == "host":
        return Config.default_octoprint_host
    return None


def mock_settings_get_int(accessor):
    if accessor[0] == "octofarm_port":
        return Config.default_octofarm_port
    if accessor[0] == "ping":
        return Config.default_ping_secs
    return None
