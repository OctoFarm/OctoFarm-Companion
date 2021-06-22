class Errors:
    access_token_too_short = "The 'access_token' did not meet the expected length of 43 characters. Preventing "
    "announcement query to OctoFarm"
    base_url_not_provided = "The 'base_url' was not provided. Preventing announcement query to OctoFarm"


class Config:
    access_token_length = 43

