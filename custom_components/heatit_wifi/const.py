"""Constants for the Heatit WiFi integration."""
from typing import Final

DOMAIN: Final = "heatit_wifi"

# Status polling interval in minutes.
POLL_INTERVAL: Final = 1

# Default polling interval in seconds (overridable via the options flow).
DEFAULT_SCAN_INTERVAL: Final = POLL_INTERVAL * 60

# The firmware reports exactly 100.0 for a disconnected or shorted
# floor/external NTC sensor; treat that reading as "no sensor".
NTC_FAULT_TEMPERATURE: Final = 100.0

# API endpoints.
API_STATUS: Final = "/api/status"
API_PARAMETERS: Final = "/api/parameters"
API_RESET: Final = "/api/reset"

SENSORMODES: Final[dict[int, str]] = {
    0: "0: Floor sensor (F)",
    1: "1: Internal sensor (A)",  # Default sensor mode
    2: "2: Internal sensor & floor sensor limitation (AF)",
    3: "3: External sensor (A2)",
    4: "4: External sensor & floor sensor limitation (A2F)",
    5: "5: Power regulator mode (PWER)",
}

SENSORVALUES: Final[dict[int, str]] = {
    0: "0: 10kΩ NTC",  # Default sensor value
    1: "1: 12kΩ NTC",
    2: "2: 15kΩ NTC",
    3: "3: 22kΩ NTC",
    4: "4: 33kΩ NTC",
    5: "5: 47kΩ NTC",
    6: "6: 6.8kΩ NTC",
    7: "7: 100kΩ NTC",
}
