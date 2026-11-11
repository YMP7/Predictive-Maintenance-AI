"""
What each machine type looks like to the 3D Asset View: its parts, and which sensor
channel belongs to which part. Domain knowledge lives here (Adapter Layer), so the
frontend only knows geometry by `kind` and never branches on a domain name.

`dir` is the direction a channel moves under load or degradation: 1 up, -1 down,
0 neutral (shown, never counted as load).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class Part:
    id: str
    name: str
    detail: str


@dataclass(frozen=True)
class Binding:
    part: str
    label: str
    dir: int = 1
    unit: Optional[str] = None  # unit of the raw value, when the adapter reports one


@dataclass(frozen=True)
class AssetProfile:
    kind: str  # geometry key on the client: turbofan, laptop, phone, server, motor_pump
    label: str
    parts: Tuple[Part, ...]
    channels: Dict[str, Binding] = field(default_factory=dict)
    spin: Optional[str] = None  # the measured channel that drives rotating parts, if any
    rul_unit: str = "steps"
    attribution: bool = False  # occlusion attribution exists for this domain's feature layout
    rul_note: Optional[str] = None


P = Part
B = Binding

# C-MAPSS FD001 sensors, names and units from Saxena et al. (2008), Table 2.
TURBOFAN = AssetProfile(
    kind="turbofan",
    label="Turbofan engine (NASA C-MAPSS FD001)",
    parts=(
        P("fan", "Fan", "Moves the bypass air that makes most of the thrust"),
        P("lpc", "Low-pressure compressor", "First stage of core compression"),
        P("hpc", "High-pressure compressor", "Raises core air to combustion pressure"),
        P("combustor", "Combustor", "Burns fuel in the compressed air"),
        P("hpt", "High-pressure turbine", "Drives the high-pressure compressor"),
        P("lpt", "Low-pressure turbine", "Drives the fan and low-pressure compressor"),
        P("nozzle", "Exhaust nozzle", "Accelerates core flow out of the engine"),
    ),
    channels={
        "s2": B("lpc", "LPC outlet temperature (T24)", 1, "°R"),
        "s3": B("hpc", "HPC outlet temperature (T30)", 1, "°R"),
        "s4": B("lpt", "LPT outlet temperature (T50)", 1, "°R"),
        "s7": B("hpc", "HPC outlet pressure (P30)", -1, "psia"),
        "s8": B("fan", "Fan speed (Nf)", 1, "rpm"),
        "s9": B("hpc", "Core speed (Nc)", 1, "rpm"),
        "s11": B("hpc", "HPC static pressure (Ps30)", 1, "psia"),
        "s12": B("combustor", "Fuel flow to Ps30 ratio (phi)", -1, "pps/psi"),
        "s13": B("fan", "Corrected fan speed (NRf)", 1, "rpm"),
        "s14": B("hpc", "Corrected core speed (NRc)", 1, "rpm"),
        "s15": B("fan", "Bypass ratio (BPR)", 1, None),
        "s17": B("hpc", "Bleed enthalpy (htBleed)", 1, None),
        "s20": B("hpt", "HPT coolant bleed (W31)", -1, "lbm/s"),
        "s21": B("lpt", "LPT coolant bleed (W32)", -1, "lbm/s"),
    },
    spin="s8",
    rul_unit="cycles",
    attribution=True,
)

LAPTOP = AssetProfile(
    kind="laptop",
    label="Laptop (this computer's OS telemetry)",
    parts=(
        P("cpu", "Processor", "Runs every process; its load drives heat"),
        P("cooling", "Heat pipe and fan", "Carries processor heat to the vent"),
        P("memory", "Memory", "RAM and the swap file behind it"),
        P("storage", "SSD", "Holds the disk; reads and writes go here"),
        P("battery", "Battery", "Powers the machine off the charger"),
        P("wifi", "Wi-Fi card", "All network traffic"),
        P("display", "Display", "Lid and panel"),
    ),
    channels={
        "cpu_usage": B("cpu", "Processor load"),
        "cpu_core_p90": B("cpu", "Busiest cores (p90)"),
        "cpu_frequency": B("cpu", "Clock speed vs maximum"),
        "context_switches": B("cpu", "Context switches"),
        "interrupt_rate": B("cpu", "Hardware interrupts"),
        "process_activity": B("cpu", "Running processes"),
        "thermal_headroom": B("cooling", "Estimated temperature (heuristic)"),
        "memory_usage": B("memory", "Memory in use"),
        "swap_usage": B("memory", "Swap in use"),
        "disk_usage": B("storage", "Disk space used"),
        "disk_read_throughput": B("storage", "Disk reads"),
        "disk_write_throughput": B("storage", "Disk writes"),
        "disk_iops_rate": B("storage", "Disk operations"),
        "battery_percent": B("battery", "Battery charge", -1),
        "is_charging": B("battery", "On charger (1 = plugged in)", 0),
        "network_throughput": B("wifi", "Network traffic"),
    },
    attribution=True,
)

PHONE = AssetProfile(
    kind="phone",
    label="Android phone (ADB or browser telemetry)",
    parts=(
        P("soc", "System on chip", "Processor and memory in one package"),
        P("battery", "Battery", "Charge, temperature, current and voltage"),
        P("imu", "Motion sensors", "Accelerometer and gyroscope"),
        P("sensors", "Light and proximity sensors", "Behind the top of the screen"),
        P("compass", "Magnetometer", "Measures the magnetic field"),
        P("display", "Display", "Glass and panel"),
    ),
    channels={
        "cpu_usage": B("soc", "Processor load"),
        "memory_used_percent": B("soc", "Memory in use"),
        "battery_level": B("battery", "Battery charge", -1),
        "battery_temp": B("battery", "Battery temperature"),
        "battery_current": B("battery", "Battery current"),
        "battery_voltage": B("battery", "Battery voltage", -1),
        "vibration_rms": B("imu", "Vibration (RMS)"),
        "accel_x": B("imu", "Acceleration X", 0),
        "accel_y": B("imu", "Acceleration Y", 0),
        "accel_z": B("imu", "Acceleration Z", 0),
        "gyro_x": B("imu", "Rotation X", 0),
        "gyro_y": B("imu", "Rotation Y", 0),
        "gyro_z": B("imu", "Rotation Z", 0),
        "ambient_light": B("sensors", "Ambient light", 0),
        "proximity": B("sensors", "Proximity", 0),
        "magnetic_field": B("compass", "Magnetic field strength", 0),
    },
    attribution=True,
)

SERVER = AssetProfile(
    kind="server",
    label="Rack server (host telemetry)",
    parts=(
        P("cpu", "Processors", "Two sockets under their heat sinks"),
        P("memory", "Memory modules", "DIMMs either side of the sockets"),
        P("storage", "Drive bays", "Front-loaded disks"),
        P("nic", "Network card", "All network traffic"),
        P("gpu", "GPU", "Accelerator card, when fitted"),
        P("fans", "Fan wall", "Pulls air front to back"),
        P("psu", "Power supplies", "Two redundant units"),
    ),
    channels={
        "cpu_usage": B("cpu", "Processor load"),
        "memory_usage": B("memory", "Memory in use"),
        "disk_usage": B("storage", "Disk space used"),
        "network_io_rate": B("nic", "Network traffic"),
        "gpu_utilization": B("gpu", "GPU load"),
    },
    attribution=True,
)

# Channel names match the ModbusAdapter register map (server/adapters/modbus_adapter.py).
MOTOR_PUMP = AssetProfile(
    kind="motor_pump",
    label="Motor-driven pump (Modbus TCP)",
    parts=(
        P("fan", "Cooling fan", "Pulls air over the motor body"),
        P("bearing_nde", "Rear bearing", "Non-drive end, supports the shaft"),
        P("stator", "Motor body", "Stator windings turn current into torque"),
        P("terminal", "Terminal box", "Supply cables connect here"),
        P("bearing_de", "Front bearing", "Drive end, carries the highest load"),
        P("coupling", "Shaft coupling", "Joins the motor shaft to the pump"),
        P("pump", "Pump and impeller", "The driven load"),
    ),
    channels={
        "temperature_c": B("stator", "Winding temperature", 1, "°C"),
        "vibration_mms": B("bearing_de", "Vibration velocity", 1, "mm/s"),
        "current_a": B("terminal", "Phase current", 1, "A"),
        "power_factor": B("terminal", "Power factor", -1, None),
        "speed_rpm": B("coupling", "Shaft speed", 0, "rpm"),
        "pressure_bar": B("pump", "Discharge pressure", 0, "bar"),
    },
    spin="speed_rpm",
    rul_unit="cycles",
    attribution=True,
    rul_note="The pump RUL model (trained on SIMULATED run-to-failure data) is not installed. "
             "Train it with: python -m server.atlas.train_pump_rul",
)

ASSET_PROFILES: Dict[str, AssetProfile] = {
    "cmapss": TURBOFAN,
    "laptop": LAPTOP,
    "mobile": PHONE,
    "server": SERVER,
    "modbus": MOTOR_PUMP,
}


def get_asset_profile(domain: str) -> Optional[AssetProfile]:
    return ASSET_PROFILES.get(domain)


def profile_dict(domain: str, p: AssetProfile) -> dict:
    return {
        "domain": domain,
        "kind": p.kind,
        "label": p.label,
        "parts": [{"id": x.id, "name": x.name, "detail": x.detail} for x in p.parts],
        "channels": {k: {"part": b.part, "label": b.label, "dir": b.dir, "unit": b.unit} for k, b in p.channels.items()},
        "spin": p.spin,
        "rul_unit": p.rul_unit,
        "attribution": p.attribution,
        "rul_note": p.rul_note,
    }


# Channels whose rise means wear; speed, pressure and power factor are shown but not weighted.
_MODBUS_HEALTH_WEIGHTS = {"temperature_c": 1.0, "vibration_mms": 1.0, "current_a": 0.5}


def sensor_profile_template(domain: str, machine_id: str, simulated: bool = False) -> Optional[dict]:
    """A ready SensorProfile (as a dict) for machine types with a known register map, or None.

    Used by the onboarding wizard and scripts/modbus_bridge.py. Only Modbus has one today: its
    channels, units and valid ranges come from ModbusAdapter's default register map.
    """
    if domain != "modbus":
        return None
    from server.adapters.modbus_adapter import DEFAULT_REGISTER_MAP

    return {
        "machine_id": machine_id,
        "domain": "modbus",
        "display_name": f"Motor-driven pump {machine_id}",
        "simulated": simulated,
        "channels": [
            {"channel": c.name, "feature": c.name, "unit": c.unit, "valid_min": c.min_val, "valid_max": c.max_val,
             "sampling_hz": 1.0, "health_weight": _MODBUS_HEALTH_WEIGHTS.get(c.name, 0.0),
             "part": MOTOR_PUMP.channels[c.name].part if c.name in MOTOR_PUMP.channels else None}
            for c in DEFAULT_REGISTER_MAP
        ],
    }
