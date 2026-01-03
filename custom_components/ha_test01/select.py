"""Select platform for ha_test01."""

from calendar import c
from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .data import HaTest01ConfigEntry
from .entity import HaTest01Entity

if TYPE_CHECKING:
    from .coordinator import BlueprintDataUpdateCoordinator


FOXESS_MODES = ["ForceCharge", "SelfUse"]

ATTR_BOOST_AMOUNT = "amount"

BAT_MINSOC_SCHEMA = {
    vol.Required(ATTR_BOOST_AMOUNT): vol.All(
        vol.Coerce(float),
        vol.Range(min=10, max=100),
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HaTest01ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set-up select platform."""
    platform = entity_platform.async_get_current_platform()
    coordinator = hass.data[DOMAIN][entry.entry_id]
    devices = []
    platform.async_register_entity_service(
        "bat_min_soc",
        BAT_MINSOC_SCHEMA,
        "set_bat_min_soc",
    )
    devices.append(FoxEssWorkingModeSelect(coordinator))
    async_add_entities(devices)


class FoxEssWorkingModeSelect(HaTest01Entity, SelectEntity):
    """FoxEss Sensor class."""

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_icon = "mdi:ev-station"
        self._attr_unique_id = f"{self.coordinator.config_entry.entry_id}-working-mode"
        self._attr_name = f"{self.coordinator.config_entry.entry_id} Working Mode"
        self._attr_translation_key = "working_mode"
        self._attr_options = FOXESS_MODES

    @property
    def current_option(self):
        """Return the state of the sensor."""
        return self.device.charge_mode

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        await self.device.set_charge_mode(option)
        self.async_schedule_update_ha_state()
