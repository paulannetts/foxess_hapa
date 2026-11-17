"""Shared helpers for FoxESS HAPA tests."""

from __future__ import annotations

import copy
from datetime import datetime
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant.common import MockConfigEntry

from custom_components.foxess_hapa import api
from custom_components.foxess_hapa.const import (
    CONF_API_KEY,
    CONF_DEVICE_SERIAL_NUMBER,
    DOMAIN,
)
from custom_components.foxess_hapa.mock_api import MockFoxessHapaApiClient

if TYPE_CHECKING:
    from collections.abc import Generator

    from freezegun.api import FrozenDateTimeFactory
    from homeassistant.core import HomeAssistant


def group(
    start: str,
    end: str,
    work_mode: str = "SelfUse",
    *,
    enable: int = 1,
    extra_param: dict[str, Any] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Build a scheduler group as the FoxESS API returns it, from HH:MM times."""
    start_hour, start_minute = (int(x) for x in start.split(":"))
    end_hour, end_minute = (int(x) for x in end.split(":"))
    result: dict[str, Any] = {
        "enable": enable,
        "startHour": start_hour,
        "startMinute": start_minute,
        "endHour": end_hour,
        "endMinute": end_minute,
        "workMode": work_mode,
        **extra,
    }
    if extra_param is not None:
        result["extraParam"] = extra_param
    return result


@pytest.fixture
def freeze_clock(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Return a setter that fixes the local time seen by api.py to HH:MM."""

    def _set(hh_mm: str) -> None:
        hour, minute = (int(x) for x in hh_mm.split(":"))
        fixed = datetime(2026, 1, 15, hour, minute).astimezone()

        class _FrozenDatetime(datetime):
            @classmethod
            def now(cls, tz: Any = None) -> datetime:  # noqa: ARG003
                return fixed

        monkeypatch.setattr(api, "datetime", _FrozenDatetime)

    return _set


# --- running inside Home Assistant -------------------------------------------
#
# The fixtures below set the integration up in a test Home Assistant instance
# (the `hass` fixture from pytest-homeassistant) against RecordingClient, the
# mock_api fake with every scheduler write captured.

SERIAL = "SN0001"

# Local time the HA tests run at. 12:00 falls in the mock schedule's
# 05:30-23:30 SelfUse period (device group 2), the "current period".
NOON = "2026-01-15 12:00:00"


# The mock_api default schedule, as RecordingClient starts out.
INITIAL_GROUPS: list[dict[str, Any]] = [
    {
        "enable": 1,
        "startHour": 0,
        "startMinute": 0,
        "endHour": 3,
        "endMinute": 30,
        "workMode": "ForceCharge",
        "extraParam": {"minSocOnGrid": 10, "maxSoc": 90},
    },
    {
        "enable": 1,
        "startHour": 3,
        "startMinute": 30,
        "endHour": 5,
        "endMinute": 30,
        "workMode": "ForceCharge",
        "extraParam": {"minSocOnGrid": 10, "maxSoc": 90},
    },
    {
        "enable": 1,
        "startHour": 5,
        "startMinute": 30,
        "endHour": 23,
        "endMinute": 30,
        "workMode": "SelfUse",
        "extraParam": {"minSocOnGrid": 20, "fdSoc": 20},
    },
    {
        "enable": 1,
        "startHour": 23,
        "startMinute": 0,
        "endHour": 23,
        "endMinute": 59,
        "workMode": "SelfUse",
        "extraParam": {"minSocOnGrid": 20},
    },
]


def with_group(index: int, **changes: Any) -> list[dict[str, Any]]:
    """INITIAL_GROUPS with one group changed; `extraParam` is merged, not replaced."""
    groups = copy.deepcopy(INITIAL_GROUPS)
    extra = changes.pop("extraParam", None)
    groups[index].update(changes)
    if extra is not None:
        groups[index]["extraParam"] = {**groups[index]["extraParam"], **extra}
    return groups


class RecordingClient(MockFoxessHapaApiClient):
    """MockFoxessHapaApiClient that records every async_set_scheduler call."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Start with no recorded writes."""
        super().__init__(*args, **kwargs)
        self.writes: list[dict[str, Any]] = []

    async def async_set_scheduler(
        self,
        periods: list[dict[str, Any]],
        *,
        enable: bool = True,
        pad: bool = True,
    ) -> bool:
        """Record the exact payload, then store it like the mock does."""
        self.writes.append(
            {"groups": copy.deepcopy(periods), "enable": enable, "pad": pad}
        )
        return await super().async_set_scheduler(periods, enable=enable, pad=pad)


@pytest.fixture
def mock_client_class() -> Generator[type[RecordingClient]]:
    """Make async_setup_entry build a RecordingClient instead of the real one."""
    with patch(
        "custom_components.foxess_hapa.FoxessHapaApiClient", RecordingClient
    ) as client_class:
        yield client_class


def make_entry(serial: str = SERIAL) -> MockConfigEntry:
    """Build a config entry for one inverter, keyed by its serial number."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=f"Inverter {serial}",
        unique_id=serial,
        data={CONF_DEVICE_SERIAL_NUMBER: serial, CONF_API_KEY: "test-key"},
    )


async def setup_entry(hass: HomeAssistant, entry: MockConfigEntry) -> RecordingClient:
    """Add and set up an entry; return the client it is talking to."""
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    return entry.runtime_data.client


@pytest.fixture
async def loaded_entry(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    mock_client_class: type[RecordingClient],  # noqa: ARG001
) -> MockConfigEntry:
    """One inverter set up at noon, backed by a RecordingClient."""
    freezer.move_to(NOON)
    entry = make_entry()
    await setup_entry(hass, entry)
    return entry


@pytest.fixture
def client(loaded_entry: MockConfigEntry) -> RecordingClient:
    """Return the RecordingClient behind the loaded inverter."""
    return loaded_entry.runtime_data.client


def entity_id_for(hass: HomeAssistant, platform: str, entry: Any, key: str) -> str:
    """Look up an entity by the `<entry_id>_<key>` unique ID the platforms use."""
    entity_id = er.async_get(hass).async_get_entity_id(
        platform, DOMAIN, f"{entry.entry_id}_{key}"
    )
    assert entity_id is not None, f"no {platform} entity with key {key!r}"
    return entity_id


def device_id_for(hass: HomeAssistant, serial: str = SERIAL) -> str:
    """Device registry ID of the inverter with this serial number."""
    entry = hass.config_entries.async_entry_for_domain_unique_id(DOMAIN, serial)
    assert entry is not None
    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, serial), entry.entry_id
    )
    assert device is not None
    return device.id
