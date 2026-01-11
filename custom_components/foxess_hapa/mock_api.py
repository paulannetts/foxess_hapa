"""Mock FoxESS Cloud API Client for development without real hardware."""

from __future__ import annotations

import math
import random
from datetime import UTC, datetime
from typing import Any

from .api import (
    FoxessDeviceInfo,
    FoxessHapaApiClient,
    FoxessRealTimeData,
)
from .const import LOGGER

# Time-of-day constants for load simulation
_MORNING_START = 6
_MORNING_END = 9
_DAY_END = 17
_EVENING_END = 22
_MAX_SOC = 100


class MockFoxessHapaApiClient(FoxessHapaApiClient):
    """
    Mock FoxESS API Client that returns simulated data.

    This client simulates a solar installation with battery storage.
    Data varies based on time of day to provide realistic values:
    - Solar generation peaks at midday
    - Battery charges during high generation, discharges in evening
    - Load varies with some randomness
    """

    def __init__(
        self,
        device_serial_number: str,
        api_key: str,
        session: Any,  # Not used in mock, but keeps interface compatible
    ) -> None:
        """Initialize the mock API client."""
        self._device_sn = device_serial_number
        self._api_key = api_key
        self._session = session
        self._last_api_call: float = 0

        # Configurable mock parameters
        self._panel_capacity_kw = 6.0  # 6kW solar array
        self._battery_capacity_kwh = 10.0  # 10kWh battery
        self._battery_soc = 50.0  # Starting SOC
        self._min_soc = 10
        self._min_soc_on_grid = 10
        self._work_mode = "SelfUse"

        LOGGER.info(
            "MockFoxessHapaApiClient initialized for device %s", device_serial_number
        )

    def _get_solar_generation(self) -> float:
        """
        Calculate solar generation based on time of day.

        Uses a sine curve to simulate sun position, with peak at noon.
        Returns 0 outside of daylight hours (6am-8pm).
        """
        now = datetime.now(tz=UTC)
        hour = now.hour + now.minute / 60.0

        # Daylight hours: 6am to 8pm (adjust for your location)
        sunrise = 6.0
        sunset = 20.0

        if hour < sunrise or hour > sunset:
            return 0.0

        # Normalize to 0-1 range over daylight hours
        day_progress = (hour - sunrise) / (sunset - sunrise)

        # Sine curve peaks at 0.5 (solar noon)
        generation_factor = math.sin(day_progress * math.pi)

        # Add some cloud variation (random noise)
        cloud_factor = 0.8 + random.random() * 0.2  # noqa: S311

        return self._panel_capacity_kw * generation_factor * cloud_factor

    def _get_load_power(self) -> float:
        """Simulate household load with time-of-day variation."""
        now = datetime.now(tz=UTC)
        hour = now.hour

        # Base load varies by time of day
        if _MORNING_START <= hour < _MORNING_END:  # Morning peak
            base_load = 1.5
        elif _MORNING_END <= hour < _DAY_END:  # Daytime (away at work)
            base_load = 0.5
        elif _DAY_END <= hour < _EVENING_END:  # Evening peak
            base_load = 2.0
        else:  # Night
            base_load = 0.3

        # Add random variation (+/- 30%)
        return base_load * (0.7 + random.random() * 0.6)  # noqa: S311

    def _update_battery_soc(
        self, charge_power: float, duration_hours: float = 0.016
    ) -> None:
        """
        Update battery SOC based on charge/discharge power.

        Args:
            charge_power: Positive = charging, negative = discharging (kW)
            duration_hours: Time period (default ~1 minute)

        """
        energy_kwh = charge_power * duration_hours
        soc_change = (energy_kwh / self._battery_capacity_kwh) * 100

        self._battery_soc = max(0, min(_MAX_SOC, self._battery_soc + soc_change))

    async def async_get_data(self) -> dict[str, Any]:
        """Get all simulated data."""
        LOGGER.debug("MockFoxessHapaApiClient.async_get_data called")

        device_info = await self.async_get_device_detail()
        real_time = await self.async_get_real_time_data()
        scheduler_groups = await self.async_get_schedule_groups()

        return {
            "device_info": device_info,
            "real_time": real_time,
            "scheduler_groups": scheduler_groups,
        }

    async def async_get_device_detail(self) -> FoxessDeviceInfo:
        """Return mock device information."""
        LOGGER.debug("MockFoxessHapaApiClient.async_get_device_detail called")

        return FoxessDeviceInfo(
            station_name="Mock Solar Station",
            device_sn=self._device_sn,
            device_type="H3-6.0-E",
            has_battery=True,
            master_version="1.54",
            manager_version="1.02",
            slave_version="1.01",
            battery_list=[
                {
                    "sn": f"{self._device_sn}-BAT1",
                    "type": "HV2600",
                    "capacity": self._battery_capacity_kwh,
                }
            ],
        )

    async def async_get_real_time_data(self) -> FoxessRealTimeData:
        """Return simulated real-time power data."""
        LOGGER.debug("MockFoxessHapaApiClient.async_get_real_time_data called")

        pv_power = self._get_solar_generation()
        load_power = self._get_load_power()

        # Calculate power balance
        surplus = pv_power - load_power

        # Battery logic: charge with surplus, discharge for deficit
        battery_power = 0.0
        grid_power = 0.0

        if surplus > 0:
            # Excess solar: charge battery first, then export
            if self._battery_soc < _MAX_SOC:
                # Limit charge rate to 3kW
                battery_power = min(surplus, 3.0)
                surplus -= battery_power
            # Remaining surplus goes to grid (feed-in)
            if surplus > 0:
                grid_power = -surplus  # Negative = export
        else:
            # Deficit: discharge battery first, then import
            deficit = -surplus
            if self._battery_soc > self._min_soc:
                # Limit discharge rate to 3kW
                battery_power = -min(deficit, 3.0)
                deficit += battery_power  # battery_power is negative
            # Remaining deficit from grid
            if deficit > 0:
                grid_power = deficit  # Positive = import

        # Update battery SOC
        self._update_battery_soc(battery_power)

        # Calculate derived values
        feed_in_power = max(0, -grid_power)
        grid_consumption_power = max(0, grid_power)
        generation_power = pv_power

        # Build raw variables dict for compatibility
        raw_variables = {
            "pvPower": round(pv_power, 2),
            "SoC": round(self._battery_soc, 1),
            "batChargePower": round(max(0, battery_power), 2),
            "batDischargePower": round(max(0, -battery_power), 2),
            "meterPower": round(grid_power, 2),
            "loadsPower": round(load_power, 2),
            "feedinPower": round(feed_in_power, 2),
            "gridConsumptionPower": round(grid_consumption_power, 2),
            "generationPower": round(generation_power, 2),
        }

        return FoxessRealTimeData(
            pv_power=round(pv_power, 2),
            battery_soc=round(self._battery_soc, 1),
            battery_power=round(battery_power, 2),
            grid_power=round(grid_power, 2),
            load_power=round(load_power, 2),
            feed_in_power=round(feed_in_power, 2),
            grid_consumption_power=round(grid_consumption_power, 2),
            generation_power=round(generation_power, 2),
            raw_variables=raw_variables,
        )

    async def async_get_scheduler(self) -> dict[str, Any]:
        """Return mock scheduler settings."""
        LOGGER.debug("MockFoxessHapaApiClient.async_get_scheduler called")

        return {
            "enable": True,
            "groups": [
                {
                    "enable": 1,
                    "startHour": 0,
                    "startMinute": 0,
                    "endHour": 23,
                    "endMinute": 59,
                    "workMode": self._work_mode,
                    "extraParam": {
                        "minSocOnGrid": self._min_soc_on_grid,
                    },
                },
            ],
        }

    async def async_set_scheduler(
        self,
        periods: list[dict[str, Any]],
        *,
        enable: bool = True,
    ) -> bool:
        """Mock setting scheduler (updates internal state)."""
        LOGGER.info(
            "MockFoxessHapaApiClient.async_set_scheduler called: enable=%s, periods=%s",
            enable,
            periods,
        )

        # Update settings from the current period if provided
        if periods:
            current_idx = self.find_current_period_index(periods)
            if current_idx is not None:
                period = periods[current_idx]
                self._work_mode = period.get("workMode", self._work_mode)
                extra_param = period.get("extraParam", {})
                if "minSocOnGrid" in extra_param:
                    self._min_soc_on_grid = extra_param["minSocOnGrid"]

        return True
