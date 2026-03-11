"""Constants for the Chef iQ integration."""

from homeassistant.const import Platform

DOMAIN = "chefiq"
PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR]

BATTERY_LOW_THRESHOLD = 20  # percent

MANUFACTURER_ID = 0x05CD  # 1485 decimal
