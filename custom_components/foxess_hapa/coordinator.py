"""DataUpdateCoordinator for foxess_hapa."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    FoxessHapaApiClientAuthenticationError,
    FoxessHapaApiClientError,
)

if TYPE_CHECKING:
    from .data import FoxessHapaConfigEntry


class FoxessHapaDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching data from the FoxESS API."""

    config_entry: FoxessHapaConfigEntry

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via the FoxESS API."""
        try:
            return await self.config_entry.runtime_data.client.async_get_data()
        except FoxessHapaApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except FoxessHapaApiClientError as exception:
            raise UpdateFailed(exception) from exception
