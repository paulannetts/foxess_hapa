"""Custom types for foxess_hapa."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration

    from .api import FoxessHapaApiClient
    from .coordinator import FoxessHapaDataUpdateCoordinator


type FoxessHapaConfigEntry = ConfigEntry[FoxessHapaData]


@dataclass
class FoxessHapaData:
    """Data for the FoxESS HAPA integration."""

    client: FoxessHapaApiClient
    coordinator: FoxessHapaDataUpdateCoordinator
    integration: Integration
