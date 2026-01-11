# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FoxESS HAPA is a Home Assistant custom component integration for FoxESS solar inverters. It connects to the FoxESS Cloud API to provide real-time monitoring and control of solar/battery systems.

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

### Integration Structure (`custom_components/foxess_hapa/`)

The integration follows standard Home Assistant patterns:

- **`__init__.py`**: Entry point. Sets up the integration via `async_setup_entry()`, creates the API client and coordinator, and forwards platform setup to entity modules.

- **`config_flow.py`**: UI-based configuration flow (`FoxessHapaFlowHandler`). Handles user input for device serial number and API key, validates credentials before creating config entries.

- **`coordinator.py`**: `FoxessHapaDataUpdateCoordinator` extends HA's `DataUpdateCoordinator` for polling API data every 5 minutes. Handles authentication and communication errors appropriately.

- **`api.py`**: `FoxessHapaApiClient` - async API client using aiohttp for FoxESS Cloud API. Key components:
  - `FoxessDeviceInfo` dataclass - device metadata (serial, versions, battery info)
  - `FoxessRealTimeData` dataclass - 45+ real-time measurements
  - Rate limiting (1 req/sec) and MD5 signature authentication
  - Custom exception hierarchy (`FoxessHapaApiClientError`, `*AuthenticationError`, `*CommunicationError`)

- **`entity.py`**: Base `FoxessHapaEntity` class extending `CoordinatorEntity`. All platform entities inherit from this.

- **`data.py`**: Type definitions including `FoxessHapaData` dataclass and `FoxessHapaConfigEntry` type alias.

- **`const.py`**: Constants including `DOMAIN`, config keys, and logger.

- **Platform files**:
  - `sensor.py` - 45 sensors (power, energy, temperature, status)
  - `binary_sensor.py` - 4 binary sensors (battery state, grid export)
  - `number.py` - Min SoC setting (10-100%)
  - `select.py` - Work mode control (SelfUse, ForceCharge, etc.)

### Data Flow

1. User configures integration via config flow (device serial + API key)
2. `async_setup_entry` creates `FoxessHapaApiClient` and `FoxessHapaDataUpdateCoordinator`
3. Coordinator polls API every 5 minutes via `_async_update_data()`
4. Coordinator data contains: `device_info`, `real_time`, `scheduler_groups`
5. Entities read data from `coordinator.data` in their property methods

### FoxESS Cloud API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/op/v1/device/detail` | GET | Device info, firmware versions |
| `/op/v1/device/real/query` | POST | Real-time sensor data |
| `/op/v2/device/scheduler/get` | POST | Current scheduler/battery settings |
| `/op/v2/device/scheduler/enable` | POST | Update work mode and minSoC |

### Key Data Structures

**FoxessRealTimeData** contains:
- Power metrics: `pv_power`, `battery_power`, `grid_power`, `load_power`, `feed_in_power`, etc.
- PV strings: `pv1_volt`, `pv1_current`, `pv1_power` (x4 strings)
- EPS: `eps_power`, `eps_volt_r`, `eps_current_r`, `eps_power_r`
- Grid phase: `r_volt`, `r_current`, `r_freq`, `r_power`
- Temperature: `ambient_temp`, `inverter_temp`, `battery_temp`
- Battery: `battery_soc`, `bat_volt`, `bat_current`, `inv_bat_volt`, etc.
- Energy totals: `generation_total`, `grid_consumption_total`, `feed_in_total`, etc.
- Status: `running_state`, `battery_status`, `battery_status_name`, `current_fault`

### Configuration Constants

- `CONF_DEVICE_SERIAL_NUMBER` - Device identifier (from FoxESS Cloud)
- `CONF_API_KEY` - API authentication key (from FoxESS Cloud portal)
