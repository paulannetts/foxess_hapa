# Fox ESS Cloud Platform Open API Documentation

> **Snapshot Date:** 2026-09-07
> **Source:** https://www.foxesscloud.com/public/i18n/en/OpenApiDocument.html
> **API Version:** V1.1.18 (as of May 29, 2026)

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
- ⚠️ **No longer documented as of V1.1.18.** Present in V1.1.9, absent from the
  current published docs with no changelog entry. It may still function — treat as
  undocumented rather than confirmed-removed.

#### Get Device Battery Real Data
- **Path:** `/op/v0/device/battery/real/query`
- **Method:** POST
- **Body:** `sn`
- **Response:** Battery capacity, remaining capacity, energy, SOC, SOH, backup info
- ⚠️ **No longer documented as of V1.1.18.** Present in V1.1.9, absent from the
  current published docs with no changelog entry. It may still function — treat as
  undocumented rather than confirmed-removed.

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

#### Get Device Fault History
- **Path:** `/op/v0/device/fault/history`
- **Method:** POST
- **Response:** Historical faults with Unix timestamp (ms) of occurrence
- **Added:** V1.1.13

#### Display Sleep Settings
**Get:**
- **Path:** `/op/v0/device/displaySleep/get`
- **Method:** POST

**Set:**
- **Path:** `/op/v0/device/displaySleep/set`
- **Method:** POST
- **Body:** Three time windows (`time{1|2|3}StartHour`/`StartMinute`,
  `time{1|2|3}EndHour`/`EndMinute`) with enable flags

#### Device Boarding Status
**Get:**
- **Path:** `/op/v0/device/boarding/status`
- **Method:** GET
- **Query Parameters:** `sn`
- **Auth:** OAuth bearer token
- **Added:** V1.1.11 (retrieve endpoint V1.1.15)

**Set:**
- **Path:** `/op/v0/device/boarding/status/set`
- **Method:** POST

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

Four generations coexist. **V3 is current**; V2 remains supported and is what this
integration uses today. V0 is deprecated.

#### Scheduler V3 (Current — added in V1.1.10, 2026-02-06)

**Get Time Segment Information:**
- **Path:** `/op/v3/device/scheduler/get`
- **Method:** POST
- **Body:** `deviceSN`
- **Response:**
  - `enable` (string) - master switch state (0:off 1:on)
  - `groups[]` - configured time segments (see field table below)
  - `maxGroupCount` (number) - **maximum groups supported by this device**; do not
    assume 8
  - `properties` - per-field range metadata (see *Properties block* below)

**Set Time Segment Information:**
- **Path:** `/op/v3/device/scheduler/enable`
- **Method:** POST
- **Body:** `deviceSN`, `isDefault` (optional, default `false`), `groups[]`
- **Response:** echoes `deviceSN`, `isDefault` and the accepted `groups[]` on success
  (behaviour introduced in V1.1.12)

**Batch Set Time Segment Information:**
- **Path:** `/op/v3/device/scheduler/enable/batch`
- **Method:** POST
- **Body:** `deviceSNList[]` (max 50 devices), `groups[]`, `notifyChannel`
  (`none` | `webhook`), `isDefault` (optional), `requestId` (optional idempotency
  key, max 64 chars), `webhook` (optional `{url, secret}` override; URL must be HTTPS)
- **Validation is all-or-nothing:** if any device is invalid/unauthorised or any
  segment is invalid, the entire request is rejected and no task is submitted.
- **Asynchronous:** returns `ACCEPTED` immediately with `requestId`, `total`,
  `accepted`; it does not wait for devices to finish.
- **Webhook signature:** read `X-Foxess-Timestamp`, `X-Foxess-Nonce`,
  `X-Foxess-Signature`; sign `timestamp + "\n" + nonce + "\n" + rawBody` with
  HMAC-SHA256 using the webhook secret, hex-encoded lowercase, compared
  constant-time against the value after `sha256=`. Use `X-Foxess-Event-Id` for
  idempotency.

**Key differences from V2:**
- V3 groups have **no per-group `enable` field** — the presence of a group in the
  list is what makes it active. (V2 groups carry `enable` 0/1.)
- `maxGroupCount` is reported by the device rather than fixed at 8.
- Adds the batch endpoint and webhook completion notifications.

---

#### Scheduler V2

**Get Time Segment Information:**
- **Path:** `/op/v2/device/scheduler/get`
- **Method:** POST
- **Body:** `deviceSN`
- **Response:** `enable` (master switch), `groups[]`, `properties`

**Set Time Segment Information:**
- **Path:** `/op/v2/device/scheduler/enable`
- **Method:** POST
- **Body:** `deviceSN`, `isDefault` (optional, default `false`), `groups[]`

---

#### Scheduler group fields (V2 and V3)

| Field | Type | Required | Note |
|---|---|---|---|
| `enable` | integer | V2 only | Whether this group is active (0:disable 1:enable). Not present in V3. |
| `startHour` / `startMinute` | integer | Yes | Start time |
| `endHour` / `endMinute` | integer | Yes | End time |
| `workMode` | string | Yes | `SelfUse`, `Feedin`, `Backup`, `ForceCharge`, `ForceDischarge` |
| `extraParam` | object | No | See below |

**`extraParam` fields** (all optional on write):

| Field | Meaning |
|---|---|
| `minSocOnGrid` | Battery discharge cut-off SoC in grid-connected state |
| `fdSoc` | **FC/FD SoC.** The SoC level for Force Charge *or* Force Discharge mode. Once the battery reaches this SoC the system automatically stops charging or discharging. |
| `fdPwr` | **FC/FD Power.** Maximum charging *or* discharging power in Force Charge / Force Discharge mode: the max AC input power drawn from grid when force charging, and the max AC output power delivered when force discharging. |
| `maxSoc` | Max SoC value |
| `importLimit` | Import limit |
| `exportLimit` | Export limit |
| `pvLimit` | PV limit |
| `reactivePower` | Reactive power limit |

> **Note:** `fdSoc` and `fdPwr` are **not discharge-only**. The official
> descriptions cover both Force Charge and Force Discharge, so naming them as
> "charge" or "discharge" parameters is misleading in one direction or the other.

#### `isDefault` — merge vs. reset semantics

`isDefault` controls what happens to `extraParam` fields you do **not** send:

- `false` (default) — parameters not provided in `extraParam` **remain unchanged**.
- `true` — parameters not provided in `extraParam` are **restored to system defaults**.

This is documented identically for V2 and V3. Sending a partial `extraParam` with
`isDefault: false` is therefore a safe partial update; it does not clobber the
fields you omitted.

#### Properties block

Both V2 and V3 `get` responses include a `properties` object giving the valid
**range for each field** in a group time period, keyed by field name:

```
properties.{field_name} = {
  unit:      string,
  precision: 1 | 0.1 | 0.01,
  range:     { min: number, max: number }
}
```

Use this to derive entity ranges (e.g. the real `fdPwr` maximum, which is
inverter-dependent) rather than hardcoding limits.

> **Observed vs. documented (verified against an H3 device, 2026-09-07):**
>
> - **Keys are returned fully lowercased** — `fdpwr`, `fdsoc`, `minsocongrid`,
>   `maxsoc`, `workmode`, `starthour` … — *not* the camelCase used everywhere
>   else in the API. Look up `properties["fdpwr"]`, not `properties["fdPwr"]`.
> - **`workmode` carries an undocumented `enumList`** giving the modes the
>   device actually accepts. The published docs list five modes; a real device
>   returned seven, including `ForceCharge(BAT)` and `ForceDischarge(BAT)`:
>   `["ForceDischarge", "Feedin", "ForceCharge(BAT)", "ForceDischarge(BAT)",
>   "Backup", "SelfUse", "ForceCharge"]`. Prefer `enumList` over any static list.
> - **`range` is not always present.** `reactivepowerenable` returned `precision`
>   and `unit` but no `range`. Handle its absence.
> - **Ranges are device-specific.** The same H3 reported `fdpwr` max **10500 W**
>   (not the 6000 often assumed), `fdsoc`/`maxsoc`/`minsocongrid` 10–100 %,
>   `pvlimit` 0–20000 W, `reactivepower` ±6000 Var, `importlimit`/`exportlimit`
>   0–100000 W. Always read them rather than hardcoding.
> - **`maxGroupCount` is V3-only** and was **96** on this device — V2's response
>   omits the field entirely.

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
  - `workMode`, `minSocOnGrid` (10-100), `fdSoc`, `fdPwr`
  - `maxSoc` (optional, added in V1.0.10)
- **Note:** V1 carries the SOC/power fields flat on the group, not under `extraParam`.

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
- ⚠️ **Source inconsistency:** the endpoint listing gives `/op/v0/device/scheduler/set/flag`,
  but the Python sample in the same doc (`device_scheduler_set_flag()`) posts to
  `/op/v0/device/scheduler/set`. Verify against the device if you use V0.

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

#### Get Data Logger Details
- **Path:** `/op/v0/module/detail`
- **Method:** GET
- **Response:** Includes `webVersion`, `softVersion`
- **Added:** V1.1.11

#### Get Data Logger LAN Info
- **Path:** `/op/v0/module/getLanInfo`
- **Method:** POST
- **Response:** IP, `gateway`, `mask`

#### Get Data Logger WiFi Info
- **Path:** `/op/v0/module/getWifiInfo`
- **Method:** POST

#### Modbus Commands
- **Path:** `/op/v0/module/modbus/commands`
- **Method:** POST
- **Body:** `sn`, `data` (base64-encoded), `timeout` (optional, default 10s)
- **Response:** `data` (base64-encoded response)

---

### EMS (Energy Management System)

#### Get EMS Real-Time Data
- **Path:** `/op/v0/ems/real/query`
- **Method:** POST
- **Added:** V1.1.10

#### Get EMS History Data
- **Path:** `/op/v0/ems/history/query`
- **Method:** POST
- **Added:** V1.1.10

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

#### Heat Pump Controls (V1.1.18)
Four get/set control groups, each `POST`:

| Control group | Get | Set |
|---|---|---|
| Generic | `/op/v0/heat/genericControls/get` | `/op/v0/heat/genericControls/set` |
| Heating | `/op/v0/heat/heatingControls/get` | `/op/v0/heat/heatingControls/set` |
| Heating circuits | `/op/v0/heat/heatingCircuitsControls/get` | `/op/v0/heat/heatingCircuitsControls/set` |
| DHW (hot water) | `/op/v0/heat/dhwControls/get` | `/op/v0/heat/dhwControls/set` |

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

#### VPP OAuth 2.0 Client Onboarding
- **Onboard:** `POST /op/v0/vpp/oauth2/client/onboard`
- **Offboard:** `POST /op/v0/vpp/oauth2/client/offboard`
- **Device offboard:** `POST /op/v0/vpp/oauth2/code/offboard/device`

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
| 2026/02/06 | V1.1.10 | EMS real-time and history query interfaces; **Scheduler V3** |
| 2026/03/09 | V1.1.11 | Boarding status; Data Logger Details endpoint |
| 2026/03/20 | V1.1.12 | Device param setting APIs echo input on success; GMAX peak time params constrained |
| 2026/04/02 | V1.1.13 | Device fault history endpoint; `PVEnergyTotal` added to real-time data |
| 2026/04/03 | V1.1.14 | Kafka integration documentation |
| 2026/04/29 | V1.1.15 | Device boarding status retrieve endpoint; new data variables |
| 2026/05/07 | V1.1.16 | OAuth guide updated |
| 2026/05/22 | V1.1.17 | Battery information added to plant details endpoint (US only) |
| 2026/05/29 | V1.1.18 | Heat pump endpoints; variable table updated |
