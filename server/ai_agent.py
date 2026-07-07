import os
import json
import math
import threading
from copy import deepcopy
import numpy as np
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class FaultDetector:
    def __init__(self):
        self.thresholds = {}
        config_path = os.path.join(os.path.dirname(__file__), "config", "machines.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    self.config = json.load(f)
                    for mid, mcfg in self.config.get("machines", {}).items():
                        self.thresholds[mid] = mcfg.get("thresholds", {})
            except Exception:
                pass

    def detect_fault(self, reading: Dict) -> Tuple[str, List[str]]:
        machine_id = reading.get("machine_id", "M001")
        m_thresh = self.thresholds.get(machine_id, {
            "vibration": {"warning": 1.5, "critical": 3.0},
            "temperature": {"warning": 60.0, "critical": 75.0},
            "current": {"warning": 3.5, "critical": 4.5}
        })
        
        vibration = reading.get("vibration")
        if not isinstance(vibration, dict):
            raise ValueError("reading.vibration must be an object")

        required_values = {
            "reading.vibration.rms": vibration.get("rms"),
            "reading.temperature": reading.get("temperature"),
            "reading.current": reading.get("current"),
        }
        for field, value in required_values.items():
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
                raise ValueError(f"{field} must be a finite number")

        v_rms = float(required_values["reading.vibration.rms"])
        temp = float(required_values["reading.temperature"])
        curr = float(required_values["reading.current"])
        
        issues = []
        
        # Check Vibration
        if v_rms > m_thresh["vibration"]["critical"]:
            issues.append("Critical Vibration Level")
        elif v_rms > m_thresh["vibration"]["warning"]:
            issues.append("Elevated Vibration (Warning)")
            
        # Check Temperature
        if temp > m_thresh["temperature"]["critical"]:
            issues.append("Critical Temperature Level")
        elif temp > m_thresh["temperature"]["warning"]:
            issues.append("Elevated Temperature (Warning)")
            
        # Check Current
        if curr > m_thresh["current"]["critical"]:
            issues.append("Critical Current Draw")
        elif curr > m_thresh["current"]["warning"]:
            issues.append("Elevated Current (Warning)")

        # Pattern classification
        fault_type = "Normal"
        if not issues:
            return "Normal", []

        # Misalignment: High vibration, normal temperature
        if v_rms > m_thresh["vibration"]["warning"] and temp < m_thresh["temperature"]["warning"]:
            fault_type = "Misalignment"
        # Overheating: High temp, high current, moderate vibration
        elif temp > m_thresh["temperature"]["warning"] and curr > m_thresh["current"]["warning"] and v_rms < m_thresh["vibration"]["critical"]:
            fault_type = "Overheating"
        # Bearing Wear: High vibration and high temperature
        elif v_rms > m_thresh["vibration"]["warning"] and temp > m_thresh["temperature"]["warning"]:
            fault_type = "Bearing Wear"
        # Electrical Fault: Excess current
        elif curr > m_thresh["current"]["warning"]:
            fault_type = "Electrical Fault"
            
        return fault_type, issues

class RULEstimator:
    def __init__(self):
        # Maps machine_id to list of degradation scores
        self.history: Dict[str, List[float]] = {}
        self.max_history = 1000
        
    def update_degradation(self, machine_id: str, reading: Dict) -> None:
        v_rms = reading.get("vibration", {}).get("rms", 0.0)
        temp = reading.get("temperature", 0.0)
        curr = reading.get("current", 0.0)
        
        # Calculate degradation score [0, 1]
        score = 0.5 * (v_rms / 5.0) + 0.3 * ((temp - 45) / 30) + 0.2 * ((curr - 2.5) / 2.0)
        score = max(0.0, min(1.0, score))
        
        if machine_id not in self.history:
            self.history[machine_id] = []
        self.history[machine_id].append(score)
        if len(self.history[machine_id]) > self.max_history:
            self.history[machine_id].pop(0)
        
    def estimate_rul(self, machine_id: str) -> Dict:
        history = self.history.get(machine_id, [])
        if len(history) < 10:
            return {
                "rul_days": None,
                "confidence": 0.0,
                "status": "Insufficient Data"
            }
            
        # Linear trend extrapolation
        x = np.arange(len(history))
        y = np.array(history)
        
        # Fit linear curve: y = mx + c
        m, c = np.polyfit(x, y, 1)
        
        current_deg = history[-1]
        critical_threshold = 0.8
        
        if current_deg >= critical_threshold:
            return {
                "rul_days": 0,
                "confidence": 0.95,
                "status": "Degrading"
            }
            
        if m <= 0:
            return {
                "rul_days": 100,  # stable
                "confidence": 0.80,
                "status": "Stable"
            }
            
        # Estimate remaining steps to reach critical threshold
        steps_to_fail = (critical_threshold - current_deg) / m
        
        # Assume 1 step = 1 simulation interval. In real days:
        # Scale steps for simulation purposes: e.g., 100 steps = 14 days
        rul_days = max(1, int(steps_to_fail * 0.14))
        
        # R-squared value for confidence
        y_pred = m * x + c
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_sq = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
        confidence = max(0.5, min(0.95, float(r_sq)))
        
        status = "Degrading" if current_deg > 0.5 else "Collecting Data"
        if rul_days > 30:
            status = "Stable"
            
        return {
            "rul_days": rul_days,
            "confidence": round(confidence, 2),
            "status": status
        }

class AlertGenerator:
    def __init__(self):
        pass

    def generate_alerts(self, machine_id: str, fault_detector: FaultDetector, rul_estimator: RULEstimator, reading: Dict) -> List[Dict]:
        alerts = []
        fault_type, issues = fault_detector.detect_fault(reading)
        rul_info = rul_estimator.estimate_rul(machine_id)
        
        # 1. Fault Detection Alerts
        if fault_type != "Normal":
            severity = "Medium"
            if any("Critical" in issue for issue in issues):
                severity = "Critical"
            elif len(issues) >= 2:
                severity = "High"
                
            alerts.append({
                "timestamp": utc_timestamp(),
                "machine_id": machine_id,
                "type": "Fault Detection",
                "severity": severity,
                "message": f"{', '.join(issues)} detected in {machine_id}",
                "fault_type": fault_type
            })
            
        # 2. RUL Warnings
        rul_days = rul_info.get("rul_days")
        if rul_days is not None and rul_days < 10:
            severity = "Medium"
            if rul_days < 3:
                severity = "Critical"
            elif rul_days < 7:
                severity = "High"
                
            alerts.append({
                "timestamp": utc_timestamp(),
                "machine_id": machine_id,
                "type": "RUL Warning",
                "severity": severity,
                "message": f"Low Remaining Useful Life: {rul_days} days remaining",
                "fault_type": fault_type
            })
            
        return alerts

class AIAgent:
    def __init__(self):
        self.fault_detector = FaultDetector()
        self.rul_estimator = RULEstimator()
        self.alert_generator = AlertGenerator()
        self._machine_statuses: Dict[str, Dict] = {}
        self._lock = threading.RLock()
        
    def process_reading(self, reading: Dict) -> Dict:
        if not isinstance(reading, dict):
            raise ValueError("reading must be an object")

        machine_id = reading.get("machine_id", "M001")
        if not isinstance(machine_id, str) or not machine_id.strip():
            raise ValueError("reading.machine_id must be a non-empty string")

        fault_type, detected_issues = self.fault_detector.detect_fault(reading)
        self.rul_estimator.update_degradation(machine_id, reading)
        rul_info = self.rul_estimator.estimate_rul(machine_id)
        alerts = self.alert_generator.generate_alerts(machine_id, self.fault_detector, self.rul_estimator, reading)

        status = "Normal"
        if any("Critical" in issue for issue in detected_issues):
            status = "Critical"
        elif detected_issues:
            status = "Warning"

        recommendation = "No action required"
        if fault_type == "Bearing Wear":
            recommendation = "Lubricate bearings and schedule diagnostic verification."
        elif fault_type == "Misalignment":
            recommendation = "Perform shaft alignment correction procedures."
        elif fault_type == "Overheating":
            recommendation = "Check cooling systems and reduce machine load."
        elif fault_type == "Electrical Fault":
            recommendation = "Inspect electrical connections and check current draw safety parameters."
            
        result = {
            "machine_id": machine_id,
            "timestamp": reading.get("timestamp", utc_timestamp()),
            "status": status,
            "fault_type": fault_type,
            "detected_issues": detected_issues,
            "rul_days": rul_info.get("rul_days"),
            "rul_confidence": rul_info.get("confidence", 0.0),
            "alerts": alerts,
            "recommendation": recommendation
        }

        with self._lock:
            self._machine_statuses[machine_id] = deepcopy(result)
        return result

    def get_machine_status(self, machine_id: str) -> Optional[Dict]:
        with self._lock:
            status = self._machine_statuses.get(machine_id)
            return deepcopy(status) if status else None

    def get_all_machine_statuses(self) -> Dict:
        with self._lock:
            return {
                machine_id: deepcopy(status)
                for machine_id, status in self._machine_statuses.items()
            }
