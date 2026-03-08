"""Constants for the E.ON Energy integration."""

DOMAIN = "eon_energy"

# API
API_BASE = "https://api.eon.com/uksol/cm/aem-heat-api/v1"
API_CLIENT_ID = "8a77e5d8b85b46dc9e3dbbc8fb118c51"
API_CLIENT_SECRET = "DCa050cc2C0b44238BF321031C6F4a5E"

# Config entry data keys (authentication + cached consumption)
CONF_BEARER_TOKEN = "bearer_token"       # id_token used as Bearer
CONF_TOKEN_EXPIRY = "token_expiry"       # absolute Unix timestamp
CONF_ACCOUNT_NUMBER = "account_number"
CONF_STORED_CONSUMPTION = "stored_consumption"  # last successful fetch, persisted as dict

# Options keys (user-configurable)
CONF_FETCH_DAY = "fetch_day"             # day-of-month on which to call the API (1–28)
DEFAULT_FETCH_DAY = 10                   # sensible default: mid-month, after billing closes

PLATFORMS = ["sensor"]
