import time
import random
import json
import os
from datetime import datetime, timezone
from typing import Dict, List


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class SensorSimulator:
    def __init__(self, machine_id: str, fault_mode: str = "normal"):
        self.machine_id = machine_id
        self.fault_mode = fault_mode
        self.degradation_step = 0
        
        # Load thresholds if config exists
        self.thresholds = {"vibration": 1.5, "temperature": 60.0, "current": 3.5}
        config_path = os.path.join(os.path.dirname(__file__), "config", "machines.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    machine_config = config.get("machines", {}).get(machine_id, {})
                    thresholds = machine_config.get("thresholds", {})
                    self.thresholds = {
                        "vibration": thresholds.get("vibration", {}).get("warning", 1.5),
                        "temperature": thresholds.get("temperature", {}).get("warning", 60.0),
                        "current": thresholds.get("current", {}).get("warning", 3.5)
                    }
            except Exception:
                pass

    def get_sensor_reading(self) -> Dict:
        self.degradation_step += 1
        
        # Base normal values
        vib_x = 0.3 + random.uniform(-0.1, 0.1)
        vib_y = 0.4 + random.uniform(-0.1, 0.1)
        vib_z = 0.2 + random.uniform(-0.05, 0.05)
        temp = 45.0 + random.uniform(-2.0, 2.0)
        curr = 2.2 + random.uniform(-0.2, 0.2)
        
        if self.fault_mode == "bearing_wear":
            # Progressive degradation
            factor = min(self.degradation_step / 100.0, 2.0)
            vib_x += 1.5 * factor
            vib_y += 1.2 * factor
            vib_z += 0.8 * factor
            temp += 15.0 * factor
            curr += 1.2 * factor
        elif self.fault_mode == "misalignment":
            vib_x += 2.0  # High in x axis
            vib_y += 0.5
            temp += 2.0
            curr += 0.4
        elif self.fault_mode == "overheating":
            temp += 28.0 + random.uniform(0, 5.0)
            vib_x += 0.4
            curr += 0.8
        elif self.fault_mode == "electrical_fault":
            curr += 2.5
            temp += 10.0
            vib_x += 0.2
            
        rms = (vib_x**2 + vib_y**2 + vib_z**2)**0.5
        
        status = "Normal"
        if rms > self.thresholds["vibration"] * 2 or temp > self.thresholds["temperature"] * 1.25 or curr > self.thresholds["current"] * 1.25:
            status = "Critical"
        elif rms > self.thresholds["vibration"] or temp > self.thresholds["temperature"] or curr > self.thresholds["current"]:
            status = "Warning"
            
        return {
            "timestamp": utc_timestamp(),
            "machine_id": self.machine_id,
            "vibration": {
                "x": round(vib_x, 3),
                "y": round(vib_y, 3),
                "z": round(vib_z, 3),
                "rms": round(rms, 3)
            },
            "temperature": round(temp, 1),
            "current": round(curr, 2),
            "status": status
        }

class MultiMachineSimulator:
    def __init__(self):
        self.machines = {
            "M001": SensorSimulator("M001", "normal"),
            "M002": SensorSimulator("M002", "normal"),
            "M003": SensorSimulator("M003", "normal"),
            "M004": SensorSimulator("M004", "normal")
        }

    def get_machine_reading(self, machine_id: str) -> Dict:
        if machine_id in self.machines:
            return self.machines[machine_id].get_sensor_reading()
        raise ValueError(f"Machine {machine_id} not found")

    def get_all_readings(self) -> List[Dict]:
        return [sim.get_sensor_reading() for sim in self.machines.values()]
