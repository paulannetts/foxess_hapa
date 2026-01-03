"""Custom types for ha_test01."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration

    from .api import HaTest01ApiClient
    from .coordinator import BlueprintDataUpdateCoordinator


type HaTest01ConfigEntry = ConfigEntry[HaTest01Data]


@dataclass
class HaTest01Data:
    """Data for the Blueprint integration."""

    client: HaTest01ApiClient
    coordinator: BlueprintDataUpdateCoordinator
    integration: Integration
