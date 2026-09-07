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
from homeassistant.const import PERCENTAGE, UnitOfPower

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

    value_attr: str  # Maps to FIELD_MAPPING key for scheduler extraParam


# Map entity value_attr to scheduler API field names (v2 uses extraParam)
FIELD_MAPPING: dict[str, str] = {
    "min_soc_on_grid": "minSocOnGrid",
    "fd_soc": "fdSoc",
    "fd_pwr": "fdPwr",
}

# The min/max below are fallbacks only. Devices report their real limits in the
# scheduler `properties` block -- an H3 allows fdPwr up to 10500 W -- so
# native_min_value/native_max_value prefer those when available.
NUMBER_DESCRIPTIONS: tuple[FoxessHapaNumberEntityDescription, ...] = (
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
    FoxessHapaNumberEntityDescription(
        key="fd_soc",
        translation_key="fd_soc",
        name="Force Charge/Discharge SoC",
        native_min_value=10,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        device_class=NumberDeviceClass.BATTERY,
        mode=NumberMode.SLIDER,
        icon="mdi:battery-arrow-down",
        value_attr="fd_soc",
    ),
    FoxessHapaNumberEntityDescription(
        key="fd_pwr",
        translation_key="fd_pwr",
        name="Force Charge/Discharge Power",
        native_min_value=0,
        native_max_value=10500,
        native_step=1,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=NumberDeviceClass.POWER,
        mode=NumberMode.BOX,
        icon="mdi:transmission-tower-export",
        value_attr="fd_pwr",
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
    def _api_field(self) -> str | None:
        """Scheduler extraParam field this entity maps to."""
        return FIELD_MAPPING.get(self.entity_description.value_attr)

    @property
    def _device_range(self) -> tuple[float, float] | None:
        """Device-reported (min, max) for this field, if it reports one."""
        if not self.coordinator.data or not self._api_field:
            return None
        client = self.coordinator.config_entry.runtime_data.client
        return client.property_range(
            self.coordinator.data.get("scheduler_properties"), self._api_field
        )

    @property
    def native_min_value(self) -> float:
        """Minimum accepted by this device, falling back to the description."""
        device_range = self._device_range
        if device_range is None:
            return self.entity_description.native_min_value
        return device_range[0]

    @property
    def native_max_value(self) -> float:
        """Maximum accepted by this device, falling back to the description."""
        device_range = self._device_range
        if device_range is None:
            return self.entity_description.native_max_value
        return device_range[1]

    @property
    def native_value(self) -> float | None:
        """Return the current value from scheduler data."""
        if not self.coordinator.data:
            return None

        groups = self.coordinator.data.get("scheduler_groups")
        if not groups:
            return None

        client = self.coordinator.config_entry.runtime_data.client
        current_idx = client.find_current_period_index(groups)
        if current_idx is None:
            return None

        extra_param = groups[current_idx].get("extraParam", {})
        return extra_param.get(self._api_field)

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

        client = self.coordinator.config_entry.runtime_data.client
        try:
            groups = await client.async_get_schedule_groups(active_only=False)

            api_field = self._api_field
            if not api_field:
                LOGGER.error("Unknown field: %s", self.entity_description.value_attr)
                return

            if not groups:
                # Create a default schedule period if none exists
                # Use minimal_group for base structure, add only our extraParam
                groups = [
                    {
                        **client.minimal_group({}),
                        "extraParam": {api_field: int(value)},
                    }
                ]
            else:
                # Find the current period and only update that one
                current_idx = client.find_current_period_index(groups)
                if current_idx is None:
                    LOGGER.warning(
                        "No schedule period covers the current time, cannot update %s",
                        self.entity_description.key,
                    )
                    return

                # Update only the current period, preserving the other extraParam
                # values on it, and leave every other period untouched.
                groups = [
                    {
                        **client.minimal_group(g),
                        "extraParam": {
                            **g.get("extraParam", {}),
                            api_field: int(value),
                        },
                    }
                    if i == current_idx
                    else client.minimal_group(g)
                    for i, g in enumerate(groups)
                ]

            success = await client.async_set_scheduler(groups, enable=True, pad=False)

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
