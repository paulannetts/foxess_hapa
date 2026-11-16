"""Shared helpers for FoxESS HAPA tests."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest

from custom_components.foxess_hapa import api


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
