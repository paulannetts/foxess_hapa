"""Number platform for foxess_hapa."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import PERCENTAGE, UnitOfPower
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, LOGGER
from .entity import FoxessHapaEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import FoxessHapaDataUpdateCoordinator
    from .data import FoxessHapaConfigEntry


@dataclass(frozen=True, kw_only=True)
class FoxessHapaNumberEntityDescription(NumberEntityDescription):
    """Describes a FoxESS HAPA number entity."""

    # Scheduler extraParam fields this entity writes, all to the same value in
    # a single API call. The first is the one read back as the entity state.
    api_fields: tuple[str, ...]


# Attribute names for the raw fields, matching the schedule sensor and services.
_ATTR_NAMES: dict[str, str] = {
    "minSocOnGrid": "min_soc",
    "fdSoc": "fd_soc",
    "fdPwr": "fd_pwr",
}

# Entity keys removed in favour of target_soc. Their registry entries are
# cleaned up on every setup so they do not linger as "unavailable", which means
# a key listed here must never be reused by a live NUMBER_DESCRIPTIONS entry.
_REMOVED_KEYS: tuple[str, ...] = ("min_soc_on_grid", "fd_soc")

# The min/max below are fallbacks only. Devices report their real limits in the
# scheduler `properties` block -- an H3 allows fdPwr up to 10500 W -- so
# native_min_value/native_max_value prefer those when available.
NUMBER_DESCRIPTIONS: tuple[FoxessHapaNumberEntityDescription, ...] = (
    # minSocOnGrid is the floor in SelfUse/ForceDischarge; fdSoc is the level
    # ForceCharge charges up to and ForceDischarge discharges down to. From the
    # user's side that is one intent -- "get the battery to this SoC and hold
    # it" -- so they are written together rather than left to drift apart.
    FoxessHapaNumberEntityDescription(
        key="target_soc",
        translation_key="target_soc",
        name="Target SoC",
        native_min_value=10,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        device_class=NumberDeviceClass.BATTERY,
        mode=NumberMode.SLIDER,
        icon="mdi:battery-heart-variant",
        api_fields=("minSocOnGrid", "fdSoc"),
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
        api_fields=("fdPwr",),
    ),
)


def _remove_stale_entities(hass: HomeAssistant, entry: FoxessHapaConfigEntry) -> None:
    """Drop registry entries for number entities this integration no longer offers."""
    registry = er.async_get(hass)
    for key in _REMOVED_KEYS:
        entity_id = registry.async_get_entity_id(
            "number", DOMAIN, f"{entry.entry_id}_{key}"
        )
        if entity_id:
            LOGGER.info("Removing superseded entity %s", entity_id)
            registry.async_remove(entity_id)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FoxessHapaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the number platform."""
    # Runs before the data gate so a restart while the API is down still cleans up.
    _remove_stale_entities(hass, entry)

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
    def _api_fields(self) -> tuple[str, ...]:
        """Scheduler extraParam fields this entity maps to."""
        return self.entity_description.api_fields

    @property
    def _device_range(self) -> tuple[float, float] | None:
        """
        Device-reported (min, max) for this entity, if it reports one.

        With several fields the range is their intersection, so a value the
        slider accepts is valid for every field it writes.
        """
        if not self.coordinator.data:
            return None
        client = self.coordinator.config_entry.runtime_data.client
        properties = self.coordinator.data.get("scheduler_properties")
        ranges = [
            r
            for field in self._api_fields
            if (r := client.property_range(properties, field)) is not None
        ]
        if not ranges:
            return None
        return max(r[0] for r in ranges), min(r[1] for r in ranges)

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
    def _current_extra_param(self) -> dict[str, Any] | None:
        """The extraParam block of the schedule period governing now."""
        if not self.coordinator.data:
            return None

        groups = self.coordinator.data.get("scheduler_groups")
        if not groups:
            return None

        client = self.coordinator.config_entry.runtime_data.client
        current_idx = client.find_current_period_index(groups)
        if current_idx is None:
            return None

        return groups[current_idx].get("extraParam", {})

    @property
    def native_value(self) -> float | None:
        """Return the current value from scheduler data."""
        extra_param = self._current_extra_param
        if extra_param is None:
            return None
        return extra_param.get(self._api_fields[0])

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """
        Raw value of each field this entity writes.

        The fields can drift apart when set individually through the FoxESS
        app or the set_slot service; exposing them makes that visible rather
        than hidden behind the single state value.
        """
        if len(self._api_fields) < 2:  # noqa: PLR2004
            return None
        extra_param = self._current_extra_param or {}
        return {
            _ATTR_NAMES.get(field, field): extra_param.get(field)
            for field in self._api_fields
        }

    async def async_set_native_value(self, value: float) -> None:
        """
        Set the new value via the scheduler API.

        Note: FoxESS requires using the scheduler API to change battery settings.
        Individual setting changes may return 'Unsupported Function Code' when
        the mode scheduler is enabled.
        """
        key = self.entity_description.key
        new_params = {field: int(value) for field in self._api_fields}
        LOGGER.info("Setting %s to %s via scheduler API", key, value)

        client = self.coordinator.config_entry.runtime_data.client
        groups = await client.async_get_schedule_groups(active_only=False)

        if not groups:
            # Create a default schedule period if none exists
            # Use minimal_group for base structure, add only our extraParam
            groups = [{**client.minimal_group({}), "extraParam": new_params}]
        else:
            # Find the current period and only update that one
            current_idx = client.find_current_period_index(groups)
            if current_idx is None:
                msg = f"No schedule period covers the current time, cannot set {key}"
                raise HomeAssistantError(msg)

            # Update only the current period, preserving the other extraParam
            # values on it, and leave every other period untouched. All fields
            # go in the one write so they cannot end up half-applied.
            groups = [
                {
                    **client.minimal_group(g),
                    "extraParam": {**g.get("extraParam", {}), **new_params},
                }
                if i == current_idx
                else client.minimal_group(g)
                for i, g in enumerate(groups)
            ]

        success = await client.async_set_scheduler(groups, enable=True, pad=False)
        if not success:
            msg = f"FoxESS API rejected the update to {key}"
            raise HomeAssistantError(msg)

        LOGGER.info("Successfully updated %s to %s", key, value)
        await self.coordinator.async_request_refresh()
