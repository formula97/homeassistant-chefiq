"""Config flow for Chef iQ integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ADDRESS

from .const import DOMAIN, MANUFACTURER_ID


class ChefIQConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Chef iQ."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_devices: dict[str, str] = {}  # address -> name
        self._discovered_address: str = ""
        self._discovered_name: str = ""

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle bluetooth discovery."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        last4 = discovery_info.address.replace(":", "")[-4:].upper()
        self._discovered_address = discovery_info.address
        self._discovered_name = f"Chef iQ Probe ({last4})"
        self.context["title_placeholders"] = {"name": self._discovered_name}

        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm bluetooth discovery."""
        if user_input is not None:
            return self.async_create_entry(
                title=self._discovered_name,
                data={CONF_ADDRESS: self._discovered_address},
            )

        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={"name": self._discovered_name},
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the user step — show discovered CQ60 devices to pick from."""
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            name = self._discovered_devices.get(address, address)
            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=name,
                data={CONF_ADDRESS: address},
            )

        # Scan for known CQ60 devices not yet configured.
        for service_info in async_discovered_service_info(self.hass):
            address = service_info.address
            if address in self._discovered_devices:
                continue
            if MANUFACTURER_ID not in service_info.manufacturer_data:
                continue
            last4 = service_info.address.replace(":", "")[-4:].upper()
            self._discovered_devices[address] = f"Chef iQ Probe ({last4})"

        if not self._discovered_devices:
            return self.async_abort(reason="no_devices_found")

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): vol.In(
                        {
                            address: f"{name} ({address})"
                            for address, name in self._discovered_devices.items()
                        }
                    )
                }
            ),
        )
