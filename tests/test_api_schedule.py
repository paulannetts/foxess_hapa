"""Tests for the scheduler helpers on FoxessHapaApiClient."""

from __future__ import annotations

import asyncio
import copy
from typing import Any
from unittest.mock import AsyncMock

import pytest

from custom_components.foxess_hapa.api import (
    DEFAULT_WORK_MODE_OPTIONS,
    FoxessHapaApiClient,
)

from .conftest import group

Client = FoxessHapaApiClient
CATCH_ALL = group("00:00", "23:59")


# --- active groups -----------------------------------------------------------


@pytest.mark.parametrize(
    ("grp", "expected"),
    [
        (group("06:00", "09:00"), True),
        (group("06:00", "09:00", enable=0), False),
        (group("00:00", "00:00"), False),  # zero-duration placeholder
        (group("05:30", "05:30"), False),
        ({"startHour": 1, "startMinute": 0, "endHour": 2, "endMinute": 0}, True),
    ],
)
def test_is_active_group(grp: dict[str, Any], expected: bool) -> None:
    """Disabled and zero-duration groups are inactive; missing enable means on."""
    assert Client.is_active_group(grp) is expected


def test_active_group_indices_map_positions_to_full_list() -> None:
    """Active-period positions map back to indices in the device's full list."""
    groups = [
        group("00:00", "00:00", enable=0),
        group("01:00", "02:00"),
        group("00:00", "00:00"),
        group("03:00", "04:00"),
    ]
    assert Client.active_group_indices(groups) == [1, 3]
    assert Client._filter_active_groups(groups) == [groups[1], groups[3]]


# --- windows and catch-all ---------------------------------------------------


def test_group_window_in_minutes() -> None:
    """Group windows are minutes past midnight."""
    assert Client.group_window(group("01:30", "22:15")) == (90, 1335)


def test_group_window_defaults_to_full_day() -> None:
    """Missing times default to a 00:00-23:59 window."""
    assert Client.group_window({}) == (0, 1439)


def test_is_catch_all() -> None:
    """Only an exact 00:00-23:59 group is the catch-all."""
    assert Client.is_catch_all(CATCH_ALL)
    assert not Client.is_catch_all(group("00:00", "23:58"))
    assert not Client.is_catch_all(group("00:01", "23:59"))


# --- current period ----------------------------------------------------------


@pytest.mark.parametrize(
    ("now", "groups", "expected"),
    [
        # A specific period wins over the overlapping catch-all.
        ("07:00", [CATCH_ALL, group("06:00", "09:00")], 1),
        # Outside every specific period the catch-all governs.
        ("12:00", [CATCH_ALL, group("06:00", "09:00")], 0),
        # Start and end minutes are both inclusive.
        ("06:00", [CATCH_ALL, group("06:00", "09:00")], 1),
        ("09:00", [CATCH_ALL, group("06:00", "09:00")], 1),
        ("09:01", [CATCH_ALL, group("06:00", "09:00")], 0),
        # Overlapping specific periods: the narrowest wins.
        ("07:30", [group("06:00", "12:00"), group("07:00", "08:00")], 1),
        # Equal widths: the earliest index wins.
        ("07:30", [group("07:00", "08:00"), group("07:00", "08:00")], 0),
        # Periods crossing midnight match on both sides of it.
        ("23:30", [CATCH_ALL, group("23:00", "05:00")], 1),
        ("03:00", [CATCH_ALL, group("23:00", "05:00")], 1),
        ("12:00", [CATCH_ALL, group("23:00", "05:00")], 0),
        # A midnight-crossing period is narrower than a long day period.
        ("23:30", [group("12:00", "23:59"), group("23:00", "01:00")], 1),
        # Disabled and zero-duration groups never govern.
        ("07:00", [CATCH_ALL, group("06:00", "09:00", enable=0)], 0),
        ("00:00", [group("00:00", "00:00"), CATCH_ALL], 1),
        # Nothing covers the time.
        ("12:00", [group("06:00", "09:00")], None),
        ("12:00", [], None),
    ],
)
def test_find_current_period_index(
    freeze_clock: Any,
    now: str,
    groups: list[dict[str, Any]],
    expected: int | None,
) -> None:
    """The period in force is chosen as the docstring describes."""
    freeze_clock(now)
    assert Client.find_current_period_index(groups) == expected


# --- building writes ---------------------------------------------------------


def test_minimal_group_keeps_only_write_fields() -> None:
    """Read-only fields are dropped; extraParam is kept when present."""
    full = group(
        "06:00",
        "09:00",
        "ForceCharge",
        extra_param={"fdSoc": 90},
        properties={"ignored": True},
    )
    assert Client.minimal_group(full) == {
        "enable": 1,
        "startHour": 6,
        "startMinute": 0,
        "endHour": 9,
        "endMinute": 0,
        "workMode": "ForceCharge",
        "extraParam": {"fdSoc": 90},
    }


def test_minimal_group_defaults() -> None:
    """An empty group becomes an enabled full-day SelfUse period."""
    assert Client.minimal_group({}) == {
        "enable": 1,
        "startHour": 0,
        "startMinute": 0,
        "endHour": 23,
        "endMinute": 59,
        "workMode": "SelfUse",
    }


def test_update_group_changes_only_the_target() -> None:
    """Only the target group changes; others go back as the device holds them."""
    groups = [
        group("00:00", "23:59", extra_param={"minSocOnGrid": 10}, extra="x"),
        group(
            "06:00",
            "09:00",
            "ForceCharge",
            extra_param={"minSocOnGrid": 20, "fdSoc": 80, "fdPwr": 3000},
        ),
        group("00:00", "00:00", enable=0),
    ]
    original = copy.deepcopy(groups)

    result = Client.update_group(
        groups,
        1,
        fields={"workMode": "ForceDischarge"},
        extra_param={"fdSoc": 30},
    )

    assert groups == original  # input not mutated
    assert result[0] == Client.minimal_group(groups[0])
    assert result[2] == Client.minimal_group(groups[2])
    assert result[1]["workMode"] == "ForceDischarge"
    assert result[1]["startHour"] == 6
    # New extraParam values merge into the existing ones.
    assert result[1]["extraParam"] == {
        "minSocOnGrid": 20,
        "fdSoc": 30,
        "fdPwr": 3000,
    }


def test_update_group_without_extra_param_keeps_existing() -> None:
    """Changing only fields leaves the group's extraParam untouched."""
    groups = [group("06:00", "09:00", extra_param={"fdSoc": 80})]
    result = Client.update_group(groups, 0, fields={"enable": 0})
    assert result[0]["enable"] == 0
    assert result[0]["extraParam"] == {"fdSoc": 80}


def test_create_default_schedule_group() -> None:
    """The default group is a full-day period with the given mode and min SoC."""
    assert Client.create_default_schedule_group("Backup", 15) == {
        "enable": 1,
        "startHour": 0,
        "startMinute": 0,
        "endHour": 23,
        "endMinute": 59,
        "workMode": "Backup",
        "extraParam": {"minSocOnGrid": 15},
    }


# --- device properties -------------------------------------------------------


PROPERTIES = {
    "fdpwr": {"range": {"min": 0, "max": 10500}},
    "fdsoc": {"range": {"min": 10, "max": 100}},
    "reactivepowerenable": {"enumList": [0, 1]},
    "maxsoc": {"range": {"min": 10}},
    "minsocongrid": "not-a-dict",
}


@pytest.mark.parametrize(
    ("field", "expected"),
    [
        ("fdPwr", (0.0, 10500.0)),  # camelCase is looked up lowercased
        ("fdsoc", (10.0, 100.0)),
        ("reactivepowerenable", None),  # no range at all
        ("maxSoc", None),  # range missing max
        ("minSocOnGrid", None),  # malformed entry
        ("unknown", None),
    ],
)
def test_property_range(field: str, expected: tuple[float, float] | None) -> None:
    """Ranges come from the lowercased properties block, or None if unusable."""
    assert Client.property_range(PROPERTIES, field) == expected


def test_property_range_without_properties() -> None:
    """No properties block means no range."""
    assert Client.property_range(None, "fdPwr") is None
    assert Client.property_range({}, "fdPwr") is None


def test_extract_work_mode_options() -> None:
    """Device-reported work modes are used when present, else the defaults."""
    schedule = {"properties": {"workmode": {"enumList": ["SelfUse", "Backup"]}}}
    assert Client._extract_work_mode_options(schedule) == ["SelfUse", "Backup"]
    assert Client._extract_work_mode_options({}) == DEFAULT_WORK_MODE_OPTIONS
    empty = {"properties": {"workmode": {"enumList": []}}}
    assert Client._extract_work_mode_options(empty) == DEFAULT_WORK_MODE_OPTIONS


def test_extract_properties() -> None:
    """A non-dict properties value is treated as empty."""
    assert Client._extract_properties({"properties": {"a": 1}}) == {"a": 1}
    assert Client._extract_properties({"properties": None}) == {}
    assert Client._extract_properties({}) == {}


# --- the write payload -------------------------------------------------------


def _client_with_mock_request() -> tuple[FoxessHapaApiClient, AsyncMock]:
    client = FoxessHapaApiClient("SN123", "key", session=None)  # type: ignore[arg-type]
    request = AsyncMock(return_value={"errno": 0})
    client._api_request = request  # type: ignore[method-assign]
    return client, request


def test_set_scheduler_pads_to_eight_slots() -> None:
    """A full replace pads with disabled placeholders up to 8 slots."""
    client, request = _client_with_mock_request()
    periods = [group("06:00", "09:00", "ForceCharge")]

    assert asyncio.run(client.async_set_scheduler(periods)) is True

    method, path = request.call_args.args
    payload = request.call_args.kwargs["data"]
    assert (method, path) == ("POST", "/op/v2/device/scheduler/enable")
    assert payload["deviceSN"] == "SN123"
    assert payload["enable"] == 1
    assert payload["isDefault"] is False
    assert len(payload["groups"]) == 8
    assert payload["groups"][0] == periods[0]
    for placeholder in payload["groups"][1:]:
        assert placeholder["enable"] == 0
        assert not Client.is_active_group(placeholder)
    # Placeholders are independent copies.
    assert payload["groups"][1] is not payload["groups"][2]


def test_set_scheduler_partial_update_is_not_padded() -> None:
    """With pad=False the caller's list is sent exactly as given."""
    client, request = _client_with_mock_request()
    periods = [group("06:00", "09:00"), group("00:00", "00:00", enable=0)]

    asyncio.run(client.async_set_scheduler(periods, pad=False, enable=False))

    payload = request.call_args.kwargs["data"]
    assert payload["groups"] == periods
    assert payload["enable"] == 0
