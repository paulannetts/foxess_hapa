"""Tests for setting up and unloading a config entry inside Home Assistant."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from homeassistant.helpers import entity_registry as er

from custom_components.foxess_hapa.api import (
    FoxessHapaApiClientAuthenticationError,
    FoxessHapaApiClientCommunicationError,
)
from custom_components.foxess_hapa.binary_sensor import BINARY_SENSOR_DESCRIPTIONS
from custom_components.foxess_hapa.const import DOMAIN
from custom_components.foxess_hapa.mock_api import _MOCK_WORK_MODES
from custom_components.foxess_hapa.number import NUMBER_DESCRIPTIONS
from custom_components.foxess_hapa.select import SELECT_DESCRIPTIONS
from custom_components.foxess_hapa.sensor import SENSOR_DESCRIPTIONS

from .conftest import NOON, RecordingClient, entity_id_for, make_entry

if TYPE_CHECKING:
    from freezegun.api import FrozenDateTimeFactory
    from homeassistant.core import HomeAssistant

SERVICES = ("set_schedule", "set_slot", "set_current_period")


def _entities_by_platform(hass: HomeAssistant, entry: Any) -> dict[str, set[str]]:
    """Unique-ID keys of the entry's registered entities, grouped by platform."""
    prefix = f"{entry.entry_id}_"
    found: dict[str, set[str]] = {}
    for reg_entry in er.async_entries_for_config_entry(
        er.async_get(hass), entry.entry_id
    ):
        found.setdefault(reg_entry.domain, set()).add(
            reg_entry.unique_id.removeprefix(prefix)
        )
    return found


async def test_setup_creates_expected_entities(
    hass: HomeAssistant, loaded_entry: Any
) -> None:
    """Every sensor, binary_sensor, number and select is created."""
    assert _entities_by_platform(hass, loaded_entry) == {
        "sensor": {d.key for d in SENSOR_DESCRIPTIONS} | {"schedule_summary"},
        "binary_sensor": {d.key for d in BINARY_SENSOR_DESCRIPTIONS},
        "number": {d.key for d in NUMBER_DESCRIPTIONS},
        "select": {d.key for d in SELECT_DESCRIPTIONS},
    }


async def test_entities_belong_to_the_inverter_device(
    hass: HomeAssistant, loaded_entry: Any
) -> None:
    """Entities hang off one device named after the station."""
    reg_entries = er.async_entries_for_config_entry(
        er.async_get(hass), loaded_entry.entry_id
    )
    assert {e.device_id for e in reg_entries} != {None}
    assert len({e.device_id for e in reg_entries}) == 1


async def test_entity_states_are_sensible(
    hass: HomeAssistant, loaded_entry: Any
) -> None:
    """States reflect the mock's device, real-time data and noon schedule period."""
    client: RecordingClient = loaded_entry.runtime_data.client

    def state(platform: str, key: str) -> Any:
        found = hass.states.get(entity_id_for(hass, platform, loaded_entry, key))
        assert found is not None
        return found

    soc = float(state("sensor", "battery_soc").state)
    assert 0 <= soc <= 100
    assert state("sensor", "battery_soc").attributes["unit_of_measurement"] == "%"
    assert float(state("sensor", "pv_power").state) >= 0

    schedule = state("sensor", "schedule_summary")
    assert schedule.state == "SelfUse (05:30-23:30)"
    assert schedule.attributes["current_period_index"] == 2
    assert schedule.attributes["total_periods"] == 4

    assert state("binary_sensor", "has_battery").state == STATE_ON
    assert state("binary_sensor", "battery_charging").state in (STATE_ON, STATE_OFF)

    # Noon period's extraParam is {"minSocOnGrid": 20, "fdSoc": 20}.
    target_soc = state("number", "target_soc")
    assert float(target_soc.state) == 20
    assert target_soc.attributes["min_soc"] == 20
    assert target_soc.attributes["fd_soc"] == 20
    # Limits come from the device-reported ranges, not the static fallbacks.
    assert target_soc.attributes["min"] == 10
    assert target_soc.attributes["max"] == 100
    assert state("number", "fd_pwr").attributes["max"] == 10500

    work_mode = state("select", "work_mode")
    assert work_mode.state == "SelfUse"
    assert work_mode.attributes["options"] == _MOCK_WORK_MODES

    # Setting up wrote nothing to the inverter.
    assert client.writes == []


async def test_services_registered(hass: HomeAssistant, loaded_entry: Any) -> None:
    """Setting up an entry registers the scheduler services."""
    assert loaded_entry.state is ConfigEntryState.LOADED
    for service in SERVICES:
        assert hass.services.has_service(DOMAIN, service)


async def test_unload_entry(hass: HomeAssistant, loaded_entry: Any) -> None:
    """Unloading the entry unloads it and leaves its entities unavailable."""
    soc_entity = entity_id_for(hass, "sensor", loaded_entry, "battery_soc")

    assert await hass.config_entries.async_unload(loaded_entry.entry_id)
    await hass.async_block_till_done()

    assert loaded_entry.state is ConfigEntryState.NOT_LOADED
    state = hass.states.get(soc_entity)
    assert state is not None
    assert state.state == STATE_UNAVAILABLE


async def test_reload_entry(hass: HomeAssistant, loaded_entry: Any) -> None:
    """The entry can be reloaded, building a fresh client."""
    old_client = loaded_entry.runtime_data.client

    assert await hass.config_entries.async_reload(loaded_entry.entry_id)
    await hass.async_block_till_done()

    assert loaded_entry.state is ConfigEntryState.LOADED
    assert loaded_entry.runtime_data.client is not old_client


async def test_two_entries_load_side_by_side(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    mock_client_class: type[RecordingClient],  # noqa: ARG001
) -> None:
    """Two inverters each get their own client and entities."""
    freezer.move_to(NOON)
    first, second = make_entry("SN0001"), make_entry("SN0002")
    for entry in (first, second):
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert first.state is second.state is ConfigEntryState.LOADED
    assert first.runtime_data.client is not second.runtime_data.client
    assert _entities_by_platform(hass, first) == _entities_by_platform(hass, second)


@pytest.mark.parametrize(
    ("error", "expected_state"),
    [
        (FoxessHapaApiClientCommunicationError("down"), ConfigEntryState.SETUP_RETRY),
        (FoxessHapaApiClientAuthenticationError("bad"), ConfigEntryState.SETUP_ERROR),
    ],
)
async def test_first_refresh_failure(
    hass: HomeAssistant,
    mock_client_class: type[RecordingClient],  # noqa: ARG001
    error: Exception,
    expected_state: ConfigEntryState,
) -> None:
    """API errors on the first poll retry later; bad credentials start reauth."""
    entry = make_entry()
    entry.add_to_hass(hass)

    with patch.object(RecordingClient, "async_get_data", AsyncMock(side_effect=error)):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is expected_state
