"""Services for FoxESS HAPA integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import async_extract_config_entry_ids

from .api import DEFAULT_WORK_MODE_OPTIONS, FoxessHapaApiClient
from .const import DOMAIN, LOGGER

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant, ServiceCall

SERVICE_SET_SCHEDULE = "set_schedule"
SERVICE_SET_SLOT = "set_slot"
SERVICE_SET_CURRENT_PERIOD = "set_current_period"

# Outer sanity bounds only. The device reports the real limits in the scheduler
# `properties` block (fdPwr maxed at 10500 W on an H3, not the 6000 once assumed
# here), and the supported work modes in properties.workmode.enumList, so both
# are validated per-device at call time in _validate_against_device().
_SOC_BOUNDS = vol.Range(min=0, max=100)
_POWER_BOUNDS = vol.Range(min=0, max=100000)

# extraParam fields settable through these services, mapped to their API names
# and the `properties` key carrying the device's range for each.
_EXTRA_PARAM_FIELDS: dict[str, str] = {
    "min_soc": "minSocOnGrid",
    "max_soc": "maxSoc",
    "fd_soc": "fdSoc",
    "fd_pwr": "fdPwr",
}

# Superseded names kept working for existing automations. `charge_to_soc` and
# `charge_power` were misleading: fdSoc/fdPwr apply to Force *Charge* and Force
# *Discharge* alike, so the neutral fd_soc/fd_pwr names replace them.
_DEPRECATED_FIELD_ALIASES: dict[str, str] = {
    "charge_to_soc": "fd_soc",
    "charge_power": "fd_pwr",
}

# `target_soc` is shorthand for min_soc + fd_soc at the same value: the floor
# in SelfUse/ForceDischarge and the level ForceCharge charges up to, which is
# what number.target_soc sets. It is expanded in _expand_target_soc().
_SETTABLE_FIELDS = (
    "work_mode",
    "target_soc",
    "min_soc",
    "max_soc",
    "fd_soc",
    "fd_pwr",
)

# Services act on one inverter, picked as a device, one of its entities, or an
# area/label containing exactly one. The target UI offers all of these, so the
# schema accepts them all and _resolve_entry() refuses anything that resolves
# to zero or several inverters rather than fanning a schedule write out.
# `config_entry_id` predates device targeting and is kept so existing
# automations keep working; new calls should use `target:`.
_ENTRY_FIELDS = {
    **cv.TARGET_SERVICE_FIELDS,
    vol.Optional("config_entry_id"): cv.string,
}

_PERIOD_SCHEMA = vol.Schema(
    {
        vol.Required("start_time"): cv.string,
        vol.Required("end_time"): cv.string,
        vol.Required("work_mode"): cv.string,
        vol.Optional("enabled", default=True): cv.boolean,
        vol.Optional("target_soc"): vol.All(vol.Coerce(int), _SOC_BOUNDS),
        vol.Optional("min_soc"): vol.All(vol.Coerce(int), _SOC_BOUNDS),
        vol.Optional("max_soc"): vol.All(vol.Coerce(int), _SOC_BOUNDS),
        vol.Optional("fd_soc"): vol.All(vol.Coerce(int), _SOC_BOUNDS),
        vol.Optional("fd_pwr"): vol.All(vol.Coerce(int), _POWER_BOUNDS),
        vol.Optional("charge_to_soc"): vol.All(vol.Coerce(int), _SOC_BOUNDS),
        vol.Optional("charge_power"): vol.All(vol.Coerce(int), _POWER_BOUNDS),
    },
    extra=vol.REMOVE_EXTRA,
)

SCHEMA_SET_SCHEDULE = vol.Schema(
    {
        **_ENTRY_FIELDS,
        vol.Required("periods"): vol.All(
            [_PERIOD_SCHEMA],
            vol.Length(min=1, max=8),
        ),
    }
)

SCHEMA_SET_SLOT = vol.Schema(
    {
        **_ENTRY_FIELDS,
        vol.Required("slot"): vol.All(vol.Coerce(int), vol.Range(min=0, max=7)),
        vol.Optional("start_time"): cv.string,
        vol.Optional("end_time"): cv.string,
        vol.Optional("work_mode"): cv.string,
        vol.Optional("enabled"): cv.boolean,
        vol.Optional("target_soc"): vol.All(vol.Coerce(int), _SOC_BOUNDS),
        vol.Optional("min_soc"): vol.All(vol.Coerce(int), _SOC_BOUNDS),
        vol.Optional("max_soc"): vol.All(vol.Coerce(int), _SOC_BOUNDS),
        vol.Optional("fd_soc"): vol.All(vol.Coerce(int), _SOC_BOUNDS),
        vol.Optional("fd_pwr"): vol.All(vol.Coerce(int), _POWER_BOUNDS),
        vol.Optional("charge_to_soc"): vol.All(vol.Coerce(int), _SOC_BOUNDS),
        vol.Optional("charge_power"): vol.All(vol.Coerce(int), _POWER_BOUNDS),
    }
)

SCHEMA_SET_CURRENT_PERIOD = vol.Schema(
    {
        **_ENTRY_FIELDS,
        vol.Optional("work_mode"): cv.string,
        vol.Optional("target_soc"): vol.All(vol.Coerce(int), _SOC_BOUNDS),
        vol.Optional("min_soc"): vol.All(vol.Coerce(int), _SOC_BOUNDS),
        vol.Optional("max_soc"): vol.All(vol.Coerce(int), _SOC_BOUNDS),
        vol.Optional("fd_soc"): vol.All(vol.Coerce(int), _SOC_BOUNDS),
        vol.Optional("fd_pwr"): vol.All(vol.Coerce(int), _POWER_BOUNDS),
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


def _extra_param_from(data: dict) -> dict:
    """Pick the extraParam fields present in service data, keyed by API name."""
    return {
        api_field: data[key]
        for key, api_field in _EXTRA_PARAM_FIELDS.items()
        if key in data
    }


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

    extra_param = _extra_param_from(period)
    if extra_param:
        group["extraParam"] = extra_param

    return group


def _normalise_aliases(data: dict) -> dict:
    """Rewrite superseded field names to their current equivalents."""
    normalised = dict(data)
    for old_key, new_key in _DEPRECATED_FIELD_ALIASES.items():
        if old_key not in normalised:
            continue
        value = normalised.pop(old_key)
        if new_key in normalised:
            LOGGER.warning(
                "Both %r and %r given; ignoring the deprecated %r",
                old_key,
                new_key,
                old_key,
            )
            continue
        LOGGER.warning(
            "%r is deprecated, use %r instead (fdSoc/fdPwr apply to both Force "
            "Charge and Force Discharge, so the 'charge' naming was misleading)",
            old_key,
            new_key,
        )
        normalised[new_key] = value
    return normalised


def _expand_target_soc(data: dict) -> dict:
    """
    Turn `target_soc` into min_soc + fd_soc at the same value.

    Runs before device validation so both resulting fields are range-checked.
    Giving target_soc alongside either field it expands to is ambiguous, so
    that is rejected rather than silently picking a winner.
    """
    if "target_soc" not in data:
        return data
    clashes = [key for key in ("min_soc", "fd_soc") if key in data]
    if clashes:
        msg = (
            f"target_soc cannot be combined with {', '.join(clashes)}; "
            "it sets both min_soc and fd_soc"
        )
        raise ServiceValidationError(msg)
    expanded = dict(data)
    value = expanded.pop("target_soc")
    expanded["min_soc"] = value
    expanded["fd_soc"] = value
    return expanded


def _validate_against_device(data: dict, coordinator: Any) -> None:
    """
    Check work mode and numeric fields against what the device reports.

    The device advertises its supported modes in properties.workmode.enumList
    and per-field limits in properties.<field>.range. Both are device-specific,
    so a static schema cannot police them: an H3 accepts fdPwr up to 10500 W but
    rejects work modes such as PeakShaving that other models support.
    """
    device_data = coordinator.data or {}

    work_mode = data.get("work_mode")
    options = device_data.get("work_mode_options") or DEFAULT_WORK_MODE_OPTIONS
    if work_mode is not None and work_mode not in options:
        msg = (
            f"Work mode {work_mode!r} is not supported by this device. "
            f"Supported: {', '.join(options)}"
        )
        raise ServiceValidationError(msg)

    properties = device_data.get("scheduler_properties")
    for key, api_field in _EXTRA_PARAM_FIELDS.items():
        if key not in data:
            continue
        bounds = FoxessHapaApiClient.property_range(properties, api_field)
        if bounds is None:
            continue
        minimum, maximum = bounds
        if not minimum <= data[key] <= maximum:
            msg = (
                f"{key} must be between {minimum:g} and {maximum:g} "
                f"for this device (got {data[key]})"
            )
            raise ServiceValidationError(msg)


def _get_client_and_coordinator(
    hass: HomeAssistant, config_entry_id: str
) -> tuple[Any, Any]:
    """Get the API client and coordinator for a config entry."""
    entry = hass.config_entries.async_get_entry(config_entry_id)
    if entry is None:
        msg = f"Config entry {config_entry_id!r} not found"
        raise ServiceValidationError(msg)
    if entry.domain != DOMAIN:
        msg = f"Config entry {config_entry_id!r} is not a {DOMAIN} entry"
        raise ServiceValidationError(msg)
    runtime = getattr(entry, "runtime_data", None)
    if runtime is None:
        msg = f"Config entry {config_entry_id!r} is not loaded"
        raise ServiceValidationError(msg)
    return runtime.client, runtime.coordinator


async def _resolve_entry(call: ServiceCall, data: dict) -> tuple[Any, Any]:
    """
    Find the one FoxESS config entry a service call is aimed at.

    Prefers the service target (device, entity, area or label);
    `config_entry_id` is the pre-target way of naming the device and still
    honoured. Exactly one inverter must be targeted -- these services rewrite
    its schedule, and fanning that out across several devices is never what an
    automation wants.
    """
    if "config_entry_id" in data:
        LOGGER.warning(
            "'config_entry_id' is deprecated for %s.%s; target the device instead "
            "(target: device_id: ...)",
            DOMAIN,
            call.service,
        )
        return _get_client_and_coordinator(call.hass, data["config_entry_id"])

    entry_ids = await async_extract_config_entry_ids(call)
    matches = [
        entry
        for entry_id in entry_ids
        if (entry := call.hass.config_entries.async_get_entry(entry_id)) is not None
        and entry.domain == DOMAIN
    ]
    if not matches:
        msg = "No FoxESS device targeted; pick the inverter under 'target'"
        raise ServiceValidationError(msg)
    if len(matches) > 1:
        msg = (
            f"{len(matches)} FoxESS devices targeted; these services act on "
            "one device at a time, so target a single device or entity"
        )
        raise ServiceValidationError(msg)
    return _get_client_and_coordinator(call.hass, matches[0].entry_id)


async def _handle_set_schedule(call: ServiceCall) -> None:
    """Handle foxess_hapa.set_schedule service call."""
    data = SCHEMA_SET_SCHEDULE(dict(call.data))
    client, coordinator = await _resolve_entry(call, data)

    periods = [_expand_target_soc(_normalise_aliases(p)) for p in data["periods"]]
    for period in periods:
        _validate_against_device(period, coordinator)

    groups = [_period_to_group(p) for p in periods]
    LOGGER.info("set_schedule: sending %d period(s) to device", len(groups))

    try:
        await client.async_set_scheduler(groups, enable=True)
    except Exception as ex:
        msg = f"Failed to set schedule: {ex}"
        raise HomeAssistantError(msg) from ex

    await coordinator.async_request_refresh()


async def _handle_set_slot(call: ServiceCall) -> None:
    """Handle foxess_hapa.set_slot service call."""
    data = _expand_target_soc(_normalise_aliases(SCHEMA_SET_SLOT(dict(call.data))))
    client, coordinator = await _resolve_entry(call, data)
    _validate_against_device(data, coordinator)
    slot_idx: int = data["slot"]

    try:
        groups = await client.async_get_schedule_groups(active_only=False)
    except Exception as ex:
        msg = f"Failed to fetch current schedule: {ex}"
        raise HomeAssistantError(msg) from ex

    # `slot` addresses active periods, which is what the schedule sensor shows,
    # but the write has to go back as the device's full list so untouched slots
    # (including its disabled ones) survive.
    active = client.active_group_indices(groups)
    if slot_idx >= len(active):
        msg = (
            f"Slot {slot_idx} does not exist; schedule only has {len(active)} period(s)"
        )
        raise ServiceValidationError(msg)
    target = active[slot_idx]

    fields: dict = {}
    if "start_time" in data:
        fields["startHour"], fields["startMinute"] = _parse_time(data["start_time"])
    if "end_time" in data:
        fields["endHour"], fields["endMinute"] = _parse_time(data["end_time"])
    if "work_mode" in data:
        fields["workMode"] = data["work_mode"]
    if "enabled" in data:
        fields["enable"] = 1 if data["enabled"] else 0

    updated_groups = client.update_group(
        groups, target, fields=fields, extra_param=_extra_param_from(data)
    )

    LOGGER.info(
        "set_slot: updating active slot %d (device group %d of %d)",
        slot_idx,
        target,
        len(updated_groups),
    )

    try:
        await client.async_set_scheduler(updated_groups, enable=True, pad=False)
    except Exception as ex:
        msg = f"Failed to update slot: {ex}"
        raise HomeAssistantError(msg) from ex

    await coordinator.async_request_refresh()


async def _handle_set_current_period(call: ServiceCall) -> None:
    """
    Handle foxess_hapa.set_current_period service call.

    Applies every given field to the schedule period governing the current
    time in one scheduler write, so an automation can switch work mode and
    move the SoC target together without a window where only one has landed.
    """
    data = _expand_target_soc(
        _normalise_aliases(SCHEMA_SET_CURRENT_PERIOD(dict(call.data)))
    )
    if not any(key in data for key in _SETTABLE_FIELDS):
        msg = f"Nothing to set; give at least one of {', '.join(_SETTABLE_FIELDS)}"
        raise ServiceValidationError(msg)

    client, coordinator = await _resolve_entry(call, data)
    _validate_against_device(data, coordinator)

    try:
        groups = await client.async_get_schedule_groups(active_only=False)
    except Exception as ex:
        msg = f"Failed to fetch current schedule: {ex}"
        raise HomeAssistantError(msg) from ex

    # Same slot the work mode select and number entities act on.
    target = client.find_current_period_index(groups) if groups else None
    if target is None:
        msg = "No schedule period covers the current time"
        raise ServiceValidationError(msg)

    fields = {"workMode": data["work_mode"]} if "work_mode" in data else None
    updated_groups = client.update_group(
        groups, target, fields=fields, extra_param=_extra_param_from(data)
    )

    LOGGER.info(
        "set_current_period: updating device group %d of %d",
        target,
        len(updated_groups),
    )

    try:
        await client.async_set_scheduler(updated_groups, enable=True, pad=False)
    except Exception as ex:
        msg = f"Failed to update current period: {ex}"
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
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_CURRENT_PERIOD,
        _handle_set_current_period,
        schema=SCHEMA_SET_CURRENT_PERIOD,
    )
