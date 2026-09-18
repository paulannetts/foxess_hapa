# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- `foxess_hapa.set_current_period` service: applies any of `work_mode`,
  `target_soc`, `min_soc`, `max_soc`, `fd_soc`, `fd_pwr` to the schedule
  period covering the current time in a single scheduler write, so an
  automation can switch work mode and move the SoC target together.
- `target_soc` argument on `set_schedule` periods, `set_slot` and
  `set_current_period`: sets `min_soc` and `fd_soc` to the same value.
- Services target the inverter (`target: device_id:`, one of its entities,
  or an area containing exactly one) like other Home Assistant services.

### Deprecated

- The `config_entry_id` service argument. It still works but logs a warning;
  pick the device under "Targets" instead.

- `number.<device>_target_soc` ("Target SoC"): sets `minSocOnGrid` and `fdSoc`
  together, in one scheduler write, on the schedule period covering the current
  time. One value that the battery charges up to in ForceCharge and does not
  discharge below in SelfUse/ForceDischarge. Its `min_soc` and `fd_soc`
  attributes show the raw device values so drift set elsewhere is visible.

### Changed

- **Breaking:** the Schedule sensor's per-period attributes `charge_to_soc` and
  `charge_power` are renamed `fd_soc` and `fd_pwr`, matching the
  `set_schedule`/`set_slot` service arguments.
- Number entity writes now raise an error, visible in Home Assistant, when no
  schedule period covers the current time or the API rejects the update,
  instead of logging and silently reverting the slider.

### Removed

- **Breaking:** `number.<device>_min_soc_on_grid` and `number.<device>_fd_soc`
  are replaced by `target_soc`. Their entity-registry entries are removed
  automatically on the next load. Update automations to `target_soc`, or use
  the `foxess_hapa.set_slot` service if the two fields genuinely need
  different values.

### Fixed

- The mock API client (`FOXESS_MOCK_API=1`) rejected every entity write with a
  `TypeError`, so work mode and number changes could not be exercised locally.

## [0.1.0]

Initial release. Notable changes along the way:

- Scheduler slot selection fix, `fd_soc`/`fd_pwr` number entities, and no more
  slot renumbering on partial writes (#76).
- Work Mode select shows `ForceCharge(BAT)`/`ForceDischarge(BAT)` correctly
  and lists the modes the device reports (#59).
- `charge_power`/`charge_to_soc` parameters for ForceCharge periods (#32).
- Schedule sensor and `set_schedule`/`set_slot` services (#29).
- Migration from the deprecated FoxESS v0 API to v1 (#4).
