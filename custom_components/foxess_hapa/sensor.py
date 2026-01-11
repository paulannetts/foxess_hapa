"""Sensor platform for foxess_hapa."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)

from .entity import FoxessHapaEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import FoxessHapaDataUpdateCoordinator
    from .data import FoxessHapaConfigEntry


@dataclass(frozen=True, kw_only=True)
class FoxessHapaSensorEntityDescription(SensorEntityDescription):
    """Describes a FoxESS HAPA sensor entity."""

    value_fn: str  # Attribute name in real_time data


SENSOR_DESCRIPTIONS: tuple[FoxessHapaSensorEntityDescription, ...] = (
    # Main power metrics
    FoxessHapaSensorEntityDescription(
        key="pv_power",
        translation_key="pv_power",
        name="PV Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:solar-power",
        value_fn="pv_power",
    ),
    FoxessHapaSensorEntityDescription(
        key="battery_soc",
        translation_key="battery_soc",
        name="Battery SoC",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery",
        value_fn="battery_soc",
    ),
    FoxessHapaSensorEntityDescription(
        key="battery_power",
        translation_key="battery_power",
        name="Battery Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery-charging",
        value_fn="battery_power",
    ),
    FoxessHapaSensorEntityDescription(
        key="grid_power",
        translation_key="grid_power",
        name="Grid Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:transmission-tower",
        value_fn="grid_power",
    ),
    FoxessHapaSensorEntityDescription(
        key="load_power",
        translation_key="load_power",
        name="Load Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:home-lightning-bolt",
        value_fn="load_power",
    ),
    FoxessHapaSensorEntityDescription(
        key="feed_in_power",
        translation_key="feed_in_power",
        name="Feed-in Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:transmission-tower-export",
        value_fn="feed_in_power",
    ),
    FoxessHapaSensorEntityDescription(
        key="grid_consumption_power",
        translation_key="grid_consumption_power",
        name="Grid Consumption Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:transmission-tower-import",
        value_fn="grid_consumption_power",
    ),
    FoxessHapaSensorEntityDescription(
        key="generation_power",
        translation_key="generation_power",
        name="Generation Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:solar-power-variant",
        value_fn="generation_power",
    ),
    # PV String 1
    FoxessHapaSensorEntityDescription(
        key="pv1_volt",
        translation_key="pv1_volt",
        name="PV1 Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:solar-panel",
        value_fn="pv1_volt",
    ),
    FoxessHapaSensorEntityDescription(
        key="pv1_current",
        translation_key="pv1_current",
        name="PV1 Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:solar-panel",
        value_fn="pv1_current",
    ),
    FoxessHapaSensorEntityDescription(
        key="pv1_power",
        translation_key="pv1_power",
        name="PV1 Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:solar-panel",
        value_fn="pv1_power",
    ),
    # PV String 2
    FoxessHapaSensorEntityDescription(
        key="pv2_volt",
        translation_key="pv2_volt",
        name="PV2 Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:solar-panel",
        value_fn="pv2_volt",
    ),
    FoxessHapaSensorEntityDescription(
        key="pv2_current",
        translation_key="pv2_current",
        name="PV2 Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:solar-panel",
        value_fn="pv2_current",
    ),
    FoxessHapaSensorEntityDescription(
        key="pv2_power",
        translation_key="pv2_power",
        name="PV2 Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:solar-panel",
        value_fn="pv2_power",
    ),
    # PV String 3
    FoxessHapaSensorEntityDescription(
        key="pv3_volt",
        translation_key="pv3_volt",
        name="PV3 Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:solar-panel",
        value_fn="pv3_volt",
    ),
    FoxessHapaSensorEntityDescription(
        key="pv3_current",
        translation_key="pv3_current",
        name="PV3 Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:solar-panel",
        value_fn="pv3_current",
    ),
    FoxessHapaSensorEntityDescription(
        key="pv3_power",
        translation_key="pv3_power",
        name="PV3 Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:solar-panel",
        value_fn="pv3_power",
    ),
    # PV String 4
    FoxessHapaSensorEntityDescription(
        key="pv4_volt",
        translation_key="pv4_volt",
        name="PV4 Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:solar-panel",
        value_fn="pv4_volt",
    ),
    FoxessHapaSensorEntityDescription(
        key="pv4_current",
        translation_key="pv4_current",
        name="PV4 Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:solar-panel",
        value_fn="pv4_current",
    ),
    FoxessHapaSensorEntityDescription(
        key="pv4_power",
        translation_key="pv4_power",
        name="PV4 Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:solar-panel",
        value_fn="pv4_power",
    ),
    # EPS (Emergency Power Supply)
    FoxessHapaSensorEntityDescription(
        key="eps_power",
        translation_key="eps_power",
        name="EPS Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:power-plug-battery",
        value_fn="eps_power",
    ),
    FoxessHapaSensorEntityDescription(
        key="eps_current_r",
        translation_key="eps_current_r",
        name="EPS R Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:power-plug-battery",
        value_fn="eps_current_r",
    ),
    FoxessHapaSensorEntityDescription(
        key="eps_volt_r",
        translation_key="eps_volt_r",
        name="EPS R Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:power-plug-battery",
        value_fn="eps_volt_r",
    ),
    FoxessHapaSensorEntityDescription(
        key="eps_power_r",
        translation_key="eps_power_r",
        name="EPS R Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:power-plug-battery",
        value_fn="eps_power_r",
    ),
    # Grid R-Phase
    FoxessHapaSensorEntityDescription(
        key="r_current",
        translation_key="r_current",
        name="Grid R Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:transmission-tower",
        value_fn="r_current",
    ),
    FoxessHapaSensorEntityDescription(
        key="r_volt",
        translation_key="r_volt",
        name="Grid R Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:transmission-tower",
        value_fn="r_volt",
    ),
    FoxessHapaSensorEntityDescription(
        key="r_freq",
        translation_key="r_freq",
        name="Grid Frequency",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:sine-wave",
        value_fn="r_freq",
    ),
    FoxessHapaSensorEntityDescription(
        key="r_power",
        translation_key="r_power",
        name="Grid R Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:transmission-tower",
        value_fn="r_power",
    ),
    # Temperature sensors
    FoxessHapaSensorEntityDescription(
        key="ambient_temp",
        translation_key="ambient_temp",
        name="Ambient Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:thermometer",
        value_fn="ambient_temp",
    ),
    FoxessHapaSensorEntityDescription(
        key="inverter_temp",
        translation_key="inverter_temp",
        name="Inverter Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:thermometer",
        value_fn="inverter_temp",
    ),
    FoxessHapaSensorEntityDescription(
        key="battery_temp",
        translation_key="battery_temp",
        name="Battery Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:thermometer",
        value_fn="battery_temp",
    ),
    # Inverter battery interface
    FoxessHapaSensorEntityDescription(
        key="inv_bat_volt",
        translation_key="inv_bat_volt",
        name="Inverter Battery Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery",
        value_fn="inv_bat_volt",
    ),
    FoxessHapaSensorEntityDescription(
        key="inv_bat_current",
        translation_key="inv_bat_current",
        name="Inverter Battery Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery",
        value_fn="inv_bat_current",
    ),
    FoxessHapaSensorEntityDescription(
        key="inv_bat_power",
        translation_key="inv_bat_power",
        name="Inverter Battery Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery",
        value_fn="inv_bat_power",
    ),
    # Battery charge/discharge power
    FoxessHapaSensorEntityDescription(
        key="bat_charge_power",
        translation_key="bat_charge_power",
        name="Battery Charge Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery-charging",
        value_fn="bat_charge_power",
    ),
    FoxessHapaSensorEntityDescription(
        key="bat_discharge_power",
        translation_key="bat_discharge_power",
        name="Battery Discharge Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery-arrow-down",
        value_fn="bat_discharge_power",
    ),
    # Battery direct measurements
    FoxessHapaSensorEntityDescription(
        key="bat_volt",
        translation_key="bat_volt",
        name="Battery Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery",
        value_fn="bat_volt",
    ),
    FoxessHapaSensorEntityDescription(
        key="bat_current",
        translation_key="bat_current",
        name="Battery Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery",
        value_fn="bat_current",
    ),
    # Meter power
    FoxessHapaSensorEntityDescription(
        key="meter_power_2",
        translation_key="meter_power_2",
        name="Meter 2 Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:meter-electric",
        value_fn="meter_power_2",
    ),
    # Energy totals (kWh)
    FoxessHapaSensorEntityDescription(
        key="generation_total",
        translation_key="generation_total",
        name="Total Generation",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:solar-power-variant",
        value_fn="generation_total",
    ),
    FoxessHapaSensorEntityDescription(
        key="residual_energy",
        translation_key="residual_energy",
        name="Battery Residual Energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY_STORAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery",
        value_fn="residual_energy",
    ),
    FoxessHapaSensorEntityDescription(
        key="energy_throughput",
        translation_key="energy_throughput",
        name="Battery Throughput",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:battery-sync",
        value_fn="energy_throughput",
    ),
    FoxessHapaSensorEntityDescription(
        key="grid_consumption_total",
        translation_key="grid_consumption_total",
        name="Total Grid Consumption",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:transmission-tower-import",
        value_fn="grid_consumption_total",
    ),
    FoxessHapaSensorEntityDescription(
        key="loads_total",
        translation_key="loads_total",
        name="Total Load Consumption",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:home-lightning-bolt",
        value_fn="loads_total",
    ),
    FoxessHapaSensorEntityDescription(
        key="feed_in_total",
        translation_key="feed_in_total",
        name="Total Feed-in",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:transmission-tower-export",
        value_fn="feed_in_total",
    ),
    FoxessHapaSensorEntityDescription(
        key="charge_energy_total",
        translation_key="charge_energy_total",
        name="Total Charge Energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:battery-charging",
        value_fn="charge_energy_total",
    ),
    FoxessHapaSensorEntityDescription(
        key="discharge_energy_total",
        translation_key="discharge_energy_total",
        name="Total Discharge Energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:battery-arrow-down",
        value_fn="discharge_energy_total",
    ),
    FoxessHapaSensorEntityDescription(
        key="pv_energy_total",
        translation_key="pv_energy_total",
        name="Total PV Energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:solar-power",
        value_fn="pv_energy_total",
    ),
    # Status sensors
    FoxessHapaSensorEntityDescription(
        key="running_state",
        translation_key="running_state",
        name="Running State",
        device_class=None,
        state_class=None,
        icon="mdi:state-machine",
        value_fn="running_state",
    ),
    FoxessHapaSensorEntityDescription(
        key="battery_status",
        translation_key="battery_status",
        name="Battery Status Code",
        device_class=None,
        state_class=None,
        icon="mdi:battery-check",
        value_fn="battery_status",
    ),
    FoxessHapaSensorEntityDescription(
        key="battery_status_name",
        translation_key="battery_status_name",
        name="Battery Status",
        device_class=None,
        state_class=None,
        icon="mdi:battery-check",
        value_fn="battery_status_name",
    ),
    FoxessHapaSensorEntityDescription(
        key="current_fault",
        translation_key="current_fault",
        name="Current Fault",
        device_class=None,
        state_class=None,
        icon="mdi:alert-circle",
        value_fn="current_fault",
    ),
    FoxessHapaSensorEntityDescription(
        key="current_fault_count",
        translation_key="current_fault_count",
        name="Fault Count",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:alert-circle",
        value_fn="current_fault_count",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: FoxessHapaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator = entry.runtime_data.coordinator

    async_add_entities(
        FoxessHapaSensor(
            coordinator=coordinator,
            entity_description=description,
        )
        for description in SENSOR_DESCRIPTIONS
    )


class FoxessHapaSensor(FoxessHapaEntity, SensorEntity):
    """FoxESS HAPA Sensor class."""

    entity_description: FoxessHapaSensorEntityDescription

    def __init__(
        self,
        coordinator: FoxessHapaDataUpdateCoordinator,
        entity_description: FoxessHapaSensorEntityDescription,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{entity_description.key}"
        )

    @property
    def native_value(self) -> float | None:
        """Return the native value of the sensor."""
        if not self.coordinator.data:
            return None

        real_time = self.coordinator.data.get("real_time")
        if not real_time:
            return None

        return getattr(real_time, self.entity_description.value_fn, None)
