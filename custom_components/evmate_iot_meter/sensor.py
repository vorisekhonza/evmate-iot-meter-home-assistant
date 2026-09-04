from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EVmateCoordinator

def _signed16(value: Any) -> int | None:
    try:
        value = int(value)
    except (TypeError, ValueError):
        return None
    return value - 65536 if value > 32767 else value

def _number(value: Any) -> float | int | None:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return int(value) if value.is_integer() else value

def _current(value: Any) -> float | None:
    raw = _signed16(value)
    return None if raw is None else round(abs(raw) / 100.0, 2)

def _pf(value: Any) -> float | None:
    raw = _number(value)
    return None if raw is None else round(abs(float(raw)) / 100.0, 2)

def _energy_10wh(value: Any) -> float | None:
    raw = _number(value)
    return None if raw is None else float(raw) * 10.0

@dataclass(frozen=True, kw_only=True)
class EVmateSensorDescription(SensorEntityDescription):
    json_key: str | None = None
    value_fn: Callable[[dict[str, Any]], Any] | None = None
    optional: bool = False

def phase_desc(key, name, unit, device_class, value_fn=None):
    return tuple(
        EVmateSensorDescription(
            key=f"{key}_l{i}",
            translation_key=f"{key}_l{i}",
            json_key=f"{name}{i}",
            native_unit_of_measurement=unit,
            device_class=device_class,
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=(lambda phase: (lambda d: value_fn(d.get(f"{name}{phase}"))))(i)
                if value_fn else None,
        )
        for i in (1, 2, 3)
    )

SENSORS = (
    *phase_desc("voltage", "U", UnitOfElectricPotential.VOLT, SensorDeviceClass.VOLTAGE),
    *phase_desc("current", "I", UnitOfElectricCurrent.AMPERE, SensorDeviceClass.CURRENT, _current),
    *phase_desc("power", "P", UnitOfPower.WATT, SensorDeviceClass.POWER, _signed16),

    EVmateSensorDescription(
        key="power_total",
        translation_key="power_total",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: sum(
            x for x in (
                _signed16(d.get("P1")),
                _signed16(d.get("P2")),
                _signed16(d.get("P3")),
            ) if x is not None
        ),
    ),

    *tuple(
        EVmateSensorDescription(
            key=f"power_factor_l{i}",
            translation_key=f"power_factor_l{i}",
            json_key=f"F{i}",
            device_class=SensorDeviceClass.POWER_FACTOR,
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=(lambda phase: (lambda d: _pf(d.get(f"F{phase}"))))(i),
        )
        for i in (1, 2, 3)
    ),

    *tuple(
        EVmateSensorDescription(
            key=f"energy_positive_l{i}",
            translation_key=f"energy_positive_l{i}",
            json_key=f"E{i}tP",
            native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            value_fn=(lambda phase: (lambda d: _energy_10wh(d.get(f"E{phase}tP"))))(i),
        )
        for i in (1, 2, 3)
    ),

    *tuple(
        EVmateSensorDescription(
            key=f"energy_negative_l{i}",
            translation_key=f"energy_negative_l{i}",
            json_key=f"E{i}tN",
            native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            value_fn=(lambda phase: (lambda d: _energy_10wh(d.get(f"E{phase}tN"))))(i),
        )
        for i in (1, 2, 3)
    ),

    EVmateSensorDescription(
        key="energy_positive_total",
        translation_key="energy_positive_total",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: sum((_energy_10wh(d.get(k)) or 0) for k in ("E1tP","E2tP","E3tP")),
    ),
    EVmateSensorDescription(
        key="energy_negative_total",
        translation_key="energy_negative_total",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: sum((_energy_10wh(d.get(k)) or 0) for k in ("E1tN","E2tN","E3tN")),
    ),

    EVmateSensorDescription(
        key="evse_requested_current",
        translation_key="evse_requested_current",
        json_key="ACTUAL_CONFIG_CURRENT",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        optional=True,
    ),
    EVmateSensorDescription(
        key="evse_output_current",
        translation_key="evse_output_current",
        json_key="ACTUAL_OUTPUT_CURRENT",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        optional=True,
    ),
    EVmateSensorDescription(
        key="evse_state",
        translation_key="evse_state",
        json_key="EV_STATE",
        optional=True,
    ),
    EVmateSensorDescription(
        key="evse_internal_state",
        translation_key="evse_internal_state",
        json_key="EVSE_STATE",
        optional=True,
    ),
    EVmateSensorDescription(
        key="evse_status",
        translation_key="evse_status",
        json_key="EVSE_STATUS",
        optional=True,
    ),
    EVmateSensorDescription(
        key="evse_comm_error",
        translation_key="evse_comm_error",
        json_key="EV_COMM_ERR",
        optional=True,
    ),
    EVmateSensorDescription(
        key="charging_duration",
        translation_key="charging_duration",
        json_key="DURATION",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        optional=True,
    ),
    EVmateSensorDescription(
        key="charging_session_energy",
        translation_key="charging_session_energy",
        json_key="SESSION_ENERGY",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        optional=True,
    ),
    EVmateSensorDescription(
        key="charging_user",
        translation_key="charging_user",
        json_key="USER",
        optional=True,
    ),
    EVmateSensorDescription(
        key="car_soc",
        translation_key="car_soc",
        json_key="soc",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        optional=True,
    ),
    EVmateSensorDescription(
        key="charge_mode_raw",
        translation_key="charge_mode_raw",
        json_key="chargeMode",
    ),
)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EVmateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        EVmateSensor(coordinator, entry, description)
        for description in SENSORS
    )

class EVmateSensor(CoordinatorEntity[EVmateCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, description):
        super().__init__(coordinator)
        self.entity_description = description
        meter_id = str(coordinator.data.get("ID", entry.unique_id or entry.entry_id))
        self._attr_unique_id = f"{meter_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, meter_id)},
            name="EVmate IoT Meter",
            manufacturer="EVmate",
            model="IoT Meter",
        )

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        desc = self.entity_description
        if desc.optional and desc.json_key:
            return desc.json_key in self.coordinator.data
        return True

    @property
    def native_value(self):
        desc = self.entity_description
        if desc.value_fn is not None:
            return desc.value_fn(self.coordinator.data)
        if desc.json_key is None:
            return None
        value = self.coordinator.data.get(desc.json_key)
        if isinstance(value, (int, float)):
            return _number(value)
        return value
