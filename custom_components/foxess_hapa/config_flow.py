"""Config flow for FoxESS HAPA."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import (
    FoxessDeviceInfo,
    FoxessHapaApiClient,
    FoxessHapaApiClientAuthenticationError,
    FoxessHapaApiClientCommunicationError,
    FoxessHapaApiClientError,
)
from .const import CONF_API_KEY, CONF_DEVICE_SERIAL_NUMBER, DOMAIN, LOGGER


class FoxessHapaFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for FoxESS HAPA."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by the user."""
        _errors = {}
        if user_input is not None:
            try:
                device_info = await self._test_credentials(
                    device_serial_number=user_input[CONF_DEVICE_SERIAL_NUMBER],
                    api_key=user_input[CONF_API_KEY],
                )
            except FoxessHapaApiClientAuthenticationError as exception:
                LOGGER.warning(exception)
                _errors["base"] = "auth"
            except FoxessHapaApiClientCommunicationError as exception:
                LOGGER.error(exception)
                _errors["base"] = "connection"
            except FoxessHapaApiClientError as exception:
                LOGGER.exception(exception)
                _errors["base"] = "unknown"
            else:
                # Use device serial number as unique ID
                await self.async_set_unique_id(device_info.device_sn)
                self._abort_if_unique_id_configured()

                # Use station name as title if available
                title = (
                    device_info.station_name or user_input[CONF_DEVICE_SERIAL_NUMBER]
                )
                return self.async_create_entry(
                    title=title,
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_DEVICE_SERIAL_NUMBER,
                        default=(user_input or {}).get(
                            CONF_DEVICE_SERIAL_NUMBER, vol.UNDEFINED
                        ),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.TEXT,
                        ),
                    ),
                    vol.Required(CONF_API_KEY): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD,
                        ),
                    ),
                },
            ),
            errors=_errors,
        )

    async def _test_credentials(
        self, device_serial_number: str, api_key: str
    ) -> FoxessDeviceInfo:
        """Validate credentials by fetching device info."""
        client = FoxessHapaApiClient(
            device_serial_number=device_serial_number,
            api_key=api_key,
            session=async_create_clientsession(self.hass),
        )
        return await client.async_get_device_detail()
