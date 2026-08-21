# Heatit WiFi6 Integration for Home Assistant

This integration provides support for Heatit WiFi6 thermostats in Home Assistant.
The device is also sold under various other names depending on the region, such as "Älytermostaatti Pistesarjat WiFi6" in Finland.

## Disclaimer
This software is a third-party integration and is not affiliated with, maintained, or supported by Heatit (Thermo-Floor AS). Use it at your own risk.

## Supported Devices
* Heatit WiFi6 Thermostat (Firmware v2.20 and newer)

## Installation

### Method 1: HACS (Recommended)
1. Ensure [HACS](https://hacs.xyz/) is installed.
2. Go to **HACS** -> **Integrations**.
3. Click the three dots in the top right corner and select **Custom repositories**.
4. Add the URL to this repository, select **Integration** as the category, and click **Add**.
5. Find "Heatit WiFi6" in the list and click **Install**.
6. Restart Home Assistant.

### Method 2: Manual Installation
1. Download the `heatit_wifi6` folder from `custom_components/` in this repository.
2. Copy the folder into your Home Assistant `config/custom_components/` directory.
3. Restart Home Assistant.

## Setup
1. Ensure your thermostat is connected to your local WiFi network via the official Heatit mobile app.
2. In Home Assistant, go to **Settings** -> **Devices & Services** -> **Add Integration**.
3. Search for **Heatit WiFi6**.
4. Enter a descriptive name for your device.
5. Enter the local IP address of the thermostat (e.g., `http://192.168.1.50`).
6. Submit the configuration.

## Features & Usage
* **Climate entity:** Heat / Cool / Off modes, target temperature, and an Eco preset.
* **Sensor modes:** Supports Floor, Internal, and External sensor modes. The climate entity's current temperature automatically reflects the active sensor mode.
* **Sensors (enabled by default):** Current temperature, target temperature, power, and energy.
* **Sensors (disabled by default, enable per-entity if needed):**
    * Internal, external, and floor temperatures (always available, regardless of sensor mode)
    * Heating, cooling, and eco setpoints (diagnostic)
    * WiFi signal strength (diagnostic)
* **Binary sensors:** Open window detected, and open window detection enabled (diagnostic).
* **Device page:** Each thermostat is linked to its web UI via the `Visit` button (uses the device's local IP) and shows the WiFi MAC under connections.
* **Polling:** Local polling once per minute.
* **Advanced control:** Parameters can be changed via HTTP POST to `/api/parameters` on the device. See the OpenAPI documentation in the `docs` folder.
* **Energy meter:** Reset the kWh meter by sending a DELETE request to `/api/reset/kwh` on the device.

## Version History
* **1.3.1**
    * Documentation: corrected the OpenAPI spec for `POST /api/parameters` to declare a JSON `requestBody` instead of `in: query` parameters, matching the actual device behaviour. This unblocks the Prism-backed integration test in CI.
* **1.3.0**
    * **Breaking:** The `extra_state_attributes` blob on the climate entity has been removed. Telemetry and parameters are now exposed as dedicated sensor / binary_sensor entities (some are disabled by default — enable them in the entity registry as needed). Update any automations or templates that referenced `state_attr('climate.<id>', 'param_...')` or `info_...` attributes to use the new entities instead.
    * Added internal / external / floor temperature sensors, heating / cooling / eco setpoint diagnostic sensors, and a WiFi signal strength diagnostic sensor.
    * Added open-window-detected and open-window-detection-enabled binary sensors.
    * Aligned the integration with Home Assistant's developer guidelines: `entry.runtime_data`, shared entity base class, `quality_scale: bronze`, `configuration_url` and MAC connection on the device, translation-keyed entity names.
* **1.2.2**
    * Fixed climate entity and temperature missing due to async property getter.
* **1.2.1**
    * Fixed dual climate entity popping up 
* **1.2.0**
    * Fixed climate entity grouping with sensors under a single device.
* **1.1.2**
    * Prepared for official PR.
    * Synchronized domain and logic for better compatibility.
* **1.1.1**
    * Enhanced stability and logic improvements.
* **0.9.4**
    * Current temperature is now dynamically based on the **sensorMode** configured on the device (Floor, Internal, or External).
* **0.9.3**
    * Initial Release

## License
This software is licensed under the [MIT License](LICENSE.md).
