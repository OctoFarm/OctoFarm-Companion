class Errors:
    access_token_too_short = "The 'access_token' did not meet the expected length of 43 characters. Preventing "
    "announcement query to OctoFarm"
    access_token_not_saved = "Conditional error: 'access_token' was not saved properly. Please report a bug to the " \
                             "plugin developers. Aborting "
    base_url_not_provided = "The 'base_url' was not provided. Preventing announcement query to OctoFarm"


class Keys:
    persistence_uuid_key = "persistence_uuid"
    device_uuid_key = "device_uuid"


class Config:
    access_token_length = 43
    persisted_data_file = "backup_excluded_data.json"


class State:
    BOOT = "boot"
    SUCCESS = "success"
    SLEEP = "sleep"
    CRASHED = "crashed"
    RETRY = "retry"
