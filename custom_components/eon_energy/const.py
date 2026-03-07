"""Constants for the E.ON Energy integration."""

DOMAIN = "eon_energy"

# Auth0
AUTH0_DOMAIN = "auth.eonenergy.com"
AUTH0_CLIENT_ID = "S6oUNIPOpdfyjwTqKR5WSDEbu1EbwiDT"
AUTH0_AUDIENCE = "https://api.eon.com/"

# API
API_BASE = "https://api.eon.com/uksol/cm/aem-heat-api/v1"
API_CLIENT_ID = "8a77e5d8b85b46dc9e3dbbc8fb118c51"
API_CLIENT_SECRET = "DCa050cc2C0b44238BF321031C6F4a5E"

# Config entry keys
CONF_EMAIL = "email"
CONF_PASSWORD = "password"
CONF_ACCESS_TOKEN = "access_token"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_TOKEN_EXPIRY = "token_expiry"
CONF_ACCOUNT_NUMBER = "account_number"

PLATFORMS = ["sensor"]

UPDATE_INTERVAL_HOURS = 1
