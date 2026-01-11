"""FoxESS Cloud API Client."""

from __future__ import annotations

import asyncio
import hashlib
import socket
import time
from dataclasses import dataclass
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

    pv_power: float = 0.0
    battery_soc: float = 0.0
    battery_power: float = 0.0
    grid_power: float = 0.0
    load_power: float = 0.0
    feed_in_power: float = 0.0
    grid_consumption_power: float = 0.0
    generation_power: float = 0.0
    raw_variables: dict[str, Any] | None = None


@dataclass
class FoxessBatterySettings:
    """Battery settings from FoxESS Cloud."""

    min_soc: int = 10
    min_soc_on_grid: int = 10


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
        signature_text = f"{path}\r\n{self._api_key}\r\n{timestamp}"
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

        headers = self._generate_signature(path)
        url = f"{self.BASE_URL}{path}"

        try:
            async with async_timeout.timeout(75):
                LOGGER.debug("API Request %s %s", method, url)
                LOGGER.debug("API Readers %s", headers)
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
        battery_settings = None
        if device_info.has_battery:
            battery_settings = await self.async_get_battery_settings()

        return {
            "device_info": device_info,
            "real_time": real_time,
            "battery_settings": battery_settings,
        }

    async def async_get_device_detail(self) -> FoxessDeviceInfo:
        """Get device details from FoxESS Cloud."""
        path = "/op/v0/device/detail"
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
        path = "/op/v0/device/real/query"
        result = await self._api_request("POST", path, data={"sn": self._device_sn})

        # Parse the result - it returns a list of variables
        data = result.get("result", [])
        if isinstance(data, list) and len(data) > 0:
            data = data[0]  # First device in response

        variables = {}
        for var in data.get("datas", []):
            name = var.get("variable", "")
            value = var.get("value", 0)
            variables[name] = value

        return FoxessRealTimeData(
            pv_power=variables.get("pvPower", 0),
            battery_soc=variables.get("SoC", 0),
            battery_power=(
                variables.get("batChargePower", 0)
                - variables.get("batDischargePower", 0)
            ),
            grid_power=variables.get("meterPower", 0),
            load_power=variables.get("loadsPower", 0),
            feed_in_power=variables.get("feedinPower", 0),
            grid_consumption_power=variables.get("gridConsumptionPower", 0),
            generation_power=variables.get("generationPower", 0),
            raw_variables=variables,
        )

    async def async_get_battery_settings(self) -> FoxessBatterySettings:
        """Get battery settings from FoxESS Cloud."""
        path = "/op/v0/device/battery/soc/get"
        result = await self._api_request("GET", f"{path}?sn={self._device_sn}")

        data = result.get("result", {})
        return FoxessBatterySettings(
            min_soc=data.get("minSoc", 10),
            min_soc_on_grid=data.get("minSocOnGrid", 10),
        )

    async def async_get_scheduler(self) -> dict[str, Any]:
        """Get current scheduler settings."""
        path = "/op/v0/device/scheduler/get"
        result = await self._api_request("POST", path, data={"sn": self._device_sn})
        return result.get("result", {})

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
        path = "/op/v0/device/scheduler/enable"
        data = {
            "sn": self._device_sn,
            "groups": periods,
            "enable": 1 if enable else 0,
        }
        result = await self._api_request("POST", path, data=data)
        return result.get("errno") == 0
