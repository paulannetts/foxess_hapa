"""Tests for the config flow, run inside a test Home Assistant instance."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.foxess_hapa.api import (
    FoxessDeviceInfo,
    FoxessHapaApiClientAuthenticationError,
    FoxessHapaApiClientCommunicationError,
    FoxessHapaApiClientError,
)
from custom_components.foxess_hapa.const import (
    CONF_API_KEY,
    CONF_DEVICE_SERIAL_NUMBER,
    DOMAIN,
)

from .conftest import SERIAL, make_entry

if TYPE_CHECKING:
    from collections.abc import Generator

    from homeassistant.core import HomeAssistant

USER_INPUT = {CONF_DEVICE_SERIAL_NUMBER: SERIAL, CONF_API_KEY: "test-key"}


def _device_info(station_name: str = "Home") -> FoxessDeviceInfo:
    return FoxessDeviceInfo(
        station_name=station_name,
        device_sn=SERIAL,
        device_type="H3-6.0-E",
        has_battery=True,
        master_version="1.54",
        manager_version="1.02",
        slave_version="1.01",
    )


@pytest.fixture
def device_detail() -> Generator[AsyncMock]:
    """Patch the credential check (a device-detail fetch) in the config flow."""
    with patch(
        "custom_components.foxess_hapa.config_flow.FoxessHapaApiClient.async_get_device_detail",
        new_callable=AsyncMock,
        return_value=_device_info(),
    ) as mock:
        yield mock


@pytest.fixture(autouse=True)
def no_entry_setup() -> Generator[AsyncMock]:
    """Stop a created entry from being set up; these tests are about the flow."""
    with patch(
        "custom_components.foxess_hapa.async_setup_entry", return_value=True
    ) as mock:
        yield mock


async def _submit(hass: HomeAssistant, user_input: dict[str, Any]) -> Any:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    return await hass.config_entries.flow.async_configure(result["flow_id"], user_input)


async def test_form_shows_without_errors(hass: HomeAssistant) -> None:
    """Starting the flow shows the user form with no errors."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}


async def test_success_creates_entry(
    hass: HomeAssistant, device_detail: AsyncMock, no_entry_setup: AsyncMock
) -> None:
    """Valid credentials create an entry titled after the station, keyed by serial."""
    result = await _submit(hass, USER_INPUT)
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Home"
    assert result["data"] == USER_INPUT
    assert result["result"].unique_id == SERIAL
    device_detail.assert_awaited_once()
    no_entry_setup.assert_called_once()


async def test_title_falls_back_to_serial(
    hass: HomeAssistant, device_detail: AsyncMock
) -> None:
    """Without a station name the entry is titled with the serial number."""
    device_detail.return_value = _device_info(station_name="")

    result = await _submit(hass, USER_INPUT)

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == SERIAL


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (FoxessHapaApiClientAuthenticationError("bad key"), "invalid_auth"),
        (FoxessHapaApiClientCommunicationError("timeout"), "cannot_connect"),
        (FoxessHapaApiClientError("errno 40257"), "unknown"),
    ],
)
async def test_errors_reshow_form(
    hass: HomeAssistant,
    device_detail: AsyncMock,
    error: Exception,
    expected: str,
) -> None:
    """A failed credential check re-shows the form with the matching error."""
    device_detail.side_effect = error

    result = await _submit(hass, USER_INPUT)

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": expected}


async def test_recovers_after_error(
    hass: HomeAssistant, device_detail: AsyncMock
) -> None:
    """After an error the same flow can still succeed."""
    device_detail.side_effect = FoxessHapaApiClientCommunicationError("timeout")
    result = await _submit(hass, USER_INPUT)
    assert result["errors"] == {"base": "cannot_connect"}

    device_detail.side_effect = None
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_same_serial_aborts(
    hass: HomeAssistant, device_detail: AsyncMock
) -> None:
    """Adding an inverter that is already configured aborts."""
    make_entry().add_to_hass(hass)

    result = await _submit(hass, USER_INPUT)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    device_detail.assert_awaited_once()
