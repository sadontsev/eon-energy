"""Constants for the E.ON Energy integration."""

DOMAIN = "eon_energy"

# API
API_BASE = "https://api.eon.com/uksol/cm/aem-heat-api/v1"
API_CLIENT_ID = "8a77e5d8b85b46dc9e3dbbc8fb118c51"
API_CLIENT_SECRET = "DCa050cc2C0b44238BF321031C6F4a5E"

# Config entry keys
CONF_BEARER_TOKEN = "bearer_token"   # id_token used as Bearer
CONF_TOKEN_EXPIRY = "token_expiry"   # absolute Unix timestamp
CONF_ACCOUNT_NUMBER = "account_number"

PLATFORMS = ["sensor"]

UPDATE_INTERVAL_HOURS = 1
