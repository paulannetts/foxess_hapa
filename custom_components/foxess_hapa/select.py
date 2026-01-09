"""Select platform for foxess_hapa."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.select import SelectEntity, SelectEntityDescription

from .const import LOGGER
from .entity import FoxessHapaEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import FoxessHapaDataUpdateCoordinator
    from .data import FoxessHapaConfigEntry


# FoxESS work modes
WORK_MODES = [
    "SelfUse",
    "ForceCharge",
    "ForceDischarge",
    "Backup",
    "FeedInFirst",
]

SELECT_DESCRIPTIONS: tuple[SelectEntityDescription, ...] = (
    SelectEntityDescription(
        key="work_mode",
        translation_key="work_mode",
        name="Work Mode",
        icon="mdi:cog",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: FoxessHapaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the select platform."""
    coordinator = entry.runtime_data.coordinator

    # Only add work mode select if device has battery
    if coordinator.data:
        device_info = coordinator.data.get("device_info")
        if device_info and device_info.has_battery:
            async_add_entities(
                FoxessHapaSelect(
                    coordinator=coordinator,
                    entity_description=description,
                )
                for description in SELECT_DESCRIPTIONS
            )


class FoxessHapaSelect(FoxessHapaEntity, SelectEntity):
    """FoxESS HAPA Select class for work mode."""

    entity_description: SelectEntityDescription
    _attr_options = WORK_MODES

    def __init__(
        self,
        coordinator: FoxessHapaDataUpdateCoordinator,
        entity_description: SelectEntityDescription,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{entity_description.key}"
        )
        self._current_mode: str | None = None

    @property
    def current_option(self) -> str | None:
        """Return the current work mode."""
        # Work mode is stored in scheduler, not in real-time data
        # We track it locally after setting
        return self._current_mode or "SelfUse"

    async def async_select_option(self, option: str) -> None:
        """
        Set the work mode via the scheduler API.

        Note: FoxESS requires using the scheduler API to change work modes.
        """
        if option not in WORK_MODES:
            LOGGER.error("Invalid work mode: %s", option)
            return

        LOGGER.info("Setting work mode to %s via scheduler API", option)

        client = self.coordinator.config_entry.runtime_data.client
        try:
            # Get current scheduler settings
            current_schedule = await client.async_get_scheduler()

            # Get current battery settings for minSoC values
            battery_settings = self.coordinator.data.get("battery_settings")
            min_soc = battery_settings.min_soc if battery_settings else 10
            min_soc_on_grid = (
                battery_settings.min_soc_on_grid if battery_settings else 10
            )

            # Modify the schedule with new work mode
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
                        "workMode": option,
                        "minSoc": min_soc,
                        "minSocOnGrid": min_soc_on_grid,
                    }
                ]
            else:
                # Update existing schedule periods with new work mode
                for group in groups:
                    group["workMode"] = option

            # Apply the updated schedule
            success = await client.async_set_scheduler(groups, enable=True)

            if success:
                LOGGER.info("Successfully set work mode to %s", option)
                self._current_mode = option
                # Refresh coordinator data
                await self.coordinator.async_request_refresh()
            else:
                LOGGER.error("Failed to set work mode to %s", option)

        except Exception as ex:
            LOGGER.exception("Error setting work mode: %s", ex)
            raise
