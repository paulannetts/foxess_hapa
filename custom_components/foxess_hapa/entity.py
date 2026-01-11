"""FoxessHapaEntity class."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN
from .coordinator import FoxessHapaDataUpdateCoordinator


class FoxessHapaEntity(CoordinatorEntity[FoxessHapaDataUpdateCoordinator]):
    """Base entity for FoxESS HAPA integration."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(self, coordinator: FoxessHapaDataUpdateCoordinator) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._attr_unique_id = coordinator.config_entry.entry_id

        # Get device info from coordinator data if available
        device_info = None
        if coordinator.data:
            device_info = coordinator.data.get("device_info")

        if device_info:
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, device_info.device_sn)},
                name=device_info.station_name or f"FoxESS {device_info.device_sn}",
                manufacturer="FoxESS",
                model=device_info.device_type,
                sw_version=device_info.master_version,
            )
        else:
            # Fallback to config entry based device info
            device_sn = coordinator.config_entry.data.get(
                "device_serial_number", "Unknown"
            )
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
                name=f"FoxESS {device_sn}",
                manufacturer="FoxESS",
            )
