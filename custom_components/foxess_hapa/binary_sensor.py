"""Binary sensor platform for foxess_hapa."""

from __future__ import annotations

from collections.abc import Callable  # noqa: TC003
from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)

from .entity import FoxessHapaEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import FoxessHapaDataUpdateCoordinator
    from .data import FoxessHapaConfigEntry


@dataclass(frozen=True, kw_only=True)
class FoxessHapaBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes a FoxESS HAPA binary sensor entity."""

    value_fn: Callable[[dict], bool | None]


def _has_battery(data: dict) -> bool | None:
    """Return if device has battery."""
    device_info = data.get("device_info")
    if not device_info:
        return None
    return device_info.has_battery


def _is_charging(data: dict) -> bool | None:
    """Return if battery is charging."""
    real_time = data.get("real_time")
    if not real_time:
        return None
    return real_time.battery_power > 0


def _is_discharging(data: dict) -> bool | None:
    """Return if battery is discharging."""
    real_time = data.get("real_time")
    if not real_time:
        return None
    return real_time.battery_power < 0


def _is_exporting(data: dict) -> bool | None:
    """Return if exporting to grid."""
    real_time = data.get("real_time")
    if not real_time:
        return None
    return real_time.feed_in_power > 0


BINARY_SENSOR_DESCRIPTIONS: tuple[FoxessHapaBinarySensorEntityDescription, ...] = (
    FoxessHapaBinarySensorEntityDescription(
        key="has_battery",
        translation_key="has_battery",
        name="Has Battery",
        device_class=BinarySensorDeviceClass.PLUG,
        icon="mdi:battery",
        value_fn=_has_battery,
    ),
    FoxessHapaBinarySensorEntityDescription(
        key="battery_charging",
        translation_key="battery_charging",
        name="Battery Charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        icon="mdi:battery-charging",
        value_fn=_is_charging,
    ),
    FoxessHapaBinarySensorEntityDescription(
        key="battery_discharging",
        translation_key="battery_discharging",
        name="Battery Discharging",
        icon="mdi:battery-arrow-down",
        value_fn=_is_discharging,
    ),
    FoxessHapaBinarySensorEntityDescription(
        key="grid_exporting",
        translation_key="grid_exporting",
        name="Grid Exporting",
        icon="mdi:transmission-tower-export",
        value_fn=_is_exporting,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: FoxessHapaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary_sensor platform."""
    coordinator = entry.runtime_data.coordinator

    async_add_entities(
        FoxessHapaBinarySensor(
            coordinator=coordinator,
            entity_description=description,
        )
        for description in BINARY_SENSOR_DESCRIPTIONS
    )


class FoxessHapaBinarySensor(FoxessHapaEntity, BinarySensorEntity):
    """FoxESS HAPA binary_sensor class."""

    entity_description: FoxessHapaBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: FoxessHapaDataUpdateCoordinator,
        entity_description: FoxessHapaBinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary_sensor class."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{entity_description.key}"
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary_sensor is on."""
        if not self.coordinator.data:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
