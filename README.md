# Heatit WiFi6 Integration for Home Assistant

This integration provides support for Heatit WiFi6 thermostats in Home Assistant.
The device is also sold under various other names depending on the region, such as "Älytermostaatti Pistesarjat WiFi6" in Finland.

## Disclaimer
This software is a third-party integration and is not affiliated with, maintained, or supported by Heatit (Thermo-Floor AS). Use it at your own risk.

## Supported Devices
* Heatit WiFi6 Thermostat (Firmware v2.20 and newer)
* Heatit WiFi7 Thermostat (tested on firmware 0.1.13 — note the WiFi7 firmware numbering starts at 0.x)

### WiFi7 compatibility notes
The WiFi7 exposes the same local HTTP API as the WiFi6 (`/api/status`, `/api/parameters`, `/api/reset/...`), so all entities of this integration work on both models. Additionally:
* The WiFi7 reports a `model` field in `/api/status`; the device page shows the correct model automatically (WiFi6 devices fall back to "WiFi6 Thermostat").
* The WiFi7 adds a Relay sensor mode (RELA) — available in the sensor mode select; selecting it on a WiFi6 is rejected by the device. While in Relay mode, a "Relay" switch entity controls the output (`onOff` parameter) and the climate entity becomes unavailable (the device is a plain on/off relay then).
* WiFi7-only features (BlueFusion BLE devices, DirectLink, `externalSensorFallback`) are not yet supported by this integration.

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
    * WiFi signal strength (dBm) and WiFi signal quality (%) (diagnostic)
* **Binary sensors:** Open window detected, and open window detection enabled (diagnostic).
* **Open window remaining time (diagnostic):** Seconds until the open window detection restores the normal setpoint.
* **Switches (configuration):** Display measured temperature (instead of the setpoint, on the standby screen), child lock, and open window detection.
* **Relay switch (WiFi7 only):** Controls the output when the device runs in Relay mode; unavailable in the thermostat modes. Relay mode extras (disabled by default): always on, inverted output, automatic turn on/off timers, turn off delay, and relay state after power loss.
* **Buttons (configuration):** Reset energy meter (kWh), and reset settings to defaults (disabled by default; keeps the WiFi credentials).
* **Numbers (configuration):** Floor minimum/maximum temperature limits (enabled by default — floor protection), and disabled by default: internal/external temperature limits, hysteresis, active/standby display brightness, internal/floor/external sensor calibration, power regulator active time (PWER duty cycle), size of load (for contactor installs), and the retry delay after an overload/overheat error.
* **Selects (configuration, disabled by default):** Sensor mode (Floor / Internal / AF / External / A2F / Power regulator / Relay*), regulation mode (Hysteresis / PWM), NTC sensor type (6.8–100 kΩ; the WiFi6 and WiFi7 number these differently, handled automatically), and external sensor fallback*.
* **Entities that don't apply to the current mode** (e.g. thermostat settings while a WiFi7 runs in Relay mode) show as unavailable instead of unknown.
* **Faulty sensor handling:** A disconnected floor/external NTC sensor (reported as exactly 100.0 °C by the firmware) shows as unavailable instead of 100 °C.
* **Device page:** Each thermostat is linked to its web UI via the `Visit` button (uses the device's local IP) and shows the WiFi MAC under connections.
* **Polling:** Local polling, once per minute by default — configurable (10–3600 s) via the integration's options. The options also allow changing the device's address (e.g. after a new DHCP lease) without re-adding it.
* **Diagnostics:** Download a redacted `/api/status` dump from the device page for bug reports.
* **Advanced control:** Parameters can be changed via HTTP POST to `/api/parameters` on the device. See the OpenAPI documentation in the `docs` folder.

\* Relay mode and the external sensor fallback exist on the WiFi7 only.

## Development
Unit tests mock the device API and run against a real Home Assistant core:
```bash
pip install -r requirements_test.txt
pytest
```
`tests/test_integration.py` is the end-to-end check used by CI (a Prism mock of the OpenAPI spec plus a Home Assistant container) and is skipped by the default `pytest` run.

## Version History
* **1.4.0**
    * Reconfigure support: change the device's address from the entry's ⋮ menu → *Reconfigure* (e.g. after a DHCP lease change) without removing and re-adding the integration. The flow verifies the new address answers and belongs to the same thermostat.
    * Unit tests (pytest-homeassistant-custom-component) for the number, select, switch, sensor and button platforms plus the config, options and reconfigure flows, covering the WiFi6, WiFi7 and WiFi7 Relay mode payloads.
    * New configuration numbers: floor/internal/external temperature limits (floor limits enabled by default), size of load, retry delay after error; WiFi7 Relay mode timers (automatic turn on/off, turn off delay).
    * New configuration selects: regulation mode (Hysteresis / PWM), NTC sensor type, WiFi7 external sensor fallback and relay state after power loss.
    * New configuration switches (WiFi7 Relay mode): always on, inverted output.
    * New "Reset settings to defaults" button (disabled by default) and an "Open window remaining time" sensor.
    * New WiFi signal quality (%) sensor next to the dBm one.
    * Writes no longer trigger an immediate readback (the firmware can report the old value for a moment), so changes stay visible in HA; sibling entities update together.
    * WiFi7 fixes from live testing: child lock payload type, lowercase relay states, 0–100 display brightness scale, renamed calibration parameters, top-level `wifiSignalStrength`, and entities that don't apply in Relay mode show as unavailable.
    * WiFi7 support: confirmed working on real hardware; the device model is now read from the API (`model` field), so WiFi7 units are labeled correctly.
    * Fixed `DELETE /api/reset/{type}` to send the spec-required `?reset=reset` query parameter.
    * New "Reset energy meter" button.
    * New configuration switches: display measured temperature, child lock, open window detection.
    * New configuration numbers (disabled by default): hysteresis, display brightness (active/standby), sensor calibration (internal/floor/external).
    * New sensor mode select (disabled by default), including the WiFi7-only Relay mode.
    * New Relay switch for WiFi7 devices in Relay mode (`onOff` parameter); the climate entity is unavailable while in that mode.
    * WiFi signal strength is now a numeric dBm sensor (device class `signal_strength`).
    * Disconnected NTC sensors (100.0 °C sentinel) now show as unavailable.
    * New options flow: polling interval (10–3600 s) and host/IP change without re-adding the device.
    * New diagnostics platform (redacted status dump).
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
