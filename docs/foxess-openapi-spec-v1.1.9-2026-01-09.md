# Fox ESS Cloud Platform Open API Documentation

> **Snapshot Date:** 2026-01-11
> **Source:** https://www.foxesscloud.com/public/i18n/en/OpenApiDocument.html
> **API Version:** V1.1.9 (as of January 9, 2026)

## Overview

This is the complete Open API documentation for the Fox ESS Cloud Platform, providing RESTful endpoints for managing power stations, inverters, energy storage systems, and related devices.

**Base Domain:** `https://www.foxesscloud.com/`

## Authentication

Two authentication methods are supported:

1. **Private Token:** Include `token` header with your API key
2. **OAuth 2.0:** Include `Authorization: Bearer {access_token}` header

Cannot use both simultaneously.

### Required Headers for All Requests

| Parameter | Required | Description |
|-----------|----------|-------------|
| `token` | No* | API key from platform personal center |
| `timestamp` | Yes | Current timestamp in milliseconds |
| `signature` | Yes | MD5 hash of: `url + "\r\n" + token + "\r\n" + timestamp` |
| `lang` | Yes | Language code (e.g., "en") |
| `Authorization` | No* | OAuth 2.0 bearer token |

*One authentication method required

### OAuth 2.0 Flow

1. Redirect user to: `https://{domain}/h5/auth/foxessIndex?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}&scope={scope}`
2. User authorizes; server receives: `{redirect_uri}?code=abc&state=xyz`
3. Exchange code for token: `POST /oauth2/token?grant_type=authorization_code&client_id={client_id}&client_secret={client_secret}&code={code}`
4. Refresh token: `GET /oauth2/refresh?grant_type=refresh_token&client_id={client_id}&client_secret={client_secret}&refresh_token={refresh_token}`
5. Revoke token: `GET /oauth2/revoke?client_id={client_id}&client_secret={client_secret}&access_token={access_token}`
6. Revoke all: `GET /oauth2/revokeAllTokens?client_id={client_id}&client_secret={client_secret}&access_token={access_token}`

## Rate Limiting

- **1440 calls per day** per inverter per account
- **1 call per second** for query interfaces (per interface)
- **1 call per 2 seconds** for insert/update interfaces (per interface)

## Common Error Codes

| Code | Description |
|------|-------------|
| 40256 | Missing request header parameters |
| 40257 | Invalid request body parameters |
| 40400 | Request frequency too high |

---

## API Endpoints

### Power Station Management

#### Create Power Station
- **Path:** `/op/v0/plant/create`
- **Method:** POST
- **Description:** Create a new power station with device configuration

**Request Body Parameters:**
- `devices[]` - Device SNs (for PV/energy-storage stations)
- `pileSN` - Charge pile SN (for charging stations)
- `details` - Station information (name, type, location, capacity, pricing)
- `timezone` - IANA timezone format
- `position` - GPS coordinates and location data
- `electricmeterSN` - Optional meter serial number
- `layoutByMini` - Mini-device layout configuration

**Response:**
- `stationID` - Generated power station ID
- `devices[]` - Device status for each added device

#### Delete Power Station
- **Path:** `/op/v0/plant/delete`
- **Method:** POST
- **Parameters:** `stationID`

#### Edit Power Station
- **Path:** `/op/v0/plant/update`
- **Method:** POST
- **Parameters:** All creation parameters plus `stationID` in details

#### Get Power Station Detail
- **Path:** `/op/v0/plant/detail`
- **Method:** GET
- **Query Parameters:** `id`
- **Response:** Station metadata, user info, installer details, module list

#### Get Power Station List
- **Path:** `/op/v0/plant/list`
- **Method:** POST
- **Body:** `currentPage`, `pageSize`
- **Response:** Paginated station list with IDs, names, timezones

---

### Inverter Management (V1 - Batch Query)

#### Get Device Detail (V1)
- **Path:** `/op/v1/device/detail`
- **Method:** GET
- **Query Parameters:** `sn`
- **Response:** Device info, versions, battery list, support flags

#### Get Device Real-Time Data (V1)
- **Path:** `/op/v1/device/real/query`
- **Method:** POST
- **Body:**
  - `sns[]` - Array of up to 50 device SNs (required)
  - `variables[]` - Specific variables (optional; all if omitted)
- **Response:** Real-time data per device with timestamps

---

### Inverter Management (V0 - Standard)

#### Get Device List
- **Path:** `/op/v0/device/list`
- **Method:** POST
- **Body:** `currentPage`, `pageSize`
- **Response:** Paginated device list with status, type, battery availability

#### Get Device Detail (DEPRECATED)
- **Path:** `/op/v0/device/detail`
- **Method:** GET
- **Query Parameters:** `sn`
- **Response:** Device specifications, firmware versions, battery configuration
- **Note:** Use `/op/v1/device/detail` instead

#### Get Device Real-Time Data (DEPRECATED)
- **Path:** `/op/v0/device/real/query`
- **Method:** POST
- **Body:** `sn` (optional), `variables[]` (optional)
- **Response:** Latest data point for each variable with unit and timestamp
- **Note:** Use `/op/v1/device/real/query` instead

#### Get Device History Data
- **Path:** `/op/v0/device/history/query`
- **Method:** POST
- **Body:**
  - `sn` - Device serial number
  - `variables[]` - Variables to query
  - `begin` - Start timestamp (milliseconds)
  - `end` - End timestamp (milliseconds)
- **Response:** Time-series data points within 24-hour windows

#### Get Device Production Report
- **Path:** `/op/v0/device/report/query`
- **Method:** POST
- **Body:**
  - `sn` - Device SN
  - `year`, `month`, `day` - Date parameters
  - `dimension` - "year", "month", or "day"
  - `variables[]` - Report variables (generation, feedin, gridConsumption, chargeEnergyToTal, dischargeEnergyToTal, PVEnergyTotal)

#### Get Device Production Report Statistic
- **Path:** `/op/v0/device/report/statistic`
- **Method:** POST
- **Similar to production report with aggregated statistics**

#### Get Device Battery Real Data
- **Path:** `/op/v0/device/battery/real/query`
- **Method:** POST
- **Body:** `sn`
- **Response:** Battery capacity, remaining capacity, energy, SOC, SOH, backup info

#### Get Device Power Generation
- **Path:** `/op/v0/device/generation`
- **Method:** GET
- **Query Parameters:** `sn`
- **Response:** Today's yield, monthly yield, cumulative generation (kWh)

---

### Device Configuration

#### Get Available Variables
- **Path:** `/op/v0/device/variable/get`
- **Method:** GET
- **Response:** Comprehensive variable table with units and multilingual names

#### Get Error Code Information
- **Path:** `/op/v0/device/fault/get`
- **Method:** GET
- **Response:** Error code mappings in Chinese and English

#### Battery SOC Management

**Get Minimum SOC Settings:**
- **Path:** `/op/v0/device/battery/soc/get`
- **Method:** GET
- **Query Parameters:** `sn`
- **Response:** `minSoc`, `minSocOnGrid`

**Set Minimum SOC:**
- **Path:** `/op/v0/device/battery/soc/set`
- **Method:** POST
- **Body:** `sn`, `minSoc` (10-100), `minSocOnGrid` (10-100)

#### Battery Charging Time

**Get Charging Time:**
- **Path:** `/op/v0/device/battery/forceChargeTime/get`
- **Method:** GET
- **Query Parameters:** `sn`
- **Response:** Two configurable time periods with enable flags and hour/minute values

**Set Charging Time:**
- **Path:** `/op/v0/device/battery/forceChargeTime/set`
- **Method:** POST
- **Body:** `sn`, `enable1`, `enable2`, time objects for both periods
  - Each time period: `startTime{1|2}` and `endTime{1|2}` with `hour` and `minute` fields

#### Device Settings

**Get Setting:**
- **Path:** `/op/v0/device/setting/get`
- **Method:** POST
- **Body:** `sn`, `key` (ExportLimit, MinSoc, MinSocOnGrid, MaxSoc, GridCode, WorkMode, etc.)
- **Response:** Value, unit, precision, valid range

**Set Setting:**
- **Path:** `/op/v0/device/setting/set`
- **Method:** POST
- **Body:** `sn`, `key`, `value` (as string)

#### Device Time Management

**Get Device Time:**
- **Path:** `/op/v0/device/time/get`
- **Method:** POST
- **Body:** `sn`
- **Response:** Year, month, day, hour, minute, second

**Set Device Time:**
- **Path:** `/op/v0/device/time/set`
- **Method:** POST
- **Body:** `sn`, `year` (0-99), `month` (1-12), `day` (1-31), `hour` (0-23), `minute` (0-59), `second` (0-59)
- **Note:** "Automatic time synchronization will be disabled after modification"

#### Peak Shaving Settings

**Get Peak Shaving:**
- **Path:** `/op/v0/device/peakShaving/get`
- **Method:** POST
- **Body:** `sn`
- **Response:** `importLimit` and `soc` with ranges

**Set Peak Shaving:**
- **Path:** `/op/v0/device/peakShaving/set`
- **Method:** POST
- **Body:** `sn`, `importLimit` (number), `soc` (integer)

#### Meter Reader

**Get Meter Reader:**
- **Path:** `/op/v0/device/getMeterReader`
- **Method:** POST
- **Body:** `sn`
- **Response:** Reader type, status, connection info (IP, password)
- **Types:** 0 (close), 1 (SolarmanPV), 2 (EARN-E), 3 (SHELLY), 4 (WIZARD), 5 (Chint), 6 (AECC), 8 (iometer), 9 (Shelly Pro EM-50), 10 (Powerfox), 11 (Shelly 3EM), 12 (Solakon)

**Set Meter Reader:**
- **Path:** `/op/v0/device/setMeterReader`
- **Method:** POST
- **Body:** `sn`, `readerType`, `readerInfo` (IP and password)

#### Battery Heating Parameters

**Get Heating Parameters:**
- **Path:** `/op/v0/device/batteryHeating/get`
- **Method:** POST
- **Body:** `sn`
- **Response:** Detailed parameter list with ranges and enumerations

**Set Heating Parameters:**
- **Path:** `/op/v0/device/batteryHeating/set`
- **Method:** POST
- **Body:** `sn`, `batteryWarmUpEnable`, `startTemperature`, `endTemperature`, three time periods with enable flags and hour/minute values

---

### Scheduler Management

#### Scheduler V2 (Latest)

**Get Time Segment Information:**
- **Path:** `/op/v2/device/scheduler/get`
- **Method:** POST
- **Body:** `deviceSN`
- **Response:** Master switch state, 8 configurable time groups with work modes and extended parameters

**Set Time Segment Information:**
- **Path:** `/op/v2/device/scheduler/enable`
- **Method:** POST
- **Body:** `deviceSN`, `isDefault` (optional, default false), `groups[]` with optional `extraParam` object
- **Parameters per group:**
  - `enable`, `startHour`, `startMinute`, `endHour`, `endMinute`
  - `workMode` (SelfUse, Feedin, Backup, ForceCharge, ForceDischarge)
  - `extraParam` (optional): `minSocOnGrid`, `fdSoc`, `fdPwr`, `maxSoc`, `importLimit`, `exportLimit`, `pvLimit`, `reactivePower`

---

#### Scheduler V1

**Get Main Switch Status:**
- **Path:** `/op/v1/device/scheduler/get/flag`
- **Method:** POST
- **Body:** `deviceSN`
- **Response:** `support` (0/1), `enable` (0/1)

**Set Main Switch Status:**
- **Path:** `/op/v1/device/scheduler/set/flag`
- **Method:** POST
- **Body:** `deviceSN`, `enable` (0/1)

**Get Time Segment Information:**
- **Path:** `/op/v1/device/scheduler/get`
- **Method:** POST
- **Body:** `deviceSN`
- **Response:** 8 groups with work modes and SOC/power settings

**Set Time Segment Information:**
- **Path:** `/op/v1/device/scheduler/enable`
- **Method:** POST
- **Body:** `deviceSN`, `groups[]` with parameters:
  - `enable`, `startHour`, `startMinute`, `endHour`, `endMinute`
  - `workMode`, `minSocOnGrid` (10-100), `fdSoc`, `fdPwr` (0-6000)
  - `maxSoc` (optional, for V1)

---

#### Scheduler V0 (DEPRECATED)

**Get Main Switch Status (DEPRECATED):**
- **Path:** `/op/v0/device/scheduler/get/flag`
- **Method:** POST
- **Body:** `deviceSN`
- **Response:** Support and enable flags

**Get Time Segment Information (DEPRECATED):**
- **Path:** `/op/v0/device/scheduler/get`
- **Method:** POST
- **Body:** `deviceSN`
- **Response:** Master switch state, 8 groups (no optional parameters)

**Set Main Switch Status (DEPRECATED):**
- **Path:** `/op/v0/device/scheduler/set/flag`
- **Method:** POST
- **Body:** `deviceSN`, `enable` (0/1)

**Set Time Segment Information (DEPRECATED):**
- **Path:** `/op/v0/device/scheduler/enable`
- **Method:** POST
- **Body:** `deviceSN`, `groups[]` with same structure as V1

---

### Data Logger (Collector) Management

#### Get Data Logger Signal
- **Path:** `/op/v0/module/getSignal`
- **Method:** POST
- **Body:** `sn`
- **Response:** Timestamp, signal strength in dBm

#### Get Data Logger List
- **Path:** `/op/v0/module/list`
- **Method:** POST
- **Body:** `currentPage`, `pageSize` (10-1000)
- **Response:** Paginated list with SN, station ID, status (1 online/2 offline), signal strength (0-100), version info

#### Modbus Commands
- **Path:** `/op/v0/module/modbus/commands`
- **Method:** POST
- **Body:** `sn`, `data` (base64-encoded), `timeout` (optional, default 10s)
- **Response:** `data` (base64-encoded response)

---

### EMS (Energy Management System)

#### AC Output Control Setting

**Get:**
- **Path:** `/op/v0/ems/setting/acOutput/get`
- **Method:** GET
- **Query Parameters:** `sn`
- **Response:** DRM enable, ripple control, and 4 piecewise control values (0-100%)

**Set:**
- **Path:** `/op/v0/ems/setting/acOutput/set`
- **Method:** POST
- **Body:** `sn`, `drmEnable`, `rippleControl`, `rippleControlPiecewise{1-4}`

#### Generator Setting

**Get:**
- **Path:** `/op/v0/ems/setting/gen/get`
- **Method:** GET
- **Query Parameters:** `sn`
- **Response:** Enable flag, start/stop SOC, charge power, judge time, reset time, meter compensation

**Set:**
- **Path:** `/op/v0/ems/setting/gen/set`
- **Method:** POST
- **Body:** `sn`, all above parameters

#### More Settings

**Get:**
- **Path:** `/op/v0/ems/setting/more/get`
- **Method:** GET
- **Query Parameters:** `sn`
- **Response:** Control mode, control cycle, grid export control delta

**Set:**
- **Path:** `/op/v0/ems/setting/more/set`
- **Method:** POST
- **Body:** `sn`, `controlMode`, `controlCycle`, `gridExportControlDelta`

#### Power Limit Control Setting

**Get:**
- **Path:** `/op/v0/ems/setting/powerLimit/get`
- **Method:** GET
- **Query Parameters:** `sn`
- **Response:** Enable flag, grid export/import limits, peak shaving limits, AC output limits

**Set:**
- **Path:** `/op/v0/ems/setting/powerLimit/set`
- **Method:** POST
- **Body:** `sn`, all limit parameters

#### Rate Setting

**Get:**
- **Path:** `/op/v0/ems/setting/rate/get`
- **Method:** POST
- **Body:** `emsID`, `port`
- **Response:** Data bit (5-8), stop bit (1/1.5/2), parity (0/1/2), baud rate

**Set:**
- **Path:** `/op/v0/ems/setting/rate/set`
- **Method:** POST
- **Body:** `emsID`, `port`, `rate`, `dataBit`, `stopBit`, `parityBit`

#### System Setting

**Get:**
- **Path:** `/op/v0/ems/setting/system/get`
- **Method:** GET
- **Query Parameters:** `emsID`
- **Response:** General settings (DRM, ripple control, data cycle), parallel control config, power limits

**Set:**
- **Path:** `/op/v0/ems/setting/system/set`
- **Method:** POST
- **Body:** `emsID`, `general` object, `parallelControl` object, `powerLimit` object

#### EMS List
- **Path:** `/op/v0/ems/list`
- **Method:** POST
- **Body:** `currentPage`, `pageSize`
- **Response:** Paginated list with ID, SN, plant ID, product type, status (0 online/1 offline)

---

### Meter Management

#### Get Meter List
- **Path:** `/op/v0/gw/list`
- **Method:** POST
- **Body:** `currentPage`, `pageSize`
- **Response:** Paginated list with SN, station ID, status (1 online/2 fault/3 offline)

#### Get Meter Settings
- **Path:** `/op/v0/gw/setting/get`
- **Method:** POST
- **Body:** `sn`
- **Response:** Mode, feedin power, output/input max current, voltage thresholds, on/off power, device quantity

#### Set Meter Settings
- **Path:** `/op/v0/gw/setting/set`
- **Method:** POST
- **Body:** `sn`, `mode`, optional mode-specific parameters (feedinPower, currentLimits, voltage thresholds)

---

### Heat Pump Management

#### Heat Pump Register
- **Path:** `/op/v0/heat/register`
- **Method:** POST
- **Body:** `sn` (outdoor unit SN)

#### Heat Pump Register List
- **Path:** `/op/v0/register/heat/list`
- **Method:** POST
- **Body:** `currentPage`, `pageSize`, `sn`
- **Response:** Heat SN, module SN, register status, running status (1 online/2 fault/3 offline), version, device type

#### Heat Pump Register Status Change
- **Path:** `/op/v0/heat/register/status/change`
- **Method:** POST
- **Body:** `sn`, `status` (pending, approved, revoked)

---

### GMAX (Energy Storage) Management

#### Get GMAX List
- **Path:** `/op/v0/gmax/list`
- **Method:** POST
- **Body:** `currentPage`, `pageSize`
- **Response:** Device ID/SN, complete machine SN, PCS/BMS/PACK SNs, plant ID, communication status

#### Get GMAX History Data
- **Path:** `/op/v0/gmax/history/query`
- **Method:** POST
- **Body:** `sn`, `begin`, `end` (within 24-hour window)
- **Response:** Time-series data with SOC/SOH (%), charging/discharging power (kW), status (0 shutdown/1 charging/2 discharge/3 standby/4 fault)

#### Get GMAX Real Data
- **Path:** `/op/v0/gmax/real/query`
- **Method:** POST
- **Body:** `sn`
- **Response:** Current charging/discharging power (kW), SOC/SOH (%), status

#### Get Peak and Valley Arbitrage
- **Path:** `/op/v0/gmax/peakValleyPower/get`
- **Method:** POST
- **Body:** `sn`
- **Response:** Up to 8 periods with enable flag, power (kW), start/end time (seconds), SOC threshold, work mode (0 time/1 month/2 year), week days (1-7), timestamp

#### Set Peak and Valley Arbitrage
- **Path:** `/op/v0/gmax/peakValleyPower/set`
- **Method:** POST
- **Body:** `sn`, `peakEnable`, `datas[]` array with period configurations

---

### Platform Access

#### Get Access Count
- **Path:** `/op/v0/user/getAccessCount`
- **Method:** GET
- **Response:** `total` (total allowed calls), `remaining` (available calls)

#### Installer Device Count
- **Path:** `/op/v0/device/installer/count`
- **Method:** POST
- **Response:** Array of year/country/device count objects

---

## Variable Reference Table

The API supports numerous device variables across PV systems and energy storage. Categories include:

**Power Variables:**
- `pvPower`, `pv{1-24}Power` - Photovoltaic output
- `RCurrent`, `RVolt`, `RFreq`, `RPower` (R-phase)
- `SCurrent`, `SVolt`, `SFreq`, `SPower` (S-phase)
- `TCurrent`, `TVolt`, `TFreq`, `TPower` (T-phase)
- `generationPower`, `feedinPower`, `gridConsumptionPower`
- `loadsPower`, `meterPower`, `batChargePower`, `batDischargePower`

**Energy Variables:**
- `generation`, `feedin`, `gridConsumption`
- `chargeEnergyToTal`, `dischargeEnergyToTal`
- `PVEnergyTotal`, `loads`, `ResidualEnergy`

**Battery Variables:**
- `SoC` (State of Charge), `SOH` (State of Health)
- `batVolt`, `batCurrent`, `batTemperature`
- `invBatVolt`, `invBatCurrent`, `invBatPower`
- `energyThroughput` - Battery throughput (kWh)

**Status Variables:**
- `runningState` (160-170 enumeration)
- `batStatus`, `batStatusV2`
- `currentFault`, `currentFaultCount`

**Temperature Variables:**
- `ambientTemperation`, `boostTemperation`, `invTemperation`
- `chargeTemperature`, `dspTemperature`

**Other Variables:**
- `ReactivePower` (kVar), `PowerFactor`
- `epsPower`, `epsCurrentR/S/T`, `epsVoltR/S/T`, `epsPowerR/S/T`

All variables include multilingual names (zh_CN, en, de, pt, fr, pl) and units.

---

## Version History

| Date | Version | Changes |
|------|---------|---------|
| 2023/11/30 | V1.0.1 | Added SN parameter for real-time/historical data |
| 2023/12/18 | V1.0.2 | Variable names interface; unlimited variable queries |
| 2024/01/12 | V1.0.3 | Power generation, reports, battery settings, lists |
| 2024/06/13 | V1.0.4 | Battery throughput variables |
| 2024/08/19 | V1.0.5 | V1 real-time data interface with batch queries |
| 2024/09/13 | V1.0.6 | Device parameter settings support ExportLimit |
| 2024/10/18 | V1.0.7 | H1 series support |
| 2024/11/27 | V1.0.8 | Device time modification, safety regulations |
| 2024/12/28 | V1.0.9 | SOH variable, PV generation in reports |
| 2025/02/13 | V1.0.10 | Scheduler V1 with max SOC |
| 2025/02/18 | V1.0.11 | Battery info in device details |
| 2025/03/20 | V1.1.0 | OAuth 2.0 support |
| 2025/04/10 | V1.1.1 | New model support |
| 2025/05/12 | V1.1.2 | Meter support, peak shaving |
| 2025/06/03 | V1.1.3 | Battery model/capacity, work mode parameters |
| 2025/07/24 | V1.1.4 | Micro-reverse/storage functions |
| 2025/08/13 | V1.1.5 | Communication device signal strength |
| 2025/10/21 | V1.1.6 | Battery heating, Modbus, Scheduler V2 |
| 2025/10/31 | V1.1.7 | MicroStorage LCD, ecomode, EMS |
| 2025/11/28 | V1.1.8 | GMAX enhancements |
| 2026/01/09 | V1.1.9 | AI Link/EMS settings, collector version |
