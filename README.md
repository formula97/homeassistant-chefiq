# Chef iQ for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

Home Assistant integration for the Chef iQ CQ60 Bluetooth thermometer probe. Provides real-time temperature readings from all probe zones, ambient temperature, a computed probe average, and battery level — all via passive Bluetooth scanning with no cloud dependency.

---

## Supported Devices

| Device | Model | Bluetooth Name |
|--------|-------|----------------|
| Chef iQ Smart Wireless Meat Thermometer | CQ60 | `CQ60` |

This integration has been developed and tested against two CQ60 probes running simultaneously. Each probe is discovered and added as a separate device.

---

## Sensors

Each probe exposes the following sensors:

| Sensor | Description | Category |
|--------|-------------|----------|
| Ambient Temperature | Oven or air temperature at the probe handle | — |
| Probe Tip | Temperature at the deepest insertion point | — |
| Probe Zone 1 | Temperature closest to the tip | — |
| Probe Zone 2 | Temperature at the middle zone | — |
| Probe Zone 3 | Temperature closest to the handle | — |
| Probe Average | Average of all four probe zones (requires ≥ 2 valid readings) | — |
| Battery | Probe battery level | Diagnostic |

All temperatures are reported in °C and converted by Home Assistant to your preferred unit.

---

## Requirements

- Home Assistant 2023.6 or later
- A Bluetooth adapter accessible to your HA host
- Passive Bluetooth scanning enabled (no pairing required)
- [HACS](https://hacs.xyz) installed

---

## Installation

### Via HACS (recommended)

1. In Home Assistant, open **HACS → Integrations**
2. Click the three-dot menu → **Custom repositories**
3. Add `https://github.com/formula97/homeassistant-chefiq` as an **Integration**
4. Search for **Chef iQ** and click **Download**
5. Restart Home Assistant

### Manual

1. Copy the `custom_components/chefiq/` folder from this repository into your HA `custom_components/` directory
2. Restart Home Assistant

---

## Setup

### Automatic discovery

If your probe is powered on and in range, Home Assistant will discover it automatically and prompt you to add it via a notification. Each probe is added as a separate device.

### Manual setup

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Chef iQ**
3. Select your probe from the list of discovered devices

To identify which physical probe corresponds to which entry, check the label on your charging case — probes are marked 1 and 2. The last four characters of the Bluetooth address are shown in the device name (e.g. `Chef iQ Probe (9FD5)`).

---

## Notes

- This integration uses **passive Bluetooth scanning only** — the probe never needs to be paired or connected
- Temperature updates arrive approximately every 1–5 seconds
- Battery level updates arrive approximately every 5–8 seconds
- Sensors show as unavailable if a probe zone returns no reading (e.g. a zone beyond insertion depth)
- The Probe Average sensor requires at least 2 valid zone readings to compute; it shows unavailable otherwise

---

## Protocol

Packet format was reverse-engineered from BLE advertisement captures. Reference: [ble_monitor issue #1279](https://github.com/custom-components/ble_monitor/issues/1279).

The integration uses manufacturer ID `0x05CD` (1485 decimal) to identify Chef iQ advertisements.

---

## License

GPL-3.0 — see [LICENSE](LICENSE) for details.
