"""Sensor platform for Chef iQ thermometer."""

from __future__ import annotations

import logging

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth.passive_update_processor import (
    PassiveBluetoothDataProcessor,
    PassiveBluetoothDataUpdate,
    PassiveBluetoothEntityKey,
    PassiveBluetoothProcessorCoordinator,
    PassiveBluetoothProcessorEntity,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .parser import PACKET_TYPE_STATUS, PACKET_TYPE_TEMP, parse_advertisement

_LOGGER = logging.getLogger(__name__)

# Sensors populated directly from temperature packet parser output.
_TEMPERATURE_DESCRIPTIONS: dict[str, SensorEntityDescription] = {
    "temperature_ambient": SensorEntityDescription(
        key="temperature_ambient",
        name="Ambient Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    "temperature_probe_1": SensorEntityDescription(
        key="temperature_probe_1",
        name="Probe Tip",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    "temperature_probe_2": SensorEntityDescription(
        key="temperature_probe_2",
        name="Probe Zone 1",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    "temperature_probe_3": SensorEntityDescription(
        key="temperature_probe_3",
        name="Probe Zone 2",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    "temperature_probe_4": SensorEntityDescription(
        key="temperature_probe_4",
        name="Probe Zone 3",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
}

# Computed average of the four probe zone temperatures.
_AVERAGE_DESCRIPTION = SensorEntityDescription(
    key="temperature_average",
    name="Probe Average",
    device_class=SensorDeviceClass.TEMPERATURE,
    state_class=SensorStateClass.MEASUREMENT,
    native_unit_of_measurement=UnitOfTemperature.CELSIUS,
)

# Sensor populated from status packet parser output.
_BATTERY_DESCRIPTION = SensorEntityDescription(
    key="battery",
    name="Battery",
    device_class=SensorDeviceClass.BATTERY,
    state_class=SensorStateClass.MEASUREMENT,
    native_unit_of_measurement=PERCENTAGE,
    entity_category=EntityCategory.DIAGNOSTIC,
)

# Keys used to compute the probe average (all four zones).
_AVERAGE_KEYS = (
    "temperature_probe_1",
    "temperature_probe_2",
    "temperature_probe_3",
    "temperature_probe_4",
)

# All descriptions in display order, used when registering entities on setup.
_ALL_DESCRIPTIONS: dict[str, SensorEntityDescription] = {
    **_TEMPERATURE_DESCRIPTIONS,
    _AVERAGE_DESCRIPTION.key: _AVERAGE_DESCRIPTION,
    _BATTERY_DESCRIPTION.key: _BATTERY_DESCRIPTION,
}


def _passthrough_update(
    update: PassiveBluetoothDataUpdate,
) -> PassiveBluetoothDataUpdate:
    """Return the update unchanged.

    PassiveBluetoothDataProcessor requires a callable to transform updates.
    All transformation is already done in _parse_update, so this is a no-op.
    """
    return update


def _parse_update(
    service_info: bluetooth.BluetoothServiceInfoBleak,
) -> PassiveBluetoothDataUpdate:
    """Parse a BLE advertisement into a PassiveBluetoothDataUpdate."""
    parsed = parse_advertisement(service_info.manufacturer_data)

    entity_descriptions: dict[PassiveBluetoothEntityKey, SensorEntityDescription] = {}
    entity_data: dict[PassiveBluetoothEntityKey, float | None] = {}

    if parsed and parsed.get("packet_type") == PACKET_TYPE_TEMP:
        # Populate directly-parsed temperature sensors.
        for key, description in _TEMPERATURE_DESCRIPTIONS.items():
            if key in parsed:
                entity_key = PassiveBluetoothEntityKey(key, None)
                entity_descriptions[entity_key] = description
                entity_data[entity_key] = parsed[key]

        # Compute average of the four probe zones (require at least 2 valid readings).
        # Always write the key — None when insufficient zones so the sensor shows unavailable
        # rather than holding a stale value from the previous packet.
        avg_values = [parsed[k] for k in _AVERAGE_KEYS if parsed.get(k) is not None]
        avg_key = PassiveBluetoothEntityKey(_AVERAGE_DESCRIPTION.key, None)
        entity_descriptions[avg_key] = _AVERAGE_DESCRIPTION
        entity_data[avg_key] = (
            round(sum(avg_values) / len(avg_values), 1) if len(avg_values) >= 2 else None
        )

    elif parsed and parsed.get("packet_type") == PACKET_TYPE_STATUS:
        if "battery" in parsed:
            batt_key = PassiveBluetoothEntityKey(_BATTERY_DESCRIPTION.key, None)
            entity_descriptions[batt_key] = _BATTERY_DESCRIPTION
            entity_data[batt_key] = parsed["battery"]

    return PassiveBluetoothDataUpdate(
        devices={
            None: DeviceInfo(
                identifiers={(DOMAIN, service_info.address)},
                name=service_info.name or "Chef iQ Probe",
                manufacturer="Chef iQ",
                model="CQ60",
            )
        },
        entity_descriptions=entity_descriptions,
        entity_data=entity_data,
        entity_names={},
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Chef iQ sensors from a config entry."""
    address: str = entry.data[CONF_ADDRESS]

    coordinator = PassiveBluetoothProcessorCoordinator(
        hass,
        _LOGGER,
        address=address,
        mode=bluetooth.BluetoothScanningMode.PASSIVE,
        update_method=_parse_update,
    )

    processor = PassiveBluetoothDataProcessor(_passthrough_update)

    entry.async_on_unload(
        coordinator.async_register_processor(processor, SensorEntityDescription)
    )
    entry.async_on_unload(coordinator.async_start())

    async_add_entities(
        ChefIQSensor(processor, description, address)
        for description in _ALL_DESCRIPTIONS.values()
    )


class ChefIQSensor(PassiveBluetoothProcessorEntity, SensorEntity):
    """Representation of a Chef iQ probe sensor (temperature or battery)."""

    def __init__(
        self,
        processor: PassiveBluetoothDataProcessor,
        description: SensorEntityDescription,
        address: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            processor,
            PassiveBluetoothEntityKey(description.key, None),
            description,
        )
        self._attr_unique_id = f"{address}_{description.key}"

    @property
    def native_value(self) -> float | None:
        """Return the sensor value."""
        return self.processor.entity_data.get(
            PassiveBluetoothEntityKey(self.entity_description.key, None)
        )

    @property
    def available(self) -> bool:
        """Return True if the entity has a value and the coordinator is available."""
        return super().available and self.native_value is not None
