"""Parser for Chef iQ BLE advertisements.

HA's bluetooth API provides manufacturer_data as dict[manufacturer_id, bytes],
where the bytes payload begins AFTER the 0xFF AD type byte and 2-byte manufacturer ID.

Confirmed packet layouts (all offsets relative to start of payload bytes):

Type 0x01 — Temperature packet (18 bytes):
  [0]     0x01  packet type
  [1]     0x50  flags
  [2:4]   uint16 LE  ambient temperature (tenths °C)
  [4:6]   uint16 LE  probe housing temperature (~+0.5°C vs ambient, skip)
  [6:8]   uint16 LE  probe tip temperature (deepest point)
  [8:10]  uint16 LE  zone 1 (closest to tip)
  [10:12] uint16 LE  zone 2 (middle)
  [12:14] uint16 LE  zone 3 (closest to handle)
  [14:16] uint16 LE  duplicate ambient (ignore)
  [16:18] uint16 LE  proprietary checksum (algorithm unknown)
  Unavailable sentinel: 0x00C0

Type 0x03 — Status packet (17 bytes):
  [0]     0x03  packet type
  [1]     0x50  flags
  [2:8]   probe MAC address (6 bytes)
  [8]     battery level (0–100%)
  [9]     unknown (varies ±1, likely ADC noise)
  [10]    0x1E  constant (unknown)
  [11]    per-probe constant (1 or 50, unconfirmed meaning)
  [12]    0x03  constant (unknown)
  [13]    0x01  constant (unknown)
  [14]    0x00  constant (unknown)
  [15:17] unknown (varies, possibly a second checksum)

Type 0x00 — Name packet:
  Not parsed (name is not used by the integration).

Reference: https://github.com/custom-components/ble_monitor/issues/1279
"""

from __future__ import annotations

import logging
import struct
from typing import Any

from .const import MANUFACTURER_ID

_LOGGER = logging.getLogger(__name__)

PACKET_TYPE_TEMP = 0x01
PACKET_TYPE_STATUS = 0x03


def parse_advertisement(manufacturer_data: dict[int, bytes]) -> dict[str, Any] | None:
    """Parse a Chef iQ BLE advertisement.

    Returns a dict with parsed fields, or None if not parseable.
    """
    if MANUFACTURER_ID not in manufacturer_data:
        return None

    data = manufacturer_data[MANUFACTURER_ID]

    if len(data) < 3:
        _LOGGER.debug("ChefIQ: packet too short (%d bytes)", len(data))
        return None

    packet_type = data[0]

    result: dict[str, Any] = {"packet_type": packet_type}

    if packet_type == PACKET_TYPE_TEMP:
        # Temperature packet — confirmed 18 bytes (see module docstring).
        if len(data) < 18:
            _LOGGER.debug("ChefIQ temp packet too short: %d bytes", len(data))
            return None

        _LOGGER.debug("ChefIQ raw temp packet hex: %s (len=%d)", data.hex(), len(data))

        # Confirmed layout — see module docstring for full details
        offset = 2
        sensor_keys: list[str | None] = [
            "temperature_ambient",  # offset 2:  oven/air temperature
            None,                   # offset 4:  probe housing temp (skip)
            "temperature_probe_1",  # offset 6:  probe tip (deepest)
            "temperature_probe_2",  # offset 8:  zone 1 (closest to tip)
            "temperature_probe_3",  # offset 10: zone 2 (middle)
            "temperature_probe_4",  # offset 12: zone 3 (closest to handle)
        ]
        try:
            for key in sensor_keys:
                raw = struct.unpack_from("<H", data, offset)[0]
                offset += 2
                if key is None:
                    continue
                if raw != 0x00C0:
                    result[key] = round(raw / 10.0, 1)
                else:
                    result[key] = None
        except struct.error as err:
            _LOGGER.debug("ChefIQ temp packet parse error: %s", err)
            return None

        _LOGGER.debug(
            "ChefIQ temp packet: tip=%s ambient=%s",
            result.get("temperature_probe_1"),
            result.get("temperature_ambient"),
        )

    elif packet_type == PACKET_TYPE_STATUS:
        _LOGGER.debug("ChefIQ status packet: %s", data.hex())
        # Byte 8 is battery percentage (0–100), confirmed via overnight drain capture
        if len(data) < 17:
            _LOGGER.debug("ChefIQ status packet too short: %d bytes", len(data))
            return None
        battery = data[8]
        if 0 <= battery <= 100:
            result["battery"] = battery
            _LOGGER.debug("ChefIQ battery: %d%%", battery)

    else:
        _LOGGER.debug("ChefIQ unknown packet type 0x%02X: %s", packet_type, data.hex())
        return None

    return result
