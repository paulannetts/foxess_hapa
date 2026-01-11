"""Number platform for foxess_hapa."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import PERCENTAGE

from .const import LOGGER
from .entity import FoxessHapaEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import FoxessHapaDataUpdateCoordinator
    from .data import FoxessHapaConfigEntry


@dataclass(frozen=True, kw_only=True)
class FoxessHapaNumberEntityDescription(NumberEntityDescription):
    """Describes a FoxESS HAPA number entity."""

    value_attr: str  # Attribute name in battery_settings


NUMBER_DESCRIPTIONS: tuple[FoxessHapaNumberEntityDescription, ...] = (
    FoxessHapaNumberEntityDescription(
        key="min_soc",
        translation_key="min_soc",
        name="Min SoC",
        native_min_value=10,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        device_class=NumberDeviceClass.BATTERY,
        mode=NumberMode.SLIDER,
        icon="mdi:battery-low",
        value_attr="min_soc",
    ),
    FoxessHapaNumberEntityDescription(
        key="min_soc_on_grid",
        translation_key="min_soc_on_grid",
        name="Min SoC On Grid",
        native_min_value=10,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        device_class=NumberDeviceClass.BATTERY,
        mode=NumberMode.SLIDER,
        icon="mdi:battery-charging-low",
        value_attr="min_soc_on_grid",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: FoxessHapaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the number platform."""
    coordinator = entry.runtime_data.coordinator

    # Only add battery number entities if device has battery
    if coordinator.data:
        device_info = coordinator.data.get("device_info")
        if device_info and device_info.has_battery:
            async_add_entities(
                FoxessHapaNumber(
                    coordinator=coordinator,
                    entity_description=description,
                )
                for description in NUMBER_DESCRIPTIONS
            )


class FoxessHapaNumber(FoxessHapaEntity, NumberEntity):
    """FoxESS HAPA Number class for battery settings."""

    entity_description: FoxessHapaNumberEntityDescription

    def __init__(
        self,
        coordinator: FoxessHapaDataUpdateCoordinator,
        entity_description: FoxessHapaNumberEntityDescription,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{entity_description.key}"
        )

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        if not self.coordinator.data:
            return None

        battery_settings = self.coordinator.data.get("battery_settings")
        if not battery_settings:
            return None

        return getattr(battery_settings, self.entity_description.value_attr, None)

    async def async_set_native_value(self, value: float) -> None:
        """
        Set the new value via the scheduler API.

        Note: FoxESS requires using the scheduler API to change battery settings.
        Individual setting changes may return 'Unsupported Function Code' when
        the mode scheduler is enabled.
        """
        LOGGER.info(
            "Setting %s to %s via scheduler API",
            self.entity_description.key,
            value,
        )

        # Get current scheduler settings
        client = self.coordinator.config_entry.runtime_data.client
        try:
            current_schedule = await client.async_get_scheduler()

            # Modify the schedule with new minSoC value
            # The structure depends on the current schedule
            groups = current_schedule.get("groups", [])

            if not groups:
                # Create a default schedule period if none exists
                groups = [
                    {
                        "enable": 1,
                        "startHour": 0,
                        "startMinute": 0,
                        "endHour": 23,
                        "endMinute": 59,
                        "workMode": "SelfUse",
                        "minSoc": int(value)
                        if self.entity_description.value_attr == "min_soc"
                        else 10,
                        "minSocOnGrid": int(value)
                        if self.entity_description.value_attr == "min_soc_on_grid"
                        else 10,
                    }
                ]
            else:
                # Update existing schedule periods
                for group in groups:
                    if self.entity_description.value_attr == "min_soc":
                        group["minSoc"] = int(value)
                    elif self.entity_description.value_attr == "min_soc_on_grid":
                        group["minSocOnGrid"] = int(value)

            # Apply the updated schedule
            success = await client.async_set_scheduler(groups, enable=True)

            if success:
                LOGGER.info(
                    "Successfully updated %s to %s", self.entity_description.key, value
                )
                # Refresh coordinator data
                await self.coordinator.async_request_refresh()
            else:
                LOGGER.error("Failed to update %s", self.entity_description.key)

        except Exception as ex:
            LOGGER.exception("Error setting %s: %s", self.entity_description.key, ex)
            raise
