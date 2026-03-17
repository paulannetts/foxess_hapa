"""Services for FoxESS HAPA integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, LOGGER

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant, ServiceCall

SERVICE_SET_SCHEDULE = "set_schedule"
SERVICE_SET_SLOT = "set_slot"

_VALID_WORK_MODES = [
    "SelfUse",
    "ForceCharge",
    "ForceDischarge",
    "Backup",
    "FeedInFirst",
]

_PERIOD_SCHEMA = vol.Schema(
    {
        vol.Required("start_time"): cv.string,
        vol.Required("end_time"): cv.string,
        vol.Required("work_mode"): vol.In(_VALID_WORK_MODES),
        vol.Optional("enabled", default=True): cv.boolean,
        vol.Optional("min_soc"): vol.All(vol.Coerce(int), vol.Range(min=10, max=100)),
        vol.Optional("max_soc"): vol.All(vol.Coerce(int), vol.Range(min=10, max=100)),
    }
)

SCHEMA_SET_SCHEDULE = vol.Schema(
    {
        vol.Required("config_entry_id"): cv.string,
        vol.Required("periods"): vol.All(
            [_PERIOD_SCHEMA],
            vol.Length(min=1, max=8),
        ),
    }
)

SCHEMA_SET_SLOT = vol.Schema(
    {
        vol.Required("config_entry_id"): cv.string,
        vol.Required("slot"): vol.All(vol.Coerce(int), vol.Range(min=0, max=7)),
        vol.Optional("start_time"): cv.string,
        vol.Optional("end_time"): cv.string,
        vol.Optional("work_mode"): vol.In(_VALID_WORK_MODES),
        vol.Optional("enabled"): cv.boolean,
        vol.Optional("min_soc"): vol.All(vol.Coerce(int), vol.Range(min=10, max=100)),
        vol.Optional("max_soc"): vol.All(vol.Coerce(int), vol.Range(min=10, max=100)),
    }
)


def _parse_time(time_str: str) -> tuple[int, int]:
    """Parse HH:MM time string to (hour, minute) tuple."""
    try:
        parts = time_str.split(":")
        if len(parts) != 2:  # noqa: PLR2004
            msg = f"Invalid time format: {time_str!r}, expected HH:MM"
            raise ServiceValidationError(msg)
        hour, minute = int(parts[0]), int(parts[1])
        if not (0 <= hour <= 23 and 0 <= minute <= 59):  # noqa: PLR2004
            msg = f"Time out of range: {time_str!r}"
            raise ServiceValidationError(msg)
    except ValueError as exc:
        msg = f"Invalid time format: {time_str!r}, expected HH:MM"
        raise ServiceValidationError(msg) from exc
    else:
        return hour, minute


def _period_to_group(period: dict) -> dict:
    """Convert service period dict to API group format."""
    start_hour, start_minute = _parse_time(period["start_time"])
    end_hour, end_minute = _parse_time(period["end_time"])

    group: dict = {
        "enable": 1 if period.get("enabled", True) else 0,
        "startHour": start_hour,
        "startMinute": start_minute,
        "endHour": end_hour,
        "endMinute": end_minute,
        "workMode": period["work_mode"],
    }

    extra_param: dict = {}
    if "min_soc" in period:
        extra_param["minSocOnGrid"] = period["min_soc"]
    if "max_soc" in period:
        extra_param["maxSoc"] = period["max_soc"]
    if extra_param:
        group["extraParam"] = extra_param

    return group


def _get_client_and_coordinator(
    hass: HomeAssistant, config_entry_id: str
) -> tuple[Any, Any]:
    """Get the API client and coordinator for a config entry."""
    entry = hass.config_entries.async_get_entry(config_entry_id)
    if entry is None:
        msg = f"Config entry {config_entry_id!r} not found"
        raise ServiceValidationError(msg)
    runtime = getattr(entry, "runtime_data", None)
    if runtime is None:
        msg = f"Config entry {config_entry_id!r} is not loaded"
        raise ServiceValidationError(msg)
    return runtime.client, runtime.coordinator


async def _handle_set_schedule(call: ServiceCall) -> None:
    """Handle foxess_hapa.set_schedule service call."""
    data = SCHEMA_SET_SCHEDULE(dict(call.data))
    client, coordinator = _get_client_and_coordinator(
        call.hass, data["config_entry_id"]
    )

    groups = [_period_to_group(p) for p in data["periods"]]
    LOGGER.info("set_schedule: sending %d period(s) to device", len(groups))

    try:
        await client.async_set_scheduler(groups, enable=True)
    except Exception as ex:
        msg = f"Failed to set schedule: {ex}"
        raise HomeAssistantError(msg) from ex

    await coordinator.async_request_refresh()


async def _handle_set_slot(call: ServiceCall) -> None:
    """Handle foxess_hapa.set_slot service call."""
    data = SCHEMA_SET_SLOT(dict(call.data))
    client, coordinator = _get_client_and_coordinator(
        call.hass, data["config_entry_id"]
    )
    slot_idx: int = data["slot"]

    try:
        groups = await client.async_get_schedule_groups()
    except Exception as ex:
        msg = f"Failed to fetch current schedule: {ex}"
        raise HomeAssistantError(msg) from ex

    if slot_idx >= len(groups):
        msg = (
            f"Slot {slot_idx} does not exist; schedule only has {len(groups)} period(s)"
        )
        raise ServiceValidationError(msg)

    # Start from minimal representation (preserves extraParam)
    group = dict(client.minimal_group(groups[slot_idx]))

    if "start_time" in data:
        h, m = _parse_time(data["start_time"])
        group["startHour"] = h
        group["startMinute"] = m
    if "end_time" in data:
        h, m = _parse_time(data["end_time"])
        group["endHour"] = h
        group["endMinute"] = m
    if "work_mode" in data:
        group["workMode"] = data["work_mode"]
    if "enabled" in data:
        group["enable"] = 1 if data["enabled"] else 0

    # Merge extraParam fields into existing params
    extra_param = dict(groups[slot_idx].get("extraParam", {}))
    if "min_soc" in data:
        extra_param["minSocOnGrid"] = data["min_soc"]
    if "max_soc" in data:
        extra_param["maxSoc"] = data["max_soc"]
    if extra_param:
        group["extraParam"] = extra_param

    updated_groups = [
        group if i == slot_idx else client.minimal_group(g)
        for i, g in enumerate(groups)
    ]

    LOGGER.info("set_slot: updating slot %d of %d", slot_idx, len(updated_groups))

    try:
        await client.async_set_scheduler(updated_groups, enable=True)
    except Exception as ex:
        msg = f"Failed to update slot: {ex}"
        raise HomeAssistantError(msg) from ex

    await coordinator.async_request_refresh()


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register integration services (idempotent — skips if already registered)."""
    if hass.services.has_service(DOMAIN, SERVICE_SET_SCHEDULE):
        return

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SCHEDULE,
        _handle_set_schedule,
        schema=SCHEMA_SET_SCHEDULE,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SLOT,
        _handle_set_slot,
        schema=SCHEMA_SET_SLOT,
    )
