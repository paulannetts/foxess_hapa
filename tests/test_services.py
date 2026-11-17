"""
End-to-end tests for the scheduler services inside Home Assistant.

These services rewrite the inverter's schedule, so each test asserts the exact
`groups` payload handed to async_set_scheduler. The RecordingClient starts with
the mock_api schedule and the clock is frozen at noon:

    group 0  00:00-03:30  ForceCharge  {minSocOnGrid: 10, maxSoc: 90}
    group 1  03:30-05:30  ForceCharge  {minSocOnGrid: 10, maxSoc: 90}
    group 2  05:30-23:30  SelfUse      {minSocOnGrid: 20, fdSoc: 20}  <- noon
    group 3  23:00-23:59  SelfUse      {minSocOnGrid: 20}
"""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any

import pytest
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr

from custom_components.foxess_hapa.const import DOMAIN

from .conftest import (
    INITIAL_GROUPS,
    NOON,
    RecordingClient,
    device_id_for,
    entity_id_for,
    make_entry,
    setup_entry,
    with_group,
)

if TYPE_CHECKING:
    from freezegun.api import FrozenDateTimeFactory
    from homeassistant.core import HomeAssistant


@pytest.fixture
def target(hass: HomeAssistant, loaded_entry: Any) -> dict[str, Any]:  # noqa: ARG001
    """Service target naming the loaded inverter by device."""
    return {"device_id": device_id_for(hass)}


async def _call(
    hass: HomeAssistant,
    service: str,
    data: dict[str, Any],
    target: dict[str, Any] | None = None,
) -> None:
    await hass.services.async_call(DOMAIN, service, data, target=target, blocking=True)


async def test_initial_groups_match_mock(client: RecordingClient) -> None:
    """Guard: the expectations below assume the mock's default schedule."""
    assert client._schedule_groups == INITIAL_GROUPS


# --- set_schedule ------------------------------------------------------------


async def test_set_schedule_payload(
    hass: HomeAssistant, client: RecordingClient, target: dict[str, Any]
) -> None:
    """Periods become groups with API field names, padded as a full replace."""
    await _call(
        hass,
        "set_schedule",
        {
            "periods": [
                {
                    "start_time": "00:30",
                    "end_time": "04:30",
                    "work_mode": "ForceCharge",
                    "fd_soc": 95,
                    "fd_pwr": 6000,
                    "max_soc": 100,
                },
                {
                    "start_time": "16:00",
                    "end_time": "19:00",
                    "work_mode": "ForceDischarge",
                    "min_soc": 30,
                    "enabled": False,
                },
                {"start_time": "19:00", "end_time": "23:59", "work_mode": "SelfUse"},
            ]
        },
        target,
    )

    assert client.writes == [
        {
            "groups": [
                {
                    "enable": 1,
                    "startHour": 0,
                    "startMinute": 30,
                    "endHour": 4,
                    "endMinute": 30,
                    "workMode": "ForceCharge",
                    "extraParam": {"maxSoc": 100, "fdSoc": 95, "fdPwr": 6000},
                },
                {
                    "enable": 0,
                    "startHour": 16,
                    "startMinute": 0,
                    "endHour": 19,
                    "endMinute": 0,
                    "workMode": "ForceDischarge",
                    "extraParam": {"minSocOnGrid": 30},
                },
                {
                    "enable": 1,
                    "startHour": 19,
                    "startMinute": 0,
                    "endHour": 23,
                    "endMinute": 59,
                    "workMode": "SelfUse",
                },
            ],
            "enable": True,
            "pad": True,
        }
    ]


async def test_set_schedule_target_soc_and_aliases(
    hass: HomeAssistant, client: RecordingClient, target: dict[str, Any]
) -> None:
    """target_soc expands to minSocOnGrid + fdSoc; deprecated names still map."""
    await _call(
        hass,
        "set_schedule",
        {
            "periods": [
                {
                    "start_time": "00:00",
                    "end_time": "05:00",
                    "work_mode": "ForceCharge",
                    "target_soc": 80,
                    "charge_power": 4000,
                },
                {
                    "start_time": "05:00",
                    "end_time": "23:59",
                    "work_mode": "SelfUse",
                    "charge_to_soc": 25,
                },
            ]
        },
        target,
    )

    groups = client.writes[0]["groups"]
    assert groups[0]["extraParam"] == {
        "minSocOnGrid": 80,
        "fdSoc": 80,
        "fdPwr": 4000,
    }
    assert groups[1]["extraParam"] == {"fdSoc": 25}


async def test_set_schedule_refreshes_entities(
    hass: HomeAssistant,
    loaded_entry: Any,
    target: dict[str, Any],
    freezer: FrozenDateTimeFactory,
) -> None:
    """After a write the coordinator refreshes and entities show the new period."""
    await _call(
        hass,
        "set_schedule",
        {
            "periods": [
                {
                    "start_time": "00:00",
                    "end_time": "23:59",
                    "work_mode": "Feedin",
                    "target_soc": 40,
                }
            ]
        },
        target,
    )
    # The refresh request is debounced; let it run.
    freezer.tick(15)
    await hass.async_block_till_done()

    select = hass.states.get(entity_id_for(hass, "select", loaded_entry, "work_mode"))
    number = hass.states.get(entity_id_for(hass, "number", loaded_entry, "target_soc"))
    assert select is not None
    assert number is not None
    assert select.state == "Feedin"
    assert float(number.state) == 40


# --- set_slot ----------------------------------------------------------------


async def test_set_slot_payload(
    hass: HomeAssistant, client: RecordingClient, target: dict[str, Any]
) -> None:
    """Only the addressed slot changes; the full list goes back unpadded."""
    await _call(
        hass,
        "set_slot",
        {
            "slot": 1,
            "start_time": "03:00",
            "end_time": "06:15",
            "work_mode": "ForceDischarge",
            "fd_pwr": 3000,
        },
        target,
    )

    assert client.writes == [
        {
            "groups": with_group(
                1,
                startHour=3,
                startMinute=0,
                endHour=6,
                endMinute=15,
                workMode="ForceDischarge",
                extraParam={"fdPwr": 3000},
            ),
            "enable": True,
            "pad": False,
        }
    ]


async def test_set_slot_target_soc_and_aliases(
    hass: HomeAssistant, client: RecordingClient, target: dict[str, Any]
) -> None:
    """target_soc and the deprecated aliases reach the slot's extraParam."""
    await _call(
        hass,
        "set_slot",
        {"slot": 0, "target_soc": 85, "charge_power": 5000},
        target,
    )
    await _call(hass, "set_slot", {"slot": 3, "charge_to_soc": 15}, target)

    assert client.writes[0]["groups"] == with_group(
        0, extraParam={"minSocOnGrid": 85, "fdSoc": 85, "fdPwr": 5000}
    )
    # The second write starts from what the first one stored.
    expected = with_group(
        0, extraParam={"minSocOnGrid": 85, "fdSoc": 85, "fdPwr": 5000}
    )
    expected[3]["extraParam"] = {"minSocOnGrid": 20, "fdSoc": 15}
    assert client.writes[1]["groups"] == expected


async def test_set_slot_disable(
    hass: HomeAssistant, client: RecordingClient, target: dict[str, Any]
) -> None:
    """enabled: false clears the slot's enable flag and nothing else."""
    await _call(hass, "set_slot", {"slot": 2, "enabled": False}, target)

    assert client.writes[0]["groups"] == with_group(2, enable=0)


async def test_set_slot_addresses_active_periods(
    hass: HomeAssistant, client: RecordingClient, target: dict[str, Any]
) -> None:
    """Slot numbers skip disabled groups, but those groups are still written back."""
    disabled = {
        "enable": 0,
        "startHour": 0,
        "startMinute": 0,
        "endHour": 0,
        "endMinute": 0,
        "workMode": "SelfUse",
    }
    client._schedule_groups = [disabled, *copy.deepcopy(INITIAL_GROUPS)]

    await _call(hass, "set_slot", {"slot": 0, "work_mode": "Backup"}, target)

    expected = [disabled, *copy.deepcopy(INITIAL_GROUPS)]
    expected[1]["workMode"] = "Backup"
    assert client.writes[0]["groups"] == expected


async def test_set_slot_out_of_range(
    hass: HomeAssistant, client: RecordingClient, target: dict[str, Any]
) -> None:
    """A slot past the active periods is refused without writing."""
    with pytest.raises(ServiceValidationError, match="Slot 5 does not exist"):
        await _call(hass, "set_slot", {"slot": 5, "work_mode": "SelfUse"}, target)
    assert client.writes == []


# --- set_current_period ------------------------------------------------------


async def test_set_current_period_payload(
    hass: HomeAssistant, client: RecordingClient, target: dict[str, Any]
) -> None:
    """Work mode and SoC land together on the period governing now."""
    await _call(
        hass,
        "set_current_period",
        {"work_mode": "ForceDischarge", "target_soc": 30, "fd_pwr": 5000},
        target,
    )

    assert client.writes == [
        {
            "groups": with_group(
                2,
                workMode="ForceDischarge",
                extraParam={"minSocOnGrid": 30, "fdSoc": 30, "fdPwr": 5000},
            ),
            "enable": True,
            "pad": False,
        }
    ]


async def test_set_current_period_follows_clock(
    hass: HomeAssistant,
    client: RecordingClient,
    target: dict[str, Any],
    freezer: FrozenDateTimeFactory,
) -> None:
    """At 04:00 the current period is group 1."""
    freezer.move_to("2026-01-15 04:00:00")

    await _call(hass, "set_current_period", {"max_soc": 95}, target)

    assert client.writes[0]["groups"] == with_group(1, extraParam={"maxSoc": 95})


async def test_set_current_period_nothing_to_set(
    hass: HomeAssistant, client: RecordingClient, target: dict[str, Any]
) -> None:
    """A call with no fields is refused."""
    with pytest.raises(ServiceValidationError, match="Nothing to set"):
        await _call(hass, "set_current_period", {}, target)
    assert client.writes == []


async def test_set_current_period_no_period_now(
    hass: HomeAssistant, client: RecordingClient, target: dict[str, Any]
) -> None:
    """If no period covers now, nothing is written."""
    client._schedule_groups = copy.deepcopy(INITIAL_GROUPS[:2])

    with pytest.raises(ServiceValidationError, match="No schedule period"):
        await _call(hass, "set_current_period", {"work_mode": "SelfUse"}, target)
    assert client.writes == []


# --- validation against the device -------------------------------------------


@pytest.mark.parametrize(
    ("service", "data", "message"),
    [
        (
            "set_current_period",
            {"target_soc": 50, "min_soc": 40},
            "cannot be combined with min_soc",
        ),
        ("set_current_period", {"work_mode": "PeakShaving"}, "not supported"),
        # The device reports SoC fields as 10-100, tighter than the schema's 0-100.
        ("set_current_period", {"target_soc": 5}, "between 10 and 100"),
        ("set_slot", {"slot": 0, "fd_pwr": 20000}, "between 0 and 10500"),
        (
            "set_schedule",
            {
                "periods": [
                    {
                        "start_time": "00:00",
                        "end_time": "23:59",
                        "work_mode": "SelfUse",
                        "min_soc": 5,
                    }
                ]
            },
            "between 10 and 100",
        ),
        (
            "set_schedule",
            {
                "periods": [
                    {"start_time": "25:00", "end_time": "23:59", "work_mode": "SelfUse"}
                ]
            },
            "out of range",
        ),
    ],
)
async def test_invalid_input_is_refused(  # noqa: PLR0913, PLR0917
    hass: HomeAssistant,
    client: RecordingClient,
    target: dict[str, Any],
    service: str,
    data: dict[str, Any],
    message: str,
) -> None:
    """Bad input is refused before anything is written to the inverter."""
    with pytest.raises(ServiceValidationError, match=message):
        await _call(hass, service, data, target)
    assert client.writes == []


async def test_write_failure_is_reported(
    hass: HomeAssistant, client: RecordingClient, target: dict[str, Any]
) -> None:
    """An API error during the write surfaces as a HomeAssistantError."""

    async def fail(*_args: Any, **_kwargs: Any) -> bool:
        msg = "boom"
        raise RuntimeError(msg)

    client.async_set_scheduler = fail  # type: ignore[method-assign]

    with pytest.raises(Exception, match="Failed to update current period: boom"):
        await _call(hass, "set_current_period", {"work_mode": "Backup"}, target)


# --- device targeting --------------------------------------------------------


@pytest.fixture
async def two_inverters(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    mock_client_class: type[RecordingClient],  # noqa: ARG001
) -> tuple[RecordingClient, RecordingClient]:
    """Two inverters loaded side by side."""
    freezer.move_to(NOON)
    first = await setup_entry(hass, make_entry("SN0001"))
    second = await setup_entry(hass, make_entry("SN0002"))
    return first, second


async def test_target_device_picks_that_inverter(
    hass: HomeAssistant, two_inverters: tuple[RecordingClient, RecordingClient]
) -> None:
    """Targeting one device writes to that inverter only."""
    first, second = two_inverters

    await _call(
        hass,
        "set_current_period",
        {"work_mode": "Backup"},
        {"device_id": device_id_for(hass, "SN0002")},
    )

    assert first.writes == []
    assert len(second.writes) == 1


async def test_target_entity_resolves_its_inverter(
    hass: HomeAssistant, two_inverters: tuple[RecordingClient, RecordingClient]
) -> None:
    """Targeting one of an inverter's entities picks that inverter."""
    first, second = two_inverters
    entry = hass.config_entries.async_entry_for_domain_unique_id(DOMAIN, "SN0001")

    await _call(
        hass,
        "set_current_period",
        {"work_mode": "Backup"},
        {"entity_id": entity_id_for(hass, "select", entry, "work_mode")},
    )

    assert len(first.writes) == 1
    assert second.writes == []


async def test_target_area_with_one_inverter(
    hass: HomeAssistant, two_inverters: tuple[RecordingClient, RecordingClient]
) -> None:
    """An area holding exactly one inverter resolves to it."""
    first, second = two_inverters
    garage = ar.async_get(hass).async_create("Garage")
    dr.async_get(hass).async_update_device(
        device_id_for(hass, "SN0001"), area_id=garage.id
    )

    await _call(
        hass, "set_current_period", {"work_mode": "Backup"}, {"area_id": garage.id}
    )

    assert len(first.writes) == 1
    assert second.writes == []


async def test_several_inverters_refused(
    hass: HomeAssistant, two_inverters: tuple[RecordingClient, RecordingClient]
) -> None:
    """Targeting both inverters is refused rather than fanning the write out."""
    first, second = two_inverters

    with pytest.raises(ServiceValidationError, match="2 FoxESS devices targeted"):
        await _call(
            hass,
            "set_current_period",
            {"work_mode": "Backup"},
            {
                "device_id": [
                    device_id_for(hass, "SN0001"),
                    device_id_for(hass, "SN0002"),
                ]
            },
        )

    assert first.writes == second.writes == []


@pytest.mark.parametrize(
    "target",
    [
        None,
        {"device_id": []},
        {"entity_id": "sensor.not_a_foxess_entity"},
    ],
)
async def test_no_inverter_refused(
    hass: HomeAssistant,
    client: RecordingClient,
    target: dict[str, Any] | None,
) -> None:
    """A call that resolves to no inverter is refused."""
    with pytest.raises(ServiceValidationError, match="No FoxESS device targeted"):
        await _call(hass, "set_current_period", {"work_mode": "Backup"}, target)
    assert client.writes == []


async def test_deprecated_config_entry_id_still_works(
    hass: HomeAssistant, loaded_entry: Any, client: RecordingClient
) -> None:
    """The pre-target config_entry_id field still selects the inverter."""
    await _call(
        hass,
        "set_current_period",
        {"config_entry_id": loaded_entry.entry_id, "work_mode": "Backup"},
    )

    assert client.writes[0]["groups"] == with_group(2, workMode="Backup")


async def test_config_entry_id_of_unknown_entry(
    hass: HomeAssistant, client: RecordingClient
) -> None:
    """An unknown config_entry_id is refused."""
    with pytest.raises(ServiceValidationError, match="not found"):
        await _call(
            hass,
            "set_current_period",
            {"config_entry_id": "nope", "work_mode": "Backup"},
        )
    assert client.writes == []
