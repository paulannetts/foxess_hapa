"""Sensor platform for myenergi."""

from homeassistant.components.number import NumberEntity
from homeassistant.helpers.entity import EntityCategory
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .data import HaTest01ConfigEntry
from .entity import HaTest01Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

ENTITY_CATEGORY_CONFIG = EntityCategory.CONFIG


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HaTest01ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Setup number platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    devices = []
    devices.append(MinimumGreenLevelNumber(coordinator, device, entry))
    async_add_entities(devices)


class BatMinSocNumber(HaTest01Entity, NumberEntity):
    """FoxESS BatMinSocNumber class."""

    def __init__(self, coordinator):
        super().__init__(
            coordinator,
        )
        self._attr_icon = "mdi:battery"
        self._attr_unique_id = f"{self.coordinator.config_entry.entry_id}-bat-min-soc"
        self._attr_name = f"{self.coordinator.config_entry.entry_id} Battery Min SoC"
        self._attr_translation_key = "bat_min_soc"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.device.bat_min_soc

    async def async_set_native_value(self, value: float) -> None:
        """Change the selected option."""
        await self.device.set_minimum_green_level(int(value))
        self.async_schedule_update_ha_state()

    @property
    def native_min_value(self):
        return 10

    @property
    def native_max_value(self):
        return 100

    @property
    def native_step(self):
        return 1
