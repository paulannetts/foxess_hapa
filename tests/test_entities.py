"""
Tests for the number and select entities' writes, inside Home Assistant.

Both act on the schedule period governing now: at the frozen noon that is
device group 2 of the mock schedule (05:30-23:30 SelfUse, minSocOnGrid/fdSoc 20).
"""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any

import pytest
from homeassistant.components.number import ATTR_VALUE, SERVICE_SET_VALUE
from homeassistant.components.select import ATTR_OPTION, SERVICE_SELECT_OPTION
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from .conftest import INITIAL_GROUPS, RecordingClient, entity_id_for, with_group

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


async def _set_number(hass: HomeAssistant, entry: Any, key: str, value: float) -> None:
    await hass.services.async_call(
        "number",
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: entity_id_for(hass, "number", entry, key), ATTR_VALUE: value},
        blocking=True,
    )


async def _select(hass: HomeAssistant, entry: Any, option: str) -> None:
    await hass.services.async_call(
        "select",
        SERVICE_SELECT_OPTION,
        {
            ATTR_ENTITY_ID: entity_id_for(hass, "select", entry, "work_mode"),
            ATTR_OPTION: option,
        },
        blocking=True,
    )


# --- Target SoC / Force power numbers ----------------------------------------


async def test_target_soc_writes_both_fields(
    hass: HomeAssistant, loaded_entry: Any, client: RecordingClient
) -> None:
    """Target SoC sets minSocOnGrid and fdSoc together on the current period only."""
    await _set_number(hass, loaded_entry, "target_soc", 65)

    assert client.writes == [
        {
            "groups": with_group(2, extraParam={"minSocOnGrid": 65, "fdSoc": 65}),
            "enable": True,
            "pad": False,
        }
    ]


async def test_target_soc_keeps_other_extra_params(
    hass: HomeAssistant, loaded_entry: Any, client: RecordingClient
) -> None:
    """Other extraParam values on the current period survive the write."""
    client._schedule_groups[2]["extraParam"]["fdPwr"] = 4000
    client._schedule_groups[2]["extraParam"]["maxSoc"] = 95

    await _set_number(hass, loaded_entry, "target_soc", 50)

    assert client.writes[0]["groups"][2]["extraParam"] == {
        "minSocOnGrid": 50,
        "fdSoc": 50,
        "fdPwr": 4000,
        "maxSoc": 95,
    }


async def test_force_power_writes_fd_pwr(
    hass: HomeAssistant, loaded_entry: Any, client: RecordingClient
) -> None:
    """Force Charge/Discharge Power writes fdPwr alone."""
    await _set_number(hass, loaded_entry, "fd_pwr", 7500)

    assert client.writes[0]["groups"] == with_group(2, extraParam={"fdPwr": 7500})


async def test_target_soc_outside_device_range_refused(
    hass: HomeAssistant, loaded_entry: Any, client: RecordingClient
) -> None:
    """The slider's limits come from the device, so 5% is refused (min is 10)."""
    with pytest.raises(ServiceValidationError):
        await _set_number(hass, loaded_entry, "target_soc", 5)
    assert client.writes == []


async def test_target_soc_without_current_period(
    hass: HomeAssistant, loaded_entry: Any, client: RecordingClient
) -> None:
    """If no period covers now, the write is refused rather than guessed."""
    client._schedule_groups = copy.deepcopy(INITIAL_GROUPS[:2])

    with pytest.raises(HomeAssistantError, match="No schedule period"):
        await _set_number(hass, loaded_entry, "target_soc", 50)
    assert client.writes == []


async def test_target_soc_creates_period_on_empty_schedule(
    hass: HomeAssistant, loaded_entry: Any, client: RecordingClient
) -> None:
    """With no schedule at all, one all-day SelfUse period is created."""
    client._schedule_groups = []

    await _set_number(hass, loaded_entry, "target_soc", 40)

    assert client.writes[0]["groups"] == [
        {
            "enable": 1,
            "startHour": 0,
            "startMinute": 0,
            "endHour": 23,
            "endMinute": 59,
            "workMode": "SelfUse",
            "extraParam": {"minSocOnGrid": 40, "fdSoc": 40},
        }
    ]


# --- Work mode select --------------------------------------------------------


async def test_work_mode_writes_current_period(
    hass: HomeAssistant, loaded_entry: Any, client: RecordingClient
) -> None:
    """Selecting a work mode changes only the current period's workMode."""
    await _select(hass, loaded_entry, "ForceCharge")

    assert client.writes == [
        {
            "groups": with_group(2, workMode="ForceCharge"),
            "enable": True,
            "pad": False,
        }
    ]


async def test_work_mode_not_offered_by_device_refused(
    hass: HomeAssistant, loaded_entry: Any, client: RecordingClient
) -> None:
    """A mode outside the device's enumList is refused by the select."""
    with pytest.raises(ServiceValidationError):
        await _select(hass, loaded_entry, "PeakShaving")
    assert client.writes == []


async def test_work_mode_creates_period_on_empty_schedule(
    hass: HomeAssistant, loaded_entry: Any, client: RecordingClient
) -> None:
    """With no schedule at all, one all-day period in the chosen mode is created."""
    client._schedule_groups = []

    await _select(hass, loaded_entry, "Backup")

    assert client.writes[0]["groups"] == [
        {
            "enable": 1,
            "startHour": 0,
            "startMinute": 0,
            "endHour": 23,
            "endMinute": 59,
            "workMode": "Backup",
            "extraParam": {"minSocOnGrid": 10},
        }
    ]
