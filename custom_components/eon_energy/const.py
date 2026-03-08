"""Constants for the E.ON Energy integration."""

DOMAIN = "eon_energy"

# API
API_BASE = "https://api.eon.com/uksol/cm/aem-heat-api/v1"
API_CLIENT_ID = "8a77e5d8b85b46dc9e3dbbc8fb118c51"
API_CLIENT_SECRET = "DCa050cc2C0b44238BF321031C6F4a5E"

# Config entry data keys
CONF_BEARER_TOKEN = "bearer_token"
CONF_TOKEN_EXPIRY = "token_expiry"
CONF_ACCOUNT_NUMBER = "account_number"
CONF_STORED_CONSUMPTION = "stored_consumption"

# Options keys
CONF_FETCH_DAY = "fetch_day"
DEFAULT_FETCH_DAY = 10

PLATFORMS = ["sensor"]
