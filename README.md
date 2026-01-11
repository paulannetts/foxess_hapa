# FoxESS HAPA

A Home Assistant custom component for FoxESS inverters using the FoxESS Cloud API.

## Features

- Real-time monitoring of your FoxESS solar/battery system
- 45+ sensors covering power, energy, temperatures, and status
- Control battery work mode and minimum SoC settings
- Uses the official FoxESS Cloud API (v1/v2)

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the menu (three dots) and select "Custom repositories"
3. Add `https://github.com/paulannetts/foxess_hapa` with category "Integration"
4. Click "Add", then find "FoxESS HAPA" and click "Download"
5. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/foxess_hapa` folder to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

1. Go to Settings > Devices & Services > Add Integration
2. Search for "FoxESS HAPA"
3. Enter your device serial number and API key from [FoxESS Cloud](https://www.foxesscloud.com/)

## Available Entities

### Sensors (45)

**Power Metrics:**
- PV Power, Generation Power
- Battery Power, Charge Power, Discharge Power
- Grid Power, Grid Consumption Power, Feed-in Power
- Load Power

**PV Strings (PV1-4):**
- Voltage, Current, Power for each string

**EPS (Emergency Power Supply):**
- EPS Power, R-phase Current, Voltage, Power

**Grid Phase:**
- R Current, R Voltage, Frequency, R Power

**Temperature:**
- Ambient, Inverter, Battery

**Battery:**
- SoC, Voltage, Current
- Inverter Battery Voltage, Current, Power

**Energy Totals (kWh):**
- Total Generation, PV Energy Total
- Grid Consumption Total, Feed-in Total, Loads Total
- Charge Energy Total, Discharge Energy Total
- Battery Throughput, Residual Energy

**Status:**
- Running State, Battery Status, Fault Info

### Binary Sensors (4)

- Has Battery
- Battery Charging
- Battery Discharging
- Grid Exporting

### Controls

- **Work Mode** (Select): SelfUse, ForceCharge, ForceDischarge, Backup, FeedInFirst
- **Min SoC on Grid** (Number): 10-100%

## API Rate Limits

FoxESS Cloud allows 1,440 API calls per day. This integration polls every 5 minutes, making 2 API calls per poll (device detail + real-time data), plus scheduler calls for battery-equipped devices (~576-864 calls/day), well within limits.

## Development

```bash
# Install dependencies
scripts/setup

# Run Home Assistant with the integration
scripts/develop

# Lint and format code
scripts/lint
```

## License

MIT License - see [LICENSE](LICENSE) file.
