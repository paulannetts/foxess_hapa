"""FoxESS Cloud API Client."""

from __future__ import annotations

import asyncio
import hashlib
import socket
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import aiohttp
import async_timeout

from .const import LOGGER


class FoxessHapaApiClientError(Exception):
    """Exception to indicate a general API error."""


class FoxessHapaApiClientCommunicationError(FoxessHapaApiClientError):
    """Exception to indicate a communication error."""


class FoxessHapaApiClientAuthenticationError(FoxessHapaApiClientError):
    """Exception to indicate an authentication error."""


@dataclass
class FoxessDeviceInfo:
    """Device information from FoxESS Cloud."""

    station_name: str
    device_sn: str
    device_type: str
    has_battery: bool
    master_version: str
    manager_version: str
    slave_version: str
    battery_list: list[dict] | None = None


@dataclass
class FoxessRealTimeData:
    """Real-time data from FoxESS Cloud."""

    # Main power metrics
    pv_power: float = 0.0
    battery_soc: float = 0.0
    battery_power: float = 0.0
    grid_power: float = 0.0
    load_power: float = 0.0
    feed_in_power: float = 0.0
    grid_consumption_power: float = 0.0
    generation_power: float = 0.0

    # PV String 1
    pv1_volt: float = 0.0
    pv1_current: float = 0.0
    pv1_power: float = 0.0

    # PV String 2
    pv2_volt: float = 0.0
    pv2_current: float = 0.0
    pv2_power: float = 0.0

    # PV String 3
    pv3_volt: float = 0.0
    pv3_current: float = 0.0
    pv3_power: float = 0.0

    # PV String 4
    pv4_volt: float = 0.0
    pv4_current: float = 0.0
    pv4_power: float = 0.0

    # EPS (Emergency Power Supply)
    eps_power: float = 0.0
    eps_current_r: float = 0.0
    eps_volt_r: float = 0.0
    eps_power_r: float = 0.0

    # Grid R-Phase
    r_current: float = 0.0
    r_volt: float = 0.0
    r_freq: float = 0.0
    r_power: float = 0.0

    # Temperature sensors
    ambient_temp: float = 0.0
    inverter_temp: float = 0.0
    battery_temp: float = 0.0

    # Inverter battery interface
    inv_bat_volt: float = 0.0
    inv_bat_current: float = 0.0
    inv_bat_power: float = 0.0

    # Battery charge/discharge power
    bat_charge_power: float = 0.0
    bat_discharge_power: float = 0.0

    # Battery direct measurements
    bat_volt: float = 0.0
    bat_current: float = 0.0

    # Meter power
    meter_power_2: float = 0.0

    # Energy totals (kWh)
    generation_total: float = 0.0
    residual_energy: float = 0.0
    energy_throughput: float = 0.0
    grid_consumption_total: float = 0.0
    loads_total: float = 0.0
    feed_in_total: float = 0.0
    charge_energy_total: float = 0.0
    discharge_energy_total: float = 0.0
    pv_energy_total: float = 0.0

    # Status
    running_state: str = ""
    battery_status: str = ""
    battery_status_name: str = ""
    current_fault: str = ""
    current_fault_count: int = 0

    raw_variables: dict[str, Any] | None = None


class FoxessHapaApiClient:
    """FoxESS Cloud API Client."""

    BASE_URL = "https://www.foxesscloud.com"
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    def __init__(
        self,
        device_serial_number: str,
        api_key: str,
        session: aiohttp.ClientSession,
    ) -> None:
        """Initialize the API client."""
        self._device_sn = device_serial_number
        self._api_key = api_key
        self._session = session
        self._last_api_call: float = 0

    def _generate_signature(self, path: str) -> dict[str, str]:
        r"""
        Generate authentication headers with MD5 signature.

        The signature is generated from: {path}\r\n{token}\r\n{timestamp}
        """
        timestamp = round(time.time() * 1000)
        signature_text = rf"{path}\r\n{self._api_key}\r\n{timestamp}"
        # MD5 is required by FoxESS Cloud API specification
        signature = hashlib.md5(  # noqa: S324
            signature_text.encode("UTF-8")
        ).hexdigest()

        return {
            "token": self._api_key,
            "lang": "en",
            "timestamp": str(timestamp),
            "Content-Type": "application/json",
            "signature": signature,
            "User-Agent": self.USER_AGENT,
            "Connection": "close",
        }

    async def _rate_limit(self) -> None:
        """Enforce minimum 1 second between API calls."""
        now = time.time()
        diff = now - self._last_api_call if self._last_api_call != 0 else 1
        if diff < 1:
            await asyncio.sleep(1 - diff + 0.2)
        self._last_api_call = time.time()

    async def _api_request(
        self,
        method: str,
        path: str,
        data: dict | None = None,
    ) -> dict[str, Any]:
        """Make an API request to FoxESS Cloud."""
        await self._rate_limit()

        # Signature must be generated on base path only (without query string)
        signature_path = path.split("?")[0]
        headers = self._generate_signature(signature_path)
        url = f"{self.BASE_URL}{path}"

        try:
            async with async_timeout.timeout(75):
                LOGGER.debug("API Request %s %s", method, url)
                if method == "GET":
                    response = await self._session.get(url, headers=headers)
                else:
                    LOGGER.debug("Request Data: %s", data)
                    response = await self._session.post(url, headers=headers, json=data)
                if response.status in (401, 403):
                    msg = "Invalid API key or unauthorized access"
                    raise FoxessHapaApiClientAuthenticationError(msg)
                result = await response.json()
                LOGGER.debug("result: %s", result)
                response.raise_for_status()

                # Check FoxESS response status
                if result.get("errno") != 0:
                    api_msg = result.get("msg", "Unknown error")
                    if "token" in api_msg.lower() or "auth" in api_msg.lower():
                        raise FoxessHapaApiClientAuthenticationError(api_msg)
                    msg = f"API error: {api_msg}"
                    raise FoxessHapaApiClientError(msg)

                return result

        except TimeoutError as exception:
            msg = f"Timeout error fetching information - {exception}"
            raise FoxessHapaApiClientCommunicationError(msg) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            msg = f"Error fetching information - {exception}"
            raise FoxessHapaApiClientCommunicationError(msg) from exception

    async def async_get_data(self) -> dict[str, Any]:
        """Get all data from FoxESS Cloud (used by coordinator)."""
        device_info = await self.async_get_device_detail()
        real_time = await self.async_get_real_time_data()
        scheduler_groups = None
        if device_info.has_battery:
            scheduler_groups = await self.async_get_schedule_groups()

        return {
            "device_info": device_info,
            "real_time": real_time,
            "scheduler_groups": scheduler_groups,
        }

    async def async_get_device_detail(self) -> FoxessDeviceInfo:
        """Get device details from FoxESS Cloud."""
        path = "/op/v1/device/detail"
        result = await self._api_request("GET", f"{path}?sn={self._device_sn}")

        data = result.get("result", {})
        return FoxessDeviceInfo(
            station_name=data.get("stationName", ""),
            device_sn=data.get("deviceSN", self._device_sn),
            device_type=data.get("deviceType", ""),
            has_battery=data.get("hasBattery", False),
            master_version=data.get("masterVersion", ""),
            manager_version=data.get("managerVersion", ""),
            slave_version=data.get("slaveVersion", ""),
            battery_list=data.get("batteryList"),
        )

    async def async_get_real_time_data(self) -> FoxessRealTimeData:
        """Get real-time data from FoxESS Cloud."""
        path = "/op/v1/device/real/query"
        result = await self._api_request("POST", path, data={"sns": [self._device_sn]})

        # Parse the result - it returns a list of variables
        data = result.get("result", [])
        if isinstance(data, list) and len(data) > 0:
            data = data[0]  # First device in response

        variables = {}
        for var in data.get("datas", []):
            name = var.get("variable", "")
            value = var.get("value", 0)
            variables[name] = value

        # Helper to safely convert values to float or int
        def safe_float(key: str, default: float = 0.0) -> float:
            val = variables.get(key, default)
            return float(val) if val is not None else default

        def safe_int(key: str, default: int = 0) -> int:
            val = variables.get(key, default)
            try:
                return int(val) if val is not None else default
            except (ValueError, TypeError):
                return default

        def safe_str(key: str, default: str = "") -> str:
            val = variables.get(key, default)
            return str(val) if val is not None else default

        # Residual energy is reported in 0.01kWh units, convert to kWh
        residual_energy_raw = safe_float("ResidualEnergy", 0)

        return FoxessRealTimeData(
            # Main power metrics
            pv_power=safe_float("pvPower"),
            battery_soc=safe_float("SoC"),
            battery_power=(
                safe_float("batChargePower") - safe_float("batDischargePower")
            ),
            grid_power=safe_float("meterPower"),
            load_power=safe_float("loadsPower"),
            feed_in_power=safe_float("feedinPower"),
            grid_consumption_power=safe_float("gridConsumptionPower"),
            generation_power=safe_float("generationPower"),
            # PV String 1
            pv1_volt=safe_float("pv1Volt"),
            pv1_current=safe_float("pv1Current"),
            pv1_power=safe_float("pv1Power"),
            # PV String 2
            pv2_volt=safe_float("pv2Volt"),
            pv2_current=safe_float("pv2Current"),
            pv2_power=safe_float("pv2Power"),
            # PV String 3
            pv3_volt=safe_float("pv3Volt"),
            pv3_current=safe_float("pv3Current"),
            pv3_power=safe_float("pv3Power"),
            # PV String 4
            pv4_volt=safe_float("pv4Volt"),
            pv4_current=safe_float("pv4Current"),
            pv4_power=safe_float("pv4Power"),
            # EPS (Emergency Power Supply)
            eps_power=safe_float("epsPower"),
            eps_current_r=safe_float("epsCurrentR"),
            eps_volt_r=safe_float("epsVoltR"),
            eps_power_r=safe_float("epsPowerR"),
            # Grid R-Phase
            r_current=safe_float("RCurrent"),
            r_volt=safe_float("RVolt"),
            r_freq=safe_float("RFreq"),
            r_power=safe_float("RPower"),
            # Temperature sensors
            ambient_temp=safe_float("ambientTemperation"),
            inverter_temp=safe_float("invTemperation"),
            battery_temp=safe_float("batTemperature"),
            # Inverter battery interface
            inv_bat_volt=safe_float("invBatVolt"),
            inv_bat_current=safe_float("invBatCurrent"),
            inv_bat_power=safe_float("invBatPower"),
            # Battery charge/discharge power
            bat_charge_power=safe_float("batChargePower"),
            bat_discharge_power=safe_float("batDischargePower"),
            # Battery direct measurements
            bat_volt=safe_float("batVolt"),
            bat_current=safe_float("batCurrent"),
            # Meter power
            meter_power_2=safe_float("meterPower2"),
            # Energy totals (kWh)
            generation_total=safe_float("generation"),
            residual_energy=residual_energy_raw,
            energy_throughput=safe_float("energyThroughput"),
            grid_consumption_total=safe_float("gridConsumption"),
            loads_total=safe_float("loads"),
            feed_in_total=safe_float("feedin"),
            charge_energy_total=safe_float("chargeEnergyToTal"),
            discharge_energy_total=safe_float("dischargeEnergyToTal"),
            pv_energy_total=safe_float("PVEnergyTotal"),
            # Status
            running_state=safe_str("runningState"),
            battery_status=safe_str("batStatus"),
            battery_status_name=safe_str("batStatusV2"),
            current_fault=safe_str("currentFault"),
            current_fault_count=safe_int("currentFaultCount"),
            raw_variables=variables,
        )

    async def async_get_scheduler(self) -> dict[str, Any]:
        """Get current scheduler settings."""
        path = "/op/v2/device/scheduler/get"
        result = await self._api_request(
            "POST", path, data={"deviceSN": self._device_sn}
        )
        return result.get("result", {})

    async def async_get_schedule_groups(self) -> list[dict[str, Any]]:
        """Get scheduler groups, filtering out zero-duration placeholders."""
        schedule = await self.async_get_scheduler()
        return [
            g
            for g in schedule.get("groups", [])
            if not (
                g.get("startHour") == g.get("endHour")
                and g.get("startMinute") == g.get("endMinute")
            )
        ]

    @staticmethod
    def minimal_group(group: dict[str, Any]) -> dict[str, Any]:
        """Extract minimal required fields from a group for v2 API updates."""
        return {
            "enable": group.get("enable", 1),
            "startHour": group.get("startHour", 0),
            "startMinute": group.get("startMinute", 0),
            "endHour": group.get("endHour", 23),
            "endMinute": group.get("endMinute", 59),
            "workMode": group.get("workMode", "SelfUse"),
        }

    @staticmethod
    def find_current_period_index(groups: list[dict[str, Any]]) -> int | None:
        """Find the index of the schedule period that covers the current time."""
        now = datetime.now().astimezone()
        current_minutes = now.hour * 60 + now.minute

        for i, group in enumerate(groups):
            start_minutes = group.get("startHour", 0) * 60 + group.get("startMinute", 0)
            end_minutes = group.get("endHour", 23) * 60 + group.get("endMinute", 59)

            # Handle periods that span midnight
            if end_minutes < start_minutes:
                if current_minutes >= start_minutes or current_minutes <= end_minutes:
                    return i
            elif start_minutes <= current_minutes <= end_minutes:
                return i

        return None

    @staticmethod
    def create_default_schedule_group(
        work_mode: str = "SelfUse",
        min_soc_on_grid: int = 10,
    ) -> dict[str, Any]:
        """Create a default 24-hour schedule group (v2 format)."""
        return {
            "enable": 1,
            "startHour": 0,
            "startMinute": 0,
            "endHour": 23,
            "endMinute": 59,
            "workMode": work_mode,
            "extraParam": {
                "minSocOnGrid": min_soc_on_grid,
            },
        }

    async def async_set_scheduler(
        self,
        periods: list[dict[str, Any]],
        *,
        enable: bool = True,
    ) -> bool:
        """
        Set scheduler settings (for minSoC and work mode changes).

        This is the main write endpoint for changing battery settings
        and work modes on FoxESS inverters.
        """
        path = "/op/v2/device/scheduler/enable"
        data = {
            "deviceSN": self._device_sn,
            "groups": periods,
            "enable": 1 if enable else 0,
            "isDefault": False,  # Preserve unprovided parameters
        }
        result = await self._api_request("POST", path, data=data)
        return result.get("errno") == 0
