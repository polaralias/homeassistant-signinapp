"""Constants for the Sign In App integration."""

DOMAIN = "signinapp"
CONF_COMPANION_CODE = "companion_code"
CONF_REMOTE_SITE_ID = "remote_site_id"
CONF_OFFICE_SITE_ID = "office_site_id"
CONF_DEVICE_TRACKER = "device_tracker"
CONF_OFFICE_DISTANCE = "office_distance"
CONF_CONFIGURED_LOCATIONS = "configured_locations"
CONF_LABEL = "label"
CONF_ENABLED = "enabled"
CONF_SITE_ID = "site_id"
CONF_SITE_TYPE = "site_type"
CONF_COORDINATE_BEHAVIOR = "coordinate_behavior"
CONF_DISTANCE = "distance"

COORDINATE_BEHAVIOR_DEVICE_TRACKER = "device_tracker"
COORDINATE_BEHAVIOR_REMOTE_ZERO = "remote_zero"

DEFAULT_OFFICE_DISTANCE = 50

API_BASE_URL = "https://backend.signinapp.com/api/mobile"

SESSION_STORE_VERSION = 1
SESSION_STORE_KEY = f"{DOMAIN}_sessions"
SESSION_STORE_HASS_KEY = f"{DOMAIN}_session_store"
SESSION_STATE_HASS_KEY = f"{DOMAIN}_session_state"
RUNTIME_STATUS_REASON_KEY = "runtime_status_reason"
DRIFT_ISSUE_ID_PREFIX = f"{DOMAIN}_config_drift"
