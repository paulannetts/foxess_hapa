"""Tests for the input handling behind the scheduler services."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from homeassistant.exceptions import ServiceValidationError

from custom_components.foxess_hapa import services
from custom_components.foxess_hapa.api import DEFAULT_WORK_MODE_OPTIONS

# --- times -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("00:00", (0, 0)),
        ("07:30", (7, 30)),
        ("7:05", (7, 5)),
        ("23:59", (23, 59)),
    ],
)
def test_parse_time_valid(text: str, expected: tuple[int, int]) -> None:
    """HH:MM strings parse to (hour, minute)."""
    assert services._parse_time(text) == expected


@pytest.mark.parametrize(
    "text",
    ["", "7", "07:00:00", "24:00", "12:60", "-1:00", "ab:cd", "07:", ":30"],
)
def test_parse_time_invalid(text: str) -> None:
    """Malformed or out-of-range times are rejected with a validation error."""
    with pytest.raises(ServiceValidationError):
        services._parse_time(text)


# --- periods -----------------------------------------------------------------


def test_period_to_group_full() -> None:
    """A service period becomes an API group with extraParam under API names."""
    period = {
        "start_time": "06:00",
        "end_time": "09:30",
        "work_mode": "ForceCharge",
        "enabled": True,
        "min_soc": 20,
        "max_soc": 95,
        "fd_soc": 90,
        "fd_pwr": 5000,
    }
    assert services._period_to_group(period) == {
        "enable": 1,
        "startHour": 6,
        "startMinute": 0,
        "endHour": 9,
        "endMinute": 30,
        "workMode": "ForceCharge",
        "extraParam": {
            "minSocOnGrid": 20,
            "maxSoc": 95,
            "fdSoc": 90,
            "fdPwr": 5000,
        },
    }


def test_period_to_group_minimal() -> None:
    """Without SoC/power fields there is no extraParam; enabled defaults on."""
    group = services._period_to_group(
        {"start_time": "22:00", "end_time": "05:00", "work_mode": "SelfUse"}
    )
    assert group["enable"] == 1
    assert "extraParam" not in group


def test_period_to_group_disabled() -> None:
    """enabled=False becomes enable=0."""
    group = services._period_to_group(
        {
            "start_time": "01:00",
            "end_time": "02:00",
            "work_mode": "SelfUse",
            "enabled": False,
        }
    )
    assert group["enable"] == 0


def test_period_to_group_rejects_bad_time() -> None:
    """A bad time in a period is a validation error, not a crash."""
    with pytest.raises(ServiceValidationError):
        services._period_to_group(
            {"start_time": "25:00", "end_time": "02:00", "work_mode": "SelfUse"}
        )


def test_period_schema_drops_unknown_keys() -> None:
    """The period schema strips keys it does not know and applies defaults."""
    period = services._PERIOD_SCHEMA(
        {
            "start_time": "06:00",
            "end_time": "09:00",
            "work_mode": "SelfUse",
            "bogus": 1,
        }
    )
    assert "bogus" not in period
    assert period["enabled"] is True


# --- deprecated aliases ------------------------------------------------------


def test_normalise_aliases_renames_deprecated_fields() -> None:
    """charge_to_soc/charge_power become fd_soc/fd_pwr."""
    data = {"charge_to_soc": 80, "charge_power": 3000, "work_mode": "ForceCharge"}
    result = services._normalise_aliases(data)
    assert result == {"fd_soc": 80, "fd_pwr": 3000, "work_mode": "ForceCharge"}
    assert "charge_to_soc" in data  # input not mutated


def test_normalise_aliases_prefers_new_name() -> None:
    """When both names are given, the current name wins."""
    result = services._normalise_aliases({"charge_to_soc": 80, "fd_soc": 60})
    assert result == {"fd_soc": 60}


def test_normalise_aliases_no_aliases() -> None:
    """Data without deprecated names is unchanged."""
    assert services._normalise_aliases({"fd_soc": 60}) == {"fd_soc": 60}


# --- target_soc --------------------------------------------------------------


def test_expand_target_soc_sets_min_and_fd_soc() -> None:
    """target_soc expands to min_soc and fd_soc at the same value."""
    data = {"target_soc": 70, "work_mode": "SelfUse"}
    assert services._expand_target_soc(data) == {
        "min_soc": 70,
        "fd_soc": 70,
        "work_mode": "SelfUse",
    }
    assert data == {"target_soc": 70, "work_mode": "SelfUse"}  # not mutated


@pytest.mark.parametrize("clash", ["min_soc", "fd_soc"])
def test_expand_target_soc_rejects_ambiguous_input(clash: str) -> None:
    """target_soc together with a field it sets is rejected."""
    with pytest.raises(ServiceValidationError, match=clash):
        services._expand_target_soc({"target_soc": 70, clash: 50})


def test_expand_target_soc_absent() -> None:
    """Without target_soc the data is returned as is."""
    data = {"min_soc": 20}
    assert services._expand_target_soc(data) is data


def test_extra_param_from_maps_to_api_names() -> None:
    """Only settable SoC/power fields are picked, under their API names."""
    assert services._extra_param_from(
        {"min_soc": 10, "fd_pwr": 2000, "work_mode": "SelfUse"}
    ) == {"minSocOnGrid": 10, "fdPwr": 2000}


# --- device validation -------------------------------------------------------


def _coordinator(data: dict[str, Any] | None) -> Any:
    return SimpleNamespace(data=data)


DEVICE = {
    "work_mode_options": ["SelfUse", "ForceCharge", "ForceDischarge"],
    "scheduler_properties": {
        "fdpwr": {"range": {"min": 0, "max": 10500}},
        "fdsoc": {"range": {"min": 10, "max": 100}},
        "minsocongrid": {"range": {"min": 10, "max": 100}},
    },
}


def test_validate_accepts_supported_values() -> None:
    """Values inside the device's limits pass, including the bounds."""
    services._validate_against_device(
        {"work_mode": "ForceCharge", "fd_pwr": 10500, "fd_soc": 10, "min_soc": 100},
        _coordinator(DEVICE),
    )


def test_validate_rejects_unsupported_work_mode() -> None:
    """A work mode the device does not list is rejected."""
    with pytest.raises(ServiceValidationError, match="PeakShaving"):
        services._validate_against_device(
            {"work_mode": "PeakShaving"}, _coordinator(DEVICE)
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [("fd_pwr", 10501), ("fd_soc", 9), ("min_soc", 101)],
)
def test_validate_rejects_out_of_range(field: str, value: int) -> None:
    """Values outside the device-reported range are rejected."""
    with pytest.raises(ServiceValidationError, match=field):
        services._validate_against_device({field: value}, _coordinator(DEVICE))


def test_validate_skips_fields_without_a_range() -> None:
    """Fields the device reports no range for are left to the schema bounds."""
    services._validate_against_device({"max_soc": 100}, _coordinator(DEVICE))


@pytest.mark.parametrize("data", [None, {}])
def test_validate_falls_back_to_default_work_modes(data: Any) -> None:
    """With no device data yet, the default work-mode list is used."""
    services._validate_against_device(
        {"work_mode": DEFAULT_WORK_MODE_OPTIONS[-1]}, _coordinator(data)
    )
    with pytest.raises(ServiceValidationError):
        services._validate_against_device({"work_mode": "NotAMode"}, _coordinator(data))
