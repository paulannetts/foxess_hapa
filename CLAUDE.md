# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Home Assistant custom component integration (`ha_test01`). 

## Development Commands

```bash
# Install dependencies
scripts/setup

# Run Home Assistant with the integration (in debug mode)
scripts/develop

# Lint and format code
scripts/lint
```

The `scripts/develop` command starts Home Assistant with the custom component loaded via PYTHONPATH, using the `config/` directory for HA configuration.

## Linting

Uses Ruff for linting and formatting (Python 3.13 target):
- `ruff format .` - Format code
- `ruff check . --fix` - Lint with auto-fix
- Configuration in `pyproject.toml` under `[tool.ruff]` - uses `ALL` rules with specific ignores

CI runs both hassfest and HACS validation on PRs to main.

## Architecture

### Integration Structure (`custom_components/ha_test01/`)

The integration follows standard Home Assistant patterns:

- **`__init__.py`**: Entry point. Sets up the integration via `async_setup_entry()`, creates the API client and coordinator, and forwards platform setup to entity modules.

- **`config_flow.py`**: UI-based configuration flow (`HaTest01FlowHandler`). Handles user input for device serial number and API key, validates credentials before creating config entries.

- **`coordinator.py`**: `BlueprintDataUpdateCoordinator` extends HA's `DataUpdateCoordinator` for polling API data. Handles authentication and communication errors appropriately.

- **`api.py`**: `HaTest01ApiClient` - async API client using aiohttp. Includes custom exception hierarchy (`HaTest01ApiClientError`, `HaTest01ApiClientAuthenticationError`, `HaTest01ApiClientCommunicationError`).

- **`entity.py`**: Base `HaTest01Entity` class extending `CoordinatorEntity`. All platform entities inherit from this.

- **`data.py`**: Type definitions including `HaTest01Data` dataclass (holds client, coordinator, integration) and `HaTest01ConfigEntry` type alias.

- **`const.py`**: Constants including `DOMAIN`, config keys (`CONF_DEVICE_SERIAL_NUMBER`, `CONF_API_KEY`), and logger.

- **Platform files** (`sensor.py`, `binary_sensor.py`, `switch.py`): Entity implementations following HA platform patterns.

### Data Flow

1. User configures integration via config flow (device serial + API key)
2. `async_setup_entry` creates `HaTest01ApiClient` and `BlueprintDataUpdateCoordinator`
3. Coordinator polls API on interval (default: 1 hour) via `_async_update_data()`
4. Entities read data from `coordinator.data` in their property methods

### Key Configuration Constants

- `CONF_DEVICE_SERIAL_NUMBER` - Device identifier
- `CONF_API_KEY` - API authentication key