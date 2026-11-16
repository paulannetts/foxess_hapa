"""Tests for parsing FoxESS API responses and request signing."""

from __future__ import annotations

import asyncio
import hashlib
from typing import Any
from unittest.mock import AsyncMock

import pytest

from custom_components.foxess_hapa import api
from custom_components.foxess_hapa.api import FoxessHapaApiClient


def _client(result: dict[str, Any]) -> tuple[FoxessHapaApiClient, AsyncMock]:
    client = FoxessHapaApiClient("SN123", "key", session=None)  # type: ignore[arg-type]
    request = AsyncMock(return_value=result)
    client._api_request = request  # type: ignore[method-assign]
    return client, request


def _real_time(datas: list[dict[str, Any]]) -> api.FoxessRealTimeData:
    client, _ = _client({"errno": 0, "result": [{"datas": datas}]})
    return asyncio.run(client.async_get_real_time_data())


# --- real-time data ----------------------------------------------------------


def test_real_time_maps_variables() -> None:
    """API variable names map onto the dataclass fields."""
    data = _real_time(
        [
            {"variable": "pvPower", "value": 3.25},
            {"variable": "SoC", "value": 76},
            {"variable": "meterPower", "value": -1.5},
            {"variable": "batChargePower", "value": 2.0},
            {"variable": "batDischargePower", "value": 0.5},
            {"variable": "runningState", "value": "163"},
            {"variable": "currentFaultCount", "value": "2"},
        ]
    )
    assert data.pv_power == 3.25
    assert data.battery_soc == 76.0
    assert data.grid_power == -1.5
    assert data.running_state == "163"
    assert data.current_fault_count == 2
    assert data.raw_variables is not None
    assert data.raw_variables["pvPower"] == 3.25


def test_battery_power_is_charge_minus_discharge() -> None:
    """Battery power is positive when charging and negative when discharging."""
    charging = _real_time(
        [
            {"variable": "batChargePower", "value": 2.0},
            {"variable": "batDischargePower", "value": 0.5},
        ]
    )
    discharging = _real_time(
        [
            {"variable": "batChargePower", "value": 0},
            {"variable": "batDischargePower", "value": 1.2},
        ]
    )
    assert charging.battery_power == 1.5
    assert discharging.battery_power == -1.2


def test_real_time_missing_and_null_values_use_defaults() -> None:
    """Variables that are absent or null fall back to 0 / empty string."""
    data = _real_time(
        [
            {"variable": "pvPower", "value": None},
            {"variable": "runningState", "value": None},
            {"variable": "currentFaultCount", "value": None},
        ]
    )
    assert data.pv_power == 0.0
    assert data.inverter_temp == 0.0  # not in the response at all
    assert data.running_state == ""
    assert data.current_fault == ""
    assert data.current_fault_count == 0


def test_real_time_variable_without_value_is_zero() -> None:
    """A variable entry with no value key reads as 0."""
    assert _real_time([{"variable": "pvPower"}]).pv_power == 0.0


def test_real_time_non_numeric_int_falls_back() -> None:
    """A non-numeric value for an integer field falls back to the default."""
    data = _real_time([{"variable": "currentFaultCount", "value": "n/a"}])
    assert data.current_fault_count == 0


@pytest.mark.xfail(
    strict=True,
    raises=ValueError,
    reason="safe_float has no error handling, unlike safe_int",
)
def test_real_time_non_numeric_float_falls_back() -> None:
    """A non-numeric value for a float field should fall back to the default."""
    data = _real_time([{"variable": "pvPower", "value": "n/a"}])
    assert data.pv_power == 0.0


@pytest.mark.xfail(
    strict=True,
    raises=AttributeError,
    reason="an empty result list is left as a list and .get() is called on it",
)
def test_real_time_empty_result() -> None:
    """An empty result should give an all-default reading, not a crash."""
    client, _ = _client({"errno": 0, "result": []})
    data = asyncio.run(client.async_get_real_time_data())
    assert data.pv_power == 0.0
    assert data.raw_variables == {}


def test_real_time_requests_this_device() -> None:
    """The real-time query is a POST for this device's serial number."""
    client, request = _client({"errno": 0, "result": [{"datas": []}]})
    asyncio.run(client.async_get_real_time_data())
    assert request.call_args.args == ("POST", "/op/v1/device/real/query")
    assert request.call_args.kwargs["data"] == {"sns": ["SN123"]}


# --- request signing ---------------------------------------------------------


def test_signature_matches_foxess_format(monkeypatch: pytest.MonkeyPatch) -> None:
    r"""
    The signature is MD5 of path, token and timestamp joined by literal \r\n.

    FoxESS's own examples join the parts with the four characters ``\r\n``
    (backslash, r, backslash, n), not a real CR/LF. The integration does the
    same and works against the live API, so this pins that behaviour.
    """
    monkeypatch.setattr(api.time, "time", lambda: 1_700_000_000.123)
    client = FoxessHapaApiClient("SN123", "my-key", session=None)  # type: ignore[arg-type]

    headers = client._generate_signature("/op/v1/device/detail")

    expected = hashlib.md5(  # noqa: S324
        b"/op/v1/device/detail\\r\\nmy-key\\r\\n1700000000123"
    ).hexdigest()
    assert headers["signature"] == expected
    assert headers["timestamp"] == "1700000000123"
    assert headers["token"] == "my-key"
    assert headers["Content-Type"] == "application/json"
