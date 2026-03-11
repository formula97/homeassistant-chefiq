"""Chef iQ smart thermometer integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth.passive_update_processor import (
    PassiveBluetoothProcessorCoordinator,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .parser import parse_advertisement

_LOGGER = logging.getLogger(__name__)


def _coordinator_update(
    service_info: bluetooth.BluetoothServiceInfoBleak,
) -> tuple[bluetooth.BluetoothServiceInfoBleak, dict[str, Any] | None]:
    """Parse a BLE advertisement and return it alongside the raw service info.

    The coordinator calls this once per advertisement and passes the result to
    all registered processors. Returning the service_info alongside the parsed
    dict allows processors to access both (e.g. for DeviceInfo.name/address).
    """
    return (service_info, parse_advertisement(service_info.manufacturer_data))


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Chef iQ from a config entry."""
    address: str = entry.data[CONF_ADDRESS]

    coordinator = PassiveBluetoothProcessorCoordinator(
        hass,
        _LOGGER,
        address=address,
        mode=bluetooth.BluetoothScanningMode.PASSIVE,
        update_method=_coordinator_update,
    )

    # Store so both sensor and binary_sensor platforms can retrieve and
    # register their own processor against the same coordinator.
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Set up platforms first so processors are registered before we start.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Start listening for advertisements after all processors are registered.
    entry.async_on_unload(coordinator.async_start())

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        return True
    return False
