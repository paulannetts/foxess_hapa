"""
Custom integration to integrate foxess_hapa with Home Assistant.

For more details about this integration, please refer to
https://github.com/paulannetts/foxess_hapa
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.const import Platform
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.loader import async_get_loaded_integration

from .api import FoxessHapaApiClient
from .const import CONF_API_KEY, CONF_DEVICE_SERIAL_NUMBER, DOMAIN, LOGGER
from .coordinator import FoxessHapaDataUpdateCoordinator
from .data import FoxessHapaData

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import FoxessHapaConfigEntry

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SELECT,
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FoxessHapaConfigEntry,
) -> bool:
    """Set up this integration using UI."""
    coordinator = FoxessHapaDataUpdateCoordinator(
        hass=hass,
        logger=LOGGER,
        name=DOMAIN,
        update_interval=timedelta(hours=1),
    )
    entry.runtime_data = FoxessHapaData(
        client=FoxessHapaApiClient(
            device_serial_number=entry.data[CONF_DEVICE_SERIAL_NUMBER],
            api_key=entry.data[CONF_API_KEY],
            session=async_get_clientsession(hass),
        ),
        integration=async_get_loaded_integration(hass, entry.domain),
        coordinator=coordinator,
    )

    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: FoxessHapaConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(
    hass: HomeAssistant,
    entry: FoxessHapaConfigEntry,
) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
