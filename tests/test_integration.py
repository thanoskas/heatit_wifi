import time
import requests
import json
import logging
import sys

HA_URL = "http://localhost:8123"
LOG_PATH = "ha_config/home-assistant.log"

def main():
    print("Waiting for Home Assistant API to become ready...")
    # Polling until REST API is reachable
    for _ in range(30):
        try:
            res = requests.get(f"{HA_URL}/api/")
            if res.status_code in [200, 401]:
                break
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(2)
    else:
        print("Timeout waiting for HA API.")
        try:
            with open(LOG_PATH, "r") as f:
                print("----- ha_config/home-assistant.log -----")
                print(f.read())
        except FileNotFoundError:
            print("Log file not found.")
        sys.exit(1)

    print("Checking Home Assistant logs for Heatit WiFi6 initialization...")
    entity_loaded = False
    for _ in range(15):
        try:
            with open(LOG_PATH, "r") as f:
                logs = f.read()
                if "Heatit WiFi6" in logs and "added to the list of entities" in logs:
                    entity_loaded = True
                    break
        except FileNotFoundError:
            pass
        time.sleep(2)

    if not entity_loaded:
        print("FAILED: Entity did not load.")
        try:
            with open(LOG_PATH, "r") as f:
                print(f.read())
        except FileNotFoundError:
            print("Log file not found.")
        sys.exit(1)

    print("Entity loaded! Waiting for startup automation to set HVAC mode...")

    # Check logs for "set_parameter" which confirms the automation triggered the API client
    # The automation is configured to run 10 seconds after startup.
    for _ in range(15):
        try:
            with open(LOG_PATH, "r") as f:
                logs = f.read()
                # Check for the specific log output from our api call setting the hvac mode
                if "set_parameter(operatingMode" in logs or "Set parameter to the thermostat" in logs:
                    print("SUCCESS: Integration initialized, entities added, and HVAC mode set successfully.")
                    sys.exit(0)
        except FileNotFoundError:
            pass
        time.sleep(2)

    print("FAILED: Did not detect setting HVAC mode.")
    try:
        with open(LOG_PATH, "r") as f:
            print(f.read())
    except FileNotFoundError:
        print("Log file not found.")
    sys.exit(1)

if __name__ == "__main__":
    main()
