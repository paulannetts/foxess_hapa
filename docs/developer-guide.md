# FoxESS HAPA Developer Guide

## Setup

```bash
# Install dependencies
scripts/setup

# Run Home Assistant with the integration (debug mode)
scripts/develop
```

`scripts/develop` starts Home Assistant with `PYTHONPATH` pointing at `custom_components/`, using `config/` for HA configuration. Logging for the integration is set to `debug` in `config/configuration.yaml`.

---

## Mock / Simulated Data Mode

When developing without physical hardware, the integration supports a mock mode that returns realistic simulated data — no FoxESS Cloud API access required.

### Enabling mock mode

Set the `FOXESS_MOCK_API` environment variable before starting Home Assistant:

```bash
FOXESS_MOCK_API=true scripts/develop
```

Accepted values: `1`, `true`, `yes` (case-insensitive). Any other value (or absence of the variable) uses the real API.

### What mock mode does

When enabled, `MockFoxessHapaApiClient` (`custom_components/foxess_hapa/mock_api.py`) is used instead of the real API client. It:

- **Skips credential validation** during the config flow — any device serial and API key are accepted.
- **Simulates a 6 kW solar array + 10 kWh battery** with time-of-day behaviour:
  - Solar generation follows a sine curve between 06:00–20:00 UTC (peaks at noon), with random cloud variation.
  - Household load varies by time: morning peak (06–09), daytime low (09–17), evening peak (17–22), night base load.
  - Battery charges from surplus solar (max 3 kW), discharges for load deficit (max 3 kW), respecting min SoC.
  - Grid import/export is derived from the balance.
- **Polls every 1 minute** instead of the normal 5 minutes, so changes are visible quickly.
- **Persists state between polls** — battery SoC evolves across calls.
- **Accepts scheduler writes** (`async_set_scheduler`) and updates internal work mode / min SoC state.

A `WARNING` log line is emitted at startup confirming mock mode is active:

```
FOXESS_MOCK_API is enabled - using mock API client with simulated data
```

### Simulated device details

| Field | Value |
|---|---|
| Station name | `Mock Solar Station` |
| Device type | `H3-6.0-E` |
| Battery | `HV2600`, 10 kWh |
| Firmware versions | master `1.54`, manager `1.02`, slave `1.01` |

---

## Testing Against a Real System

To test against a live FoxESS inverter you need:

1. **Device serial number** — visible on the inverter label and in the FoxESS Cloud portal under *Device > Details*.
2. **API key** — generated in the FoxESS Cloud portal under *User Centre > API Management*.

### Setting credentials for local development

The integration stores credentials in the Home Assistant config entry (entered via the UI config flow). For local dev, start `scripts/develop`, navigate to **Settings → Devices & Services → Add Integration**, search for *FoxESS HAPA*, and enter the serial number and API key.

Credentials are stored in `config/.storage/core.config_entries` and persist across restarts of the dev server.

> **Note:** Make sure `FOXESS_MOCK_API` is **not** set (or is set to any value other than `1`/`true`/`yes`) when testing against a real system.

### Rate limiting

The real API client enforces a minimum of 1 second between requests (FoxESS Cloud requirement). The coordinator polls every 5 minutes. Avoid running multiple dev instances simultaneously against the same API key.

---

## Logging

Debug logging for the integration is enabled by default in `config/configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.foxess_hapa: debug
```

Home Assistant is also started with `--debug` flag via `scripts/develop`, which enables HA-level debug output alongside integration logs.
