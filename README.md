# Heatit WiFi integration for Home Assistant

[![Validate](https://github.com/thanoskas/heatit_wifi/actions/workflows/validate.yml/badge.svg)](https://github.com/thanoskas/heatit_wifi/actions/workflows/validate.yml)
[![Unit tests](https://github.com/thanoskas/heatit_wifi/actions/workflows/tests.yml/badge.svg)](https://github.com/thanoskas/heatit_wifi/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE.md)

<div align="center">
  <a href="https://smarthomehellas.gr"><img src="https://github.com/thanoskas/heatit_wifi/raw/main/docs/images/smarthomehellas_logo.png" alt="Smart Home Hellas" width="240"></a>
  <p><strong>Proudly made by <a href="https://smarthomehellas.gr">Smart Home Hellas</a></strong></p>
</div>

Local (LAN-only, no cloud) Home Assistant integration for the **Heatit WiFi6** and **Heatit WiFi7** thermostats by Heatit, using the thermostats' built-in HTTP API.

Developed and maintained by [Smart Home Hellas](mailto:info@smarthomehellas.gr), building on the original `heatit_wifi6` community integration by [mattik-gh](https://github.com/mattik-gh/heatit_wifi6) (see [Credits](#credits)).

🇬🇷 Οδηγίες στα ελληνικά: [README.el.md](README.el.md)

## Disclaimer
This is a third-party integration, not affiliated with Heatit. Use it at your own risk.

## Supported devices
| Device | Firmware | Discovery |
|---|---|---|
| Heatit WiFi6 thermostat, V2 (DirectLink firmware) | 2.20 and newer | automatic (mDNS) |
| Heatit WiFi6 thermostat, V1 | 2.20 and newer | manual IP entry |
| Heatit WiFi7 thermostat | 0.1.13 and newer (the WiFi7 firmware numbering starts at 0.x) | automatic (mDNS) |

The WiFi6 is also sold under other names depending on the region, e.g. "Älytermostaatti Pistesarjat WiFi6" in Finland.

Both models expose the same local HTTP API (`/api/status`, `/api/parameters`, `/api/reset/...`), so every entity of this integration works on both. Differences are handled automatically:
* The WiFi7 reports a `model` field, so the device page shows the correct model. WiFi6 units are labeled "WiFi6 Thermostat".
* The WiFi7 adds a **Relay** sensor mode (RELA). While in Relay mode a "Relay" switch controls the output and the climate entity becomes unavailable (the device is a plain on/off relay then). Selecting Relay mode on a WiFi6 is rejected by the device.
* WiFi7-only extras (external sensor fallback, relay timers, relay state after power loss) are only offered on WiFi7 units.
* Not supported yet: WiFi7 BlueFusion (BLE accessories) and DirectLink pairing.

## Installation

### Option 1 — HACS (recommended)
1. Make sure [HACS](https://hacs.xyz/) is installed.
2. Open **HACS**, click the **⋮** menu (top right) and choose **Custom repositories**.
3. Repository: `https://github.com/thanoskas/heatit_wifi` — Type: **Integration** — click **Add**.
4. Search for **Heatit WiFi** in HACS and click **Download**.
5. Restart Home Assistant.

### Option 2 — Manual
1. Download the latest release from the [Releases](https://github.com/thanoskas/heatit_wifi/releases) page.
2. Copy the folder `custom_components/heatit_wifi` into your Home Assistant `config/custom_components/` directory (final path: `config/custom_components/heatit_wifi/manifest.json`).
3. Restart Home Assistant.

## Setup
The thermostat must already be connected to your WiFi network through the official Heatit app.

**Automatic discovery (WiFi7, WiFi6 V2):** shortly after the restart a *Discovered* card appears under **Settings → Devices & services**. Click **Add**, give the thermostat a name and submit.

**Manual (WiFi6 V1, or if discovery does not show up):**
1. Go to **Settings → Devices & services → Add integration**.
2. Search for **Heatit WiFi**.
3. Enter a name for the thermostat and its local IP address (e.g. `192.168.1.50`; the `http://` prefix is optional).
4. Submit. The integration verifies that the device answers before creating the entry.

Give the thermostat a fixed IP (DHCP reservation) in your router if you can. The integration copes with address changes (see below) but a fixed address avoids the extra step.

### Options
Open the integration entry and click **Configure**:
* **Polling interval** — 10 to 3600 seconds (default 60).
* **Host** — change the IP/hostname after a DHCP lease change without removing the device. The same is available from the entry's **⋮ → Reconfigure** menu. When the thermostat is discoverable, a new IP is picked up automatically via mDNS.

## Entities
* **Climate:** Heat / Cool / Off modes, target temperature, Eco preset. The current temperature follows the sensor mode configured on the device (floor, internal or external sensor).
* **Sensors (enabled by default):** current temperature, target temperature, power (W), energy (kWh).
* **Sensors (disabled by default):** internal, external and floor temperatures; heating, cooling and eco setpoints; WiFi signal strength (dBm) and quality (%); IP address; open window remaining time.
* **Binary sensors:** open window detected; open window detection enabled.
* **Switches (configuration):** display measured temperature on the standby screen, child lock, open window detection. **WiFi7 Relay mode:** relay output, always on, inverted output.
* **Buttons (configuration):** reset energy meter; reset settings to defaults (disabled by default, keeps WiFi credentials); factory reset (disabled by default — **also erases the WiFi credentials**, the thermostat must be re-provisioned with the Heatit app).
* **Numbers (configuration):** floor minimum/maximum temperature limits (enabled by default — floor protection); disabled by default: internal/external temperature limits, hysteresis, active/standby display brightness, internal/floor/external sensor calibration, power regulator active time (PWER duty cycle), size of load, retry delay after an overload/overheat error, WiFi7 relay timers.
* **Selects (configuration, disabled by default):** sensor mode (Floor / Internal / AF / External / A2F / Power regulator / Relay on WiFi7), regulation mode (Hysteresis / PWM), NTC sensor type (6.8–100 kΩ; the WiFi6 and WiFi7 number these differently, handled automatically), WiFi7 external sensor fallback and relay state after power loss.
* Entities that do not apply to the current mode (e.g. thermostat settings while a WiFi7 runs in Relay mode) show as *unavailable* instead of *unknown*.
* A disconnected floor/external NTC sensor (reported as exactly 100.0 °C by the firmware) shows as *unavailable* instead of 100 °C.
* **Device page:** *Visit device* opens the thermostat's web UI; the WiFi MAC is listed under connections. **Diagnostics** downloads a redacted `/api/status` dump for bug reports.

Disabled-by-default entities can be enabled per entity from the device page.

## Migrating from the `heatit_wifi6` integration
Version 2.0.0 renamed the integration from *Heatit WiFi6* (domain `heatit_wifi6`) to **Heatit WiFi** (domain `heatit_wifi`), since it supports the whole WiFi thermostat family. Home Assistant treats it as a new integration, so:
1. Note the name(s) of your thermostat entries under the old integration.
2. Delete the old entries (**Settings → Devices & services → Heatit WiFi6 → ⋮ → Delete**).
3. Remove the old folder `config/custom_components/heatit_wifi6` (HACS: remove the old repository) and install this one as described above.
4. Restart Home Assistant and add the thermostat(s) again **using the same names**. Entity IDs are derived from the name, so automations and dashboards keep working in the usual case. Re-enable any disabled-by-default entities you were using.

## Troubleshooting
* **Not discovered automatically:** WiFi6 V1 firmware does not advertise itself on mDNS — add it manually by IP. Discovery also requires Home Assistant and the thermostat to be on the same network segment (no VLAN/AP client isolation in between).
* **"Cannot connect":** open `http://<thermostat-ip>/api/status` in a browser on the same network. If you get JSON, Home Assistant can reach it too. If not, check the IP in the Heatit app or your router.
* **Device stopped updating after a router change:** the thermostat got a new IP. Use **⋮ → Reconfigure** on the entry (or wait for mDNS to update it automatically on WiFi7/WiFi6 V2).
* **Floor/external temperature shows unavailable:** the sensor is disconnected or the wrong NTC type is selected (the firmware reports 100 °C in that case).
* **A setting does not stick:** the firmware can briefly report the previous value after a write. The integration keeps the value you set until the next poll confirms it.
* For bug reports use the [issue tracker](https://github.com/thanoskas/heatit_wifi/issues) and attach the diagnostics download from the device page (it is redacted).

## Development
```bash
pip install -r requirements_test.txt
pytest
```
Unit tests use `pytest-homeassistant-custom-component` with a mocked device and cover the WiFi6, WiFi7 and WiFi7 Relay mode payloads. `tests/test_integration.py` is the end-to-end check run by CI (a Prism mock of the WiFi6 OpenAPI spec in `custom_components/heatit_wifi/docs` plus a Home Assistant container) and is skipped by a plain `pytest` run. Every push is validated with hassfest and the HACS action.

The device API is documented in `custom_components/heatit_wifi/docs/Heatit_WiFi6_OpenAPI_v70.yaml`. Parameters can also be changed directly with an HTTP POST to `/api/parameters`.

## Version history
* **2.0.3**
    * Fix: the Heatit icon and logo now show in Home Assistant (Settings → Devices & services, the setup dialog and the device page; HA 2026.3 or newer). The images were in a `brands/` folder, which Home Assistant does not read; they are now in `brand/`. The HACS store still shows a placeholder until HACS supports icons shipped inside the integration.
    * Version history: the entries for the original `heatit_wifi6` releases (0.9.3 – 1.2.x) were removed; see the Credits section.
* **2.0.2**
    * Fix: *Power regulator active time* now uses the thermostat's real scale. The device stores 1–10 (×10 %), but the entity treated the raw value as 10–100 %, so the default 20 % showed as "2 %" and writes sent out-of-range values. It now shows 10–100 % in 10 % steps. If you changed this setting with an earlier version, set it again.
* **2.0.1**
    * Greek translation: the setup, options and reconfigure screens plus every entity name and select option appear in Greek when the HA profile language is Ελληνικά. Entity IDs do not change.
    * CI: Dependabot for GitHub Actions and a monthly test run against HA stable, beta and dev.
* **2.0.0**
    * Integration renamed to **Heatit WiFi** (domain `heatit_wifi`) and moved to this repository, maintained by Smart Home Hellas. Existing `heatit_wifi6` users: see [Migrating](#migrating-from-the-heatit_wifi6-integration).
    * Includes everything from the unreleased 1.4.0 below (zeroconf discovery, reconfigure, WiFi7 support incl. Relay mode, full parameter coverage, unit tests).
    * CI: hassfest + HACS validation and unit tests on every push.
* **1.4.0** (never published as a release — folded into 2.0.0)
    * Zeroconf discovery: WiFi7 firmware (confirmed on 0.1.13) advertises `directlink._tf._tcp` via mDNS, so Home Assistant now discovers the thermostat automatically — and when a known thermostat shows up on a new IP (DHCP lease change), the stored address is updated in place without any user action. Devices answering `_tf._tcp` without the Heatit local API are ignored silently.
    * Reconfigure support: change the device's address from the entry's ⋮ menu → *Reconfigure* (e.g. after a DHCP lease change) without removing and re-adding the integration. The flow verifies the new address answers and belongs to the same thermostat.
    * Unit tests (pytest-homeassistant-custom-component) for the number, select, switch, sensor and button platforms plus the config, options and reconfigure flows, covering the WiFi6, WiFi7 and WiFi7 Relay mode payloads.
    * New configuration numbers: floor/internal/external temperature limits (floor limits enabled by default), size of load, retry delay after error; WiFi7 Relay mode timers (automatic turn on/off, turn off delay).
    * New configuration selects: regulation mode (Hysteresis / PWM), NTC sensor type, WiFi7 external sensor fallback and relay state after power loss.
    * New configuration switches (WiFi7 Relay mode): always on, inverted output.
    * New "Reset settings to defaults" button (disabled by default) and an "Open window remaining time" sensor.
    * New "Factory reset" button (disabled by default). **Warning:** unlike the settings reset, this also erases the WiFi credentials — the thermostat goes offline and must be re-provisioned with the Heatit app. Enable it in the entity registry only when you actually need it.
    * New WiFi signal quality (%) sensor next to the dBm one, and an IP address diagnostic sensor (disabled by default).
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

## Credits
* [mattik-gh](https://github.com/mattik-gh/heatit_wifi6) — original `heatit_wifi6` integration (versions 0.9.3 – 1.2.x) and the WiFi6 OpenAPI document.
* [lvlie](https://github.com/lvlie/heatit_wifi6) — sensor/binary-sensor split and HA developer-guideline alignment (1.3.x).
* [atlehogberg](https://github.com/atlehogberg) and [vlad-323](https://github.com/vlad-323) — fixes and improvements merged upstream.
* [Smart Home Hellas](mailto:info@smarthomehellas.gr) (Thanos Kasolas) — WiFi7 support, discovery, reconfigure, parameter coverage, tests and maintenance since 2026.

## License
[MIT](LICENSE.md).

---

<div align="center">
<strong>⭐ If this integration helps you automate your home, please star the repository!</strong>
</div>

<div align="center">
<strong>☕ Support Development</strong><br>
If you find this project helpful:<br><br>
<a href="https://paypal.me/thanoskasolas"><img src="https://img.shields.io/badge/PayPal-Donate-blue.svg?style=for-the-badge" alt="PayPal Donate"></a>
</div>

---

<div align="center">
<sub>Made with ❤️ by <a href="https://smarthomehellas.gr">Smart Home Hellas</a></sub>
</div>
