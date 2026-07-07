import time
import os
import json
import threading
import sqlite3
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
import numpy as np
from dotenv import load_dotenv

from server.sensor_simulator import MultiMachineSimulator
from server.ai_agent import AIAgent

# Load environment variables
load_dotenv()

# Configure logging
log_level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, log_level_str, logging.INFO)
log_file = os.environ.get("LOG_FILE", "./logs/agent.log")

# Ensure logs dir exists
os.makedirs(os.path.dirname(log_file), exist_ok=True)

logging.basicConfig(
    level=log_level,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("DigitalTwin")


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

class DataService:
    def __init__(self):
        self.simulator = MultiMachineSimulator()
        self.agent = AIAgent()
        self.is_running = False
        
        # In-memory storage
        # Maps machine_id to List of telemetry readings
        self.telemetry_cache: Dict[str, List[Dict]] = {
            "M001": [], "M002": [], "M003": [], "M004": []
        }
        # Maps machine_id to latest status dict
        self.status_cache: Dict[str, Dict] = {}
        # List of all alert dicts
        self.alerts_log: List[Dict] = []
        
        self.loop_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # Load machine info from config
        self.machine_info = {}
        config_path = os.path.join(os.path.dirname(__file__), "config", "machines.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    self.machine_info = config.get("machines", {})
            except Exception as e:
                logger.error(f"Error loading machines config: {e}")
                
        # Fill default info if configuration failed
        for mid in ["M001", "M002", "M003", "M004"]:
            if mid not in self.machine_info:
                self.machine_info[mid] = {
                    "name": f"Machine {mid}",
                    "type": "General",
                    "location": "Main Hall"
                }

        # Initialize SQLite database
        os.makedirs(os.path.join(os.path.dirname(__file__), "data"), exist_ok=True)
        self.db_path = os.path.join(os.path.dirname(__file__), "data", "digital_twin.db")
        self._init_db()
        self._load_historical_data()

    def _init_db(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS telemetry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    machine_id TEXT,
                    timestamp TEXT,
                    vibration_x REAL,
                    vibration_y REAL,
                    vibration_z REAL,
                    vibration_rms REAL,
                    temperature REAL,
                    current REAL,
                    status TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    machine_id TEXT,
                    type TEXT,
                    severity TEXT,
                    message TEXT,
                    fault_type TEXT
                )
            """)
            conn.commit()
            conn.close()
            logger.info("SQLite database initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize SQLite database: {e}")

    def _load_historical_data(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Load telemetry
            telemetry_loaded = 0
            for machine_id in self.telemetry_cache.keys():
                cursor.execute("""
                    SELECT timestamp, vibration_x, vibration_y, vibration_z, vibration_rms, temperature, current, status
                    FROM telemetry
                    WHERE machine_id = ?
                    ORDER BY id DESC LIMIT 1000
                """, (machine_id,))
                rows = cursor.fetchall()
                for row in reversed(rows):
                    reading = {
                        "machine_id": machine_id,
                        "timestamp": row[0],
                        "vibration": {
                            "x": row[1],
                            "y": row[2],
                            "z": row[3],
                            "rms": row[4]
                        },
                        "temperature": row[5],
                        "current": row[6],
                        "status": row[7]
                    }
                    self.telemetry_cache[machine_id].append(reading)
                    telemetry_loaded += 1
            
            # Load alerts
            cursor.execute("""
                SELECT timestamp, machine_id, type, severity, message, fault_type
                FROM alerts
                ORDER BY id DESC LIMIT 500
            """)
            rows = cursor.fetchall()
            for row in reversed(rows):
                alert = {
                    "timestamp": row[0],
                    "machine_id": row[1],
                    "type": row[2],
                    "severity": row[3],
                    "message": row[4],
                    "fault_type": row[5]
                }
                self.alerts_log.append(alert)
                
            conn.close()
            logger.info(f"Loaded {telemetry_loaded} telemetry readings and {len(self.alerts_log)} alerts from historical DB.")
        except Exception as e:
            logger.error(f"Error loading historical data: {e}")

    def _save_telemetry_to_db(self, machine_id: str, reading: Dict, status: str):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO telemetry (machine_id, timestamp, vibration_x, vibration_y, vibration_z, vibration_rms, temperature, current, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                machine_id,
                reading["timestamp"],
                reading["vibration"]["x"],
                reading["vibration"]["y"],
                reading["vibration"]["z"],
                reading["vibration"]["rms"],
                reading["temperature"],
                reading["current"],
                status
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error saving telemetry to SQLite: {e}")

    def _save_alert_to_db(self, alert: Dict):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO alerts (timestamp, machine_id, type, severity, message, fault_type)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                alert["timestamp"],
                alert["machine_id"],
                alert["type"],
                alert["severity"],
                alert["message"],
                alert.get("fault_type", "Normal")
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error saving alert to SQLite: {e}")

    def start_simulation(self, interval: float = 1.0) -> None:
        with self._lock:
            if self.is_running:
                logger.info("Simulation is already running.")
                return
            self.is_running = True
            self.loop_thread = threading.Thread(target=self._run_simulation, args=(interval,), daemon=True)
            self.loop_thread.start()
            logger.info(f"Simulation loop started with interval {interval}s.")

    def stop_simulation(self) -> None:
        thread_to_join = None
        with self._lock:
            if not self.is_running:
                logger.info("Simulation is already stopped.")
                return
            self.is_running = False
            thread_to_join = self.loop_thread
            logger.info("Simulation loop stopped.")

        if thread_to_join and thread_to_join.is_alive():
            thread_to_join.join(timeout=5)

    def _run_simulation(self, interval: float):
        while self.is_running:
            try:
                # Generate and process readings
                for machine_id in self.machine_info.keys():
                    reading = self.simulator.get_machine_reading(machine_id)
                    result = self.agent.process_reading(reading)
                    
                    # Store reading
                    with self._lock:
                        # Append status into reading cache
                        reading_cached = {**reading, "status": result["status"]}
                        self.telemetry_cache[machine_id].append(reading_cached)
                        # Limit cache size
                        if len(self.telemetry_cache[machine_id]) > 1000:
                            self.telemetry_cache[machine_id].pop(0)
                        
                        # Update status cache
                        self.status_cache[machine_id] = {
                            "machine_id": machine_id,
                            "status": result["status"],
                            "fault_type": result["fault_type"],
                            "detected_issues": result["detected_issues"],
                            "rul_days": result["rul_days"],
                            "rul_confidence": result["rul_confidence"],
                            "recommendation": result["recommendation"],
                            "machine_info": self.machine_info[machine_id]
                        }
                        
                        # Log alerts
                        if result["alerts"]:
                            for alert in result["alerts"]:
                                self.alerts_log.append(alert)
                                if len(self.alerts_log) > 500:
                                    self.alerts_log.pop(0)
                                    
                    # Save to DB outside memory locks
                    self._save_telemetry_to_db(machine_id, reading, result["status"])
                    if result["alerts"]:
                        for alert in result["alerts"]:
                            self._save_alert_to_db(alert)
                            # Route alerts through alert_handler queue
                            try:
                                from server.alert_handler import get_alert_handler
                                get_alert_handler().queue_alert(alert)
                            except Exception as ex:
                                logger.error(f"Failed to queue alert in alert handler: {ex}")
                                    
                time.sleep(interval)
            except Exception as e:
                logger.error(f"Error in simulation loop: {e}")
                time.sleep(1)

    def get_machine_status(self, machine_id: str) -> Optional[Dict]:
        with self._lock:
            # If not yet generated in simulation, return a default mock normal state
            if machine_id not in self.status_cache:
                if machine_id in self.machine_info:
                    return {
                        "machine_id": machine_id,
                        "status": "Normal",
                        "fault_type": "Normal",
                        "detected_issues": [],
                        "rul_days": 30,
                        "rul_confidence": 0.90,
                        "recommendation": "No action required",
                        "machine_info": self.machine_info[machine_id]
                    }
                return None
            return self.status_cache.get(machine_id)

    def get_all_machines_status(self) -> List[Dict]:
        return [self.get_machine_status(mid) for mid in self.machine_info.keys()]

    def get_all_machines_info(self) -> List[Dict]:
        return [{"machine_id": k, **v} for k, v in self.machine_info.items()]

    def get_machine_telemetry(self, machine_id: str, limit: int = 100) -> List[Dict]:
        with self._lock:
            cache = self.telemetry_cache.get(machine_id, [])
            return cache[-limit:]

    def get_machine_trends(self, machine_id: str) -> Dict:
        telemetry = self.get_machine_telemetry(machine_id, limit=50)
        if not telemetry:
            return {
                "vibration": {"values": [], "mean": 0, "max": 0, "min": 0},
                "temperature": {"values": [], "mean": 0, "max": 0, "min": 0},
                "current": {"values": [], "mean": 0, "max": 0, "min": 0}
            }
            
        vib_vals = [t["vibration"]["rms"] for t in telemetry]
        temp_vals = [t["temperature"] for t in telemetry]
        curr_vals = [t["current"] for t in telemetry]
        
        return {
            "vibration": {
                "values": vib_vals,
                "mean": round(float(np.mean(vib_vals)), 2) if vib_vals else 0,
                "max": round(float(np.max(vib_vals)), 2) if vib_vals else 0,
                "min": round(float(np.min(vib_vals)), 2) if vib_vals else 0
            },
            "temperature": {
                "values": temp_vals,
                "mean": round(float(np.mean(temp_vals)), 2) if temp_vals else 0,
                "max": round(float(np.max(temp_vals)), 2) if temp_vals else 0,
                "min": round(float(np.min(temp_vals)), 2) if temp_vals else 0
            },
            "current": {
                "values": curr_vals,
                "mean": round(float(np.mean(curr_vals)), 2) if curr_vals else 0,
                "max": round(float(np.max(curr_vals)), 2) if curr_vals else 0,
                "min": round(float(np.min(curr_vals)), 2) if curr_vals else 0
            }
        }

    def get_recent_alerts(self, limit: int = 50) -> List[Dict]:
        with self._lock:
            return self.alerts_log[-limit:]

    def get_alerts_by_machine(self, machine_id: str, limit: int = 20) -> List[Dict]:
        with self._lock:
            m_alerts = [a for a in self.alerts_log if a["machine_id"] == machine_id]
            return m_alerts[-limit:]

    def get_dashboard_summary(self) -> Dict:
        statuses = self.get_all_machines_status()
        
        status_counts = {"Normal": 0, "Warning": 0, "Critical": 0}
        alert_severity_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
        
        total_rul = 0
        valid_rul_count = 0
        
        for status in statuses:
            status_counts[status["status"]] += 1
            if status["rul_days"] is not None:
                total_rul += status["rul_days"]
                valid_rul_count += 1
                
        for alert in self.alerts_log:
            sev = alert.get("severity", "Medium")
            alert_severity_counts[sev] = alert_severity_counts.get(sev, 0) + 1
            
        avg_rul = total_rul / valid_rul_count if valid_rul_count > 0 else 0
        
        return {
            "timestamp": utc_timestamp(),
            "total_machines": len(self.machine_info),
            "machine_status_counts": status_counts,
            "alert_severity_counts": alert_severity_counts,
            "average_rul_days": round(avg_rul, 1),
            "total_alerts": len(self.alerts_log),
            "machines": statuses
        }

# Global singleton
_data_service = None

def get_data_service():
    global _data_service
    if _data_service is None:
        _data_service = DataService()
    return _data_service
