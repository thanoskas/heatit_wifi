DOMAIN = "heatit_wifi6_custom"

# status polling interval in minutes.
POLL_INTERVAL = 1 

# API-endpoints
API_STATUS = "/api/status"
API_PARAMETERS = "/api/parameters"
API_RESET = "/api/reset"

SENSORMODES = {
    0: "0: Floor sensor (F)",
    1: "1: Internal sensor (A)",  # Default sensor mode
    2: "2: Internal sensor & floor sensor limitation (AF)",
    3: "3: External sensor (A2)",
    4: "4: External sensor & floor sensor limitation (A2F)",
    5: "5: Power regulator mode (PWER)"
}

SENSORVALUES = {
    0: "0: 10kΩ NTC",  # Default sensor value
    1: "1: 12kΩ NTC",
    2: "2: 15kΩ NTC",
    3: "3: 22kΩ NTC",
    4: "4: 33kΩ NTC",
    5: "5: 47kΩ NTC",
    6: "6: 6.8kΩ NTC",
    7: "7: 100kΩ NTC"
}
