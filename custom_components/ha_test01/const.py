"""Constants for ha_test01."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "ha_test01"
ATTRIBUTION = "Data provided by http://jsonplaceholder.typicode.com/"

CONF_DEVICE_SERIAL_NUMBER = "device_serial_number"
CONF_API_KEY = "api_key"
