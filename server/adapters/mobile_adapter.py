"""
Mobile Adapter — ATLAS Machine Adapter Layer (Month 6)
======================================================
Provides telemetry from mobile Android and Windows Phone (Lumia) devices via
Wi-Fi (Termux:API or Lumia Web Bridge) and USB (ADB hardware dumpsys or Termux ADB bridge),
with realistic simulation fallbacks when physical hardware is not connected.

Design Principle:
Supports concurrent multi-device tracking (mobile_device_1 = Wi-Fi, mobile_device_2 = USB)
with non-blocking background polling to maintain sub-millisecond response times in the
ATLAS streaming loop.
"""

import json
import logging
import math
import os
import re
import subprocess
import threading
import time
from typing import Any, Dict, List, Optional
import urllib.request
import urllib.error

from server.adapters.base_adapter import (
    AdapterStatus,
    DomainType,
    MachineAdapter,
    NormalizedReading,
)

logger = logging.getLogger("ATLAS.MobileAdapter")

# Multi-device browser push registry
_browser_pushes: Dict[str, Dict[str, Any]] = {}
_browser_push_times: Dict[str, float] = {}
_latest_browser_push: Optional[Dict[str, Any]] = None
_latest_browser_push_time: float = 0.0


def push_browser_telemetry(data: Dict[str, Any]) -> None:
    """Register incoming live telemetry pushed from a web browser bridge (e.g. Lumia)."""
    global _latest_browser_push, _latest_browser_push_time
    target_unit = data.get("machine_id", "mobile_device_1")
    _browser_pushes[target_unit] = data
    _browser_push_times[target_unit] = time.time()
    _latest_browser_push = data
    _latest_browser_push_time = time.time()


def get_latest_browser_push(machine_id: str = "mobile_device_1") -> Optional[Dict[str, Any]]:
    """Return latest browser telemetry for target unit if received within the last 60 seconds."""
    global _latest_browser_push, _latest_browser_push_time
    # 1. Exact unit match
    if machine_id in _browser_pushes:
        if (time.time() - _browser_push_times.get(machine_id, 0.0)) < 60.0:
            return _browser_pushes[machine_id]
    # 2. Legacy fallback
    if _latest_browser_push is not None and (time.time() - _latest_browser_push_time) < 60.0:
        p_unit = _latest_browser_push.get("machine_id")
        if p_unit is None or p_unit == machine_id:
            return _latest_browser_push
    return None


def clear_browser_telemetry() -> None:
    """Clear registered browser telemetry (useful for test isolation)."""
    global _latest_browser_push, _latest_browser_push_time, _browser_pushes, _browser_push_times
    _browser_pushes.clear()
    _browser_push_times.clear()
    _latest_browser_push = None
    _latest_browser_push_time = 0.0


class MobileAdapter(MachineAdapter):
    """
    Adapter for mobile Android and Windows Phone (Lumia) telemetry.
    Supports dual concurrent devices:
      - mobile_device_1: Wi-Fi connection (Termux:API or Lumia Web Bridge)
      - mobile_device_2: USB connection (ADB dumpsys or Termux ADB port-forward)
    """

    def __init__(self, endpoint_url: Optional[str] = None) -> None:
        super().__init__()
        self._custom_endpoint_url = endpoint_url
        self._start_time = time.time()
        self._is_live = False
        self._sim_steps: Dict[str, int] = {"mobile_device_1": 0, "mobile_device_2": 0}

        # Cached live telemetry from background worker threads
        self._wifi_cache: Optional[Dict[str, Any]] = None
        self._wifi_cache_time: float = 0.0
        self._usb_cache: Optional[Dict[str, Any]] = None
        self._usb_cache_time: float = 0.0

        # Real hardware CPU tracking (proc/stat jiffies)
        self._last_cpu_idle: Optional[float] = None
        self._last_cpu_total: Optional[float] = None

        # Background worker management
        self._worker_running = False
        self._wifi_thread: Optional[threading.Thread] = None
        self._usb_thread: Optional[threading.Thread] = None

    @property
    def domain_id(self) -> str:
        return DomainType.MOBILE.value

    @property
    def machine_ids(self) -> List[str]:
        return ["mobile_device_1", "mobile_device_2"]

    @property
    def endpoint_url(self) -> str:
        return self._custom_endpoint_url or os.environ.get("TERMUX_API_URL", "http://127.0.0.1:8088")

    def _connect(self) -> None:
        """Start background polling workers for Wi-Fi and USB telemetry."""
        self._worker_running = True
        self._poll_wifi_once()
        self._update_aggregate_status()

        if self._wifi_thread is None or not self._wifi_thread.is_alive():
            self._wifi_thread = threading.Thread(target=self._wifi_worker_loop, daemon=True)
            self._wifi_thread.start()

        if not self._custom_endpoint_url:
            if self._usb_thread is None or not self._usb_thread.is_alive():
                self._usb_thread = threading.Thread(target=self._usb_worker_loop, daemon=True)
                self._usb_thread.start()

    def _disconnect(self) -> None:
        """Stop background polling workers."""
        self._worker_running = False
        self._is_live = False
        self._status = AdapterStatus.DISCONNECTED
        logger.info("[mobile] MobileAdapter disconnected.")

    def _update_aggregate_status(self) -> None:
        wifi_live = (self._wifi_cache is not None and (time.time() - self._wifi_cache_time) < 10.0)
        usb_live = (self._usb_cache is not None and (time.time() - self._usb_cache_time) < 20.0)
        browser_live = (get_latest_browser_push("mobile_device_1") is not None or get_latest_browser_push("mobile_device_2") is not None)
        
        self._is_live = wifi_live or usb_live or browser_live
        self._status = AdapterStatus.LIVE if self._is_live else AdapterStatus.SIMULATION

    def _wifi_worker_loop(self) -> None:
        """Daemon thread: continuously refreshes Wi-Fi telemetry cache."""
        while self._worker_running:
            try:
                self._poll_wifi_once()
            except Exception as e:
                logger.debug(f"[mobile] Wi-Fi background poll exception: {e}")
            self._update_aggregate_status()
            time.sleep(1.5)

    def _usb_worker_loop(self) -> None:
        """Daemon thread: continuously refreshes USB telemetry cache."""
        while self._worker_running:
            try:
                self._poll_usb_once()
            except Exception as e:
                logger.debug(f"[mobile] USB background poll exception: {e}")
            self._update_aggregate_status()
            time.sleep(2.0)

    def _probe_http_battery(self, url: str, timeout: float = 1.0) -> Optional[Dict[str, Any]]:
        """Safely fetch and parse Termux /battery endpoint."""
        try:
            req = urllib.request.Request(
                f"{url}/battery",
                headers={"User-Agent": "ATLAS-MobileAdapter/1.0", "Connection": "close"}
            )
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(req, timeout=timeout) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode("utf-8"))
        except Exception:
            pass
        return None

    def _poll_wifi_once(self) -> None:
        """Probe configured or discovered Wi-Fi Termux endpoint."""
        if self._custom_endpoint_url:
            candidates = [self._custom_endpoint_url]
        else:
            candidates = []
            env_wifi = os.environ.get("TERMUX_WIFI_URL")
            if env_wifi:
                candidates.append(env_wifi)
            candidates.append("http://192.168.1.3:8088")
            candidates.append("http://192.168.1.2:8088")

        for url in candidates:
            data = self._probe_http_battery(url, timeout=1.0)
            if data is not None:
                self._wifi_cache = {
                    "battery_percent": float(data.get("percentage", data.get("battery_percent", 80.0))),
                    "temperature_c": float(data.get("temperature", data.get("temperature_c", 30.0))),
                    "current_ma": float(data.get("current", data.get("current_ma", 350.0))),
                    "cpu_percent": float(data.get("cpu_percent", 28.0)),
                    "memory_percent": float(data.get("memory_percent", 52.0)),
                    "is_plugged": data.get("plugged", False),
                    "source": f"Wi-Fi (Termux @ {url.replace('http://', '')})",
                    "platform": "android",
                }
                self._wifi_cache_time = time.time()
                return

    def _poll_usb_once(self) -> None:
        """Probe USB device via Termux ADB forward (127.0.0.1:8088) or direct ADB hardware query."""
        # 1. Try Termux over ADB localhost forward first
        data = self._probe_http_battery("http://127.0.0.1:8088", timeout=0.6)
        if data is not None:
            self._usb_cache = {
                "battery_percent": float(data.get("percentage", data.get("battery_percent", 80.0))),
                "temperature_c": float(data.get("temperature", data.get("temperature_c", 30.0))),
                "current_ma": float(data.get("current", data.get("current_ma", 350.0))),
                "voltage_mv": float(data.get("voltage", 4150.0)),
                "cpu_percent": float(data.get("cpu_percent", 22.0)),
                "memory_percent": float(data.get("memory_percent", 48.0)),
                "accel_x": float(data.get("accel_x", 0.0)),
                "accel_y": float(data.get("accel_y", 0.0)),
                "accel_z": float(data.get("accel_z", 9.81)),
                "gyro_x": float(data.get("gyro_x", 0.0)),
                "gyro_y": float(data.get("gyro_y", 0.0)),
                "gyro_z": float(data.get("gyro_z", 0.0)),
                "light_lux": float(data.get("light_lux", 100.0)),
                "proximity_cm": float(data.get("proximity_cm", 5.0)),
                "mag_x": float(data.get("mag_x", 0.0)),
                "mag_y": float(data.get("mag_y", 0.0)),
                "mag_z": float(data.get("mag_z", 0.0)),
                "is_plugged": True,
                "source": "USB (Termux ADB @ 127.0.0.1:8088)",
                "platform": "android",
            }
            self._usb_cache_time = time.time()
            return

        # 2. Direct fast ADB shell hardware query (CPU jiffies, RAM, Battery, Bosch BMI320, TCS3701, QMC6308)
        try:
            cmd = "cat /proc/stat | head -n 1; echo ---MEM---; cat /proc/meminfo | head -n 5; echo ---BATT---; dumpsys battery; echo ---SENS---; dumpsys sensorservice"
            p = subprocess.run(
                ["adb", "shell", cmd],
                capture_output=True,
                text=True,
                timeout=6.0
            )
            if p.returncode == 0 and "Current Battery Service state" in p.stdout:
                stdout = p.stdout

                # A. Real dynamic CPU utilization via /proc/stat jiffies
                cpu_pct = 18.0
                if "---MEM---" in stdout:
                    try:
                        cpu_line = stdout.split("---MEM---")[0].strip()
                        cpu_parts = cpu_line.split()[1:]
                        jiffies = [float(x) for x in cpu_parts]
                        idle = jiffies[3] + (jiffies[4] if len(jiffies) > 4 else 0)
                        total = sum(jiffies)
                        if self._last_cpu_idle is not None and self._last_cpu_total is not None:
                            d_idle = idle - self._last_cpu_idle
                            d_total = total - self._last_cpu_total
                            if d_total > 0:
                                cpu_pct = max(0.0, min(100.0, (1.0 - d_idle / d_total) * 100.0))
                        self._last_cpu_idle = idle
                        self._last_cpu_total = total
                    except Exception as e:
                        logger.debug(f"[mobile] Error calculating CPU jiffies: {e}")

                # B. Real RAM utilization via /proc/meminfo
                mem_pct = 46.0
                if "---MEM---" in stdout and "---BATT---" in stdout:
                    try:
                        mem_section = stdout.split("---MEM---")[1].split("---BATT---")[0]
                        mem_tot_m = re.search(r'MemTotal:\s*(\d+)', mem_section)
                        mem_avail_m = re.search(r'MemAvailable:\s*(\d+)', mem_section)
                        if mem_tot_m and mem_avail_m:
                            total_kb = float(mem_tot_m.group(1))
                            avail_kb = float(mem_avail_m.group(1))
                            if total_kb > 0:
                                mem_pct = ((total_kb - avail_kb) / total_kb) * 100.0
                    except Exception as e:
                        logger.debug(f"[mobile] Error parsing meminfo: {e}")

                # C. Real Battery Service telemetry
                batt_section = stdout.split("---BATT---")[1].split("---SENS---")[0] if "---SENS---" in stdout else stdout
                level_match = re.search(r'^\s*level:\s*(\d+)', batt_section, re.M)
                temp_match = re.search(r'^\s*temperature:\s*(\d+)', batt_section, re.M)
                volt_match = re.search(r'^\s*voltage:\s*(\d+)', batt_section, re.M)
                usb_match = re.search(r'^\s*USB powered:\s*(true|false)', batt_section, re.M | re.I)
                curr_match = re.search(r'Max charging current:\s*(\d+)', batt_section)

                batt_pct = float(level_match.group(1)) if level_match else 80.0
                temp_c = (float(temp_match.group(1)) / 10.0) if temp_match else 32.0
                volt_mv = float(volt_match.group(1)) if volt_match else 4150.0
                is_plugged = (usb_match.group(1).lower() == "true") if usb_match else True
                current_ma = (float(curr_match.group(1)) / 1000.0) if curr_match else 500.0

                # D. Real hardware sensors via dumpsys sensorservice
                accel_x, accel_y, accel_z = 0.0, 0.0, 9.81
                gyro_x, gyro_y, gyro_z = 0.0, 0.0, 0.0
                light_lux = 100.0
                prox_cm = 5.0
                mag_x, mag_y, mag_z = 0.0, 0.0, 0.0

                if "---SENS---" in stdout:
                    sens_section = stdout.split("---SENS---")[1]

                    def _extract_last_event(sensor_name: str) -> Optional[List[float]]:
                        m = re.search(rf'{sensor_name}:\s*last\s+\d+\s+events([\s\S]*?)(?=\n\s*[a-zA-Z0-9_]+:\s*last|\Z)', sens_section)
                        if m:
                            ev_lines = [l.strip() for l in m.group(1).splitlines() if re.search(r'^\s*\d+\s*\(', l)]
                            if ev_lines:
                                last_line = ev_lines[-1]
                                vals_str = re.sub(r'^\d+\s*\([^)]*\)\s*', '', last_line)
                                return [float(x.strip()) for x in vals_str.split(',') if x.strip()]
                        return None

                    acc = _extract_last_event("bmi320_acc")
                    if acc and len(acc) >= 3:
                        accel_x, accel_y, accel_z = acc[0], acc[1], acc[2]

                    gyro = _extract_last_event("bmi320_gyro")
                    if gyro and len(gyro) >= 3:
                        gyro_x, gyro_y, gyro_z = gyro[0], gyro[1], gyro[2]

                    light = _extract_last_event("tcs3701_l")
                    if light and len(light) >= 1:
                        light_lux = light[0]

                    prox = _extract_last_event("tcs3701_p")
                    if prox and len(prox) >= 1:
                        prox_cm = prox[0]

                    mag = _extract_last_event("qmc6308")
                    if mag and len(mag) >= 3:
                        mag_x, mag_y, mag_z = mag[0], mag[1], mag[2]

                self._usb_cache = {
                    "battery_percent": batt_pct,
                    "temperature_c": temp_c,
                    "current_ma": current_ma,
                    "voltage_mv": volt_mv,
                    "cpu_percent": round(cpu_pct, 1),
                    "memory_percent": round(mem_pct, 1),
                    "accel_x": round(accel_x, 3),
                    "accel_y": round(accel_y, 3),
                    "accel_z": round(accel_z, 3),
                    "gyro_x": round(gyro_x, 4),
                    "gyro_y": round(gyro_y, 4),
                    "gyro_z": round(gyro_z, 4),
                    "light_lux": round(light_lux, 1),
                    "proximity_cm": round(prox_cm, 1),
                    "mag_x": round(mag_x, 2),
                    "mag_y": round(mag_y, 2),
                    "mag_z": round(mag_z, 2),
                    "is_plugged": is_plugged,
                    "source": "USB (ADB Cable: Android)",
                    "platform": "android",
                }
                self._usb_cache_time = time.time()
                return
        except Exception as e:
            logger.debug(f"[mobile] Error polling ADB USB telemetry: {e}")

    def _generate_simulation_reading(self, machine_id: str) -> Dict[str, Any]:
        """Generate realistic, organically fluctuating synthetic mobile telemetry covering all 16 channels."""
        now = time.time()
        self._sim_steps[machine_id] = self._sim_steps.get(machine_id, 0) + 1
        step = self._sim_steps[machine_id]

        # Multi-frequency continuous dynamic phase
        t = (now * 0.7) + (step * 0.25)

        if machine_id == "mobile_device_1":
            # 1. Dynamic CPU: oscillating base load with realistic spikes & jitter
            base_cpu = 0.18 + 0.14 * math.sin(t * 0.4) + 0.08 * math.cos(t * 0.85)
            burst = 0.28 if (math.sin(t * 1.25) > 0.72) else (0.16 if math.cos(t * 2.1) > 0.82 else 0.0)
            jitter = 0.03 * math.sin(t * 4.3) + 0.02 * math.cos(t * 7.1)
            cpu = max(0.08, min(0.92, base_cpu + burst + jitter))

            # 2. Dynamic RAM: smooth sinusoidal fluctuation
            mem = max(0.35, min(0.85, 0.52 + 0.15 * math.sin(t * 0.2) + 0.04 * math.cos(t * 0.6)))

            # 3. Dynamic Battery: continuous gradual drain
            battery_level = max(0.05, 0.90 - ((step * 0.0004) % 0.80))

            # 4. Temperature: tracks CPU workload with thermal curve
            temp_c = 30.0 + 4.5 * (0.5 + 0.5 * math.sin(t * 0.15)) + (8.0 * cpu)

            # 5. Dynamic Current & Voltage
            current_ma = 200.0 + 520.0 * cpu + 35.0 * math.sin(t * 1.5)
            volt_mv = 4120.0 - (150.0 * (1.0 - battery_level)) - (35.0 * cpu)

            # 6. Physical Motion (Bosch Sensortec BMI320 3-Axis Accel & Gyro Simulation)
            accel_x = 0.45 * math.sin(t * 1.7) + 0.15 * math.cos(t * 3.8)
            accel_y = 5.2 + 0.8 * math.cos(t * 1.2) + 0.25 * math.sin(t * 2.9)
            accel_z = 7.9 + 0.7 * math.sin(t * 0.95) + 0.2 * math.cos(t * 2.3)

            gyro_x = 0.10 * math.sin(t * 2.2) + 0.04 * math.cos(t * 5.1)
            gyro_y = 0.12 * math.cos(t * 1.6) + 0.05 * math.sin(t * 4.4)
            gyro_z = 0.07 * math.sin(t * 2.8)

            # 7. Ambient light & proximity
            light_lux = max(15.0, 160.0 + 95.0 * math.sin(t * 0.3) + 25.0 * math.cos(t * 0.8))
            prox_cm = 0.0 if (math.sin(t * 0.15) > 0.88) else 5.0

            # 8. Magnetometer
            mag_x = 16.5 + 2.5 * math.sin(t * 0.35)
            mag_y = -21.0 + 3.0 * math.cos(t * 0.25)
            mag_z = 26.0 + 2.0 * math.sin(t * 0.45)
            source = "Synthetic (Wi-Fi Sim)"
        else:
            # USB Secondary Sim
            base_cpu = 0.22 + 0.16 * math.cos(t * 0.35) + 0.10 * math.sin(t * 0.75)
            burst = 0.30 if (math.cos(t * 1.4) > 0.72) else (0.16 if math.sin(t * 1.9) > 0.82 else 0.0)
            jitter = 0.03 * math.cos(t * 4.1) + 0.02 * math.sin(t * 6.7)
            cpu = max(0.10, min(0.95, base_cpu + burst + jitter))

            mem = max(0.40, min(0.90, 0.60 + 0.12 * math.cos(t * 0.18) + 0.05 * math.sin(t * 0.5)))
            battery_level = min(1.0, 0.70 + ((step * 0.0003) % 0.28))
            temp_c = 34.0 + 3.5 * (0.5 + 0.5 * math.cos(t * 0.12)) + (7.0 * cpu)
            current_ma = 450.0 + 350.0 * cpu + 30.0 * math.cos(t * 1.8)
            volt_mv = 4180.0 - (80.0 * (1.0 - battery_level)) - (30.0 * cpu)

            accel_x = 0.15 * math.sin(t * 1.4) + 0.08 * math.cos(t * 3.2)
            accel_y = 0.25 * math.cos(t * 1.0) + 0.12 * math.sin(t * 2.5)
            accel_z = 9.81 + 0.35 * math.cos(t * 0.8) + 0.15 * math.sin(t * 1.9)

            gyro_x = 0.04 * math.cos(t * 1.9) + 0.02 * math.sin(t * 4.3)
            gyro_y = 0.05 * math.sin(t * 1.5) + 0.02 * math.cos(t * 3.8)
            gyro_z = 0.02 * math.cos(t * 2.3)

            light_lux = max(20.0, 130.0 + 60.0 * math.cos(t * 0.22) + 20.0 * math.sin(t * 0.7))
            prox_cm = 5.0
            mag_x = 18.2 + 1.8 * math.sin(t * 0.3)
            mag_y = -22.4 + 2.2 * math.cos(t * 0.2)
            mag_z = 27.5 + 1.5 * math.sin(t * 0.4)
            source = "Synthetic (USB Sim)"

        return {
            "battery_percent": round(battery_level * 100.0, 1),
            "temperature_c": round(temp_c, 1),
            "cpu_percent": round(cpu * 100.0, 1),
            "memory_percent": round(mem * 100.0, 1),
            "current_ma": round(current_ma, 1),
            "voltage_mv": round(volt_mv, 1),
            "accel_x": round(accel_x, 3),
            "accel_y": round(accel_y, 3),
            "accel_z": round(accel_z, 3),
            "gyro_x": round(gyro_x, 4),
            "gyro_y": round(gyro_y, 4),
            "gyro_z": round(gyro_z, 4),
            "light_lux": round(light_lux, 1),
            "proximity_cm": round(prox_cm, 1),
            "mag_x": round(mag_x, 2),
            "mag_y": round(mag_y, 2),
            "mag_z": round(mag_z, 2),
            "is_plugged": (machine_id == "mobile_device_2"),
            "source": source,
            "platform": "android",
        }

    def _poll_termux_live(self) -> Dict[str, Any]:
        """Legacy helper for single-endpoint poll compatibility."""
        if self._wifi_cache is not None and (time.time() - self._wifi_cache_time) < 8.0:
            return self._wifi_cache
        return self._generate_simulation_reading("mobile_device_1")

    def get_reading(self, machine_id: str) -> NormalizedReading:
        """
        Poll mobile telemetry and return a NormalizedReading.
        Differentiates between mobile_device_1 (Wi-Fi) and mobile_device_2 (USB)
        and populates all available hardware sensor channels into features.
        """
        if machine_id not in self.machine_ids:
            raise ValueError(f"Unknown machine_id: {machine_id}")

        now = time.time()
        is_unit_live = False
        raw_data: Dict[str, Any] = {}
        source_label = "Synthetic (Wi-Fi Sim)" if machine_id == "mobile_device_1" else "Synthetic (USB Sim)"
        platform_label = "android"

        # Check for matching browser push first (e.g. Lumia Web Bridge)
        browser_data = get_latest_browser_push(machine_id)

        if machine_id == "mobile_device_1":
            # Priority: Browser push targeting unit 1 -> Wi-Fi Cache -> Simulation
            if browser_data is not None:
                is_unit_live = True
                raw_data = browser_data
                source_label = browser_data.get("source", "Wi-Fi (Lumia Web Bridge)")
                platform_label = browser_data.get("platform", "windows_phone")
            elif self._wifi_cache is not None and (now - self._wifi_cache_time) < 8.0:
                is_unit_live = True
                raw_data = self._wifi_cache
                source_label = self._wifi_cache.get("source", "Wi-Fi (Termux:API)")
                platform_label = self._wifi_cache.get("platform", "android")
            else:
                is_unit_live = False
                raw_data = self._generate_simulation_reading("mobile_device_1")
                source_label = raw_data.get("source", "Synthetic (Wi-Fi Sim)")
                platform_label = "android"

        elif machine_id == "mobile_device_2":
            # Priority: Browser push targeting unit 2 -> USB Cache -> Simulation
            if browser_data is not None:
                is_unit_live = True
                raw_data = browser_data
                source_label = browser_data.get("source", "Lumia Web Bridge (USB/Secondary)")
                platform_label = browser_data.get("platform", "windows_phone")
            elif self._usb_cache is not None and (now - self._usb_cache_time) < 20.0:
                is_unit_live = True
                raw_data = self._usb_cache
                source_label = self._usb_cache.get("source", "USB (ADB Cable: Android)")
                platform_label = self._usb_cache.get("platform", "android")
            else:
                is_unit_live = False
                raw_data = self._generate_simulation_reading("mobile_device_2")
                source_label = raw_data.get("source", "Synthetic (USB Sim)")
                platform_label = "android"

        status_str = AdapterStatus.LIVE.value if is_unit_live else AdapterStatus.SIMULATION.value

        # Extract Raw Telemetry
        batt_pct = float(raw_data.get("battery_percent", raw_data.get("percentage", 80.0)))
        temp_c = float(raw_data.get("temperature_c", raw_data.get("temperature", 30.0)))
        cpu_pct = float(raw_data.get("cpu_percent", 25.0))
        mem_pct = float(raw_data.get("memory_percent", 50.0))
        current_ma = float(raw_data.get("current_ma", raw_data.get("current", 350.0)))
        volt_mv = float(raw_data.get("voltage_mv", raw_data.get("voltage", 4150.0)))

        accel_x = float(raw_data.get("accel_x", 0.0))
        accel_y = float(raw_data.get("accel_y", 0.0))
        accel_z = float(raw_data.get("accel_z", 9.81))
        gyro_x = float(raw_data.get("gyro_x", 0.0))
        gyro_y = float(raw_data.get("gyro_y", 0.0))
        gyro_z = float(raw_data.get("gyro_z", 0.0))
        light_lux = float(raw_data.get("light_lux", 100.0))
        prox_cm = float(raw_data.get("proximity_cm", 5.0))
        mag_x = float(raw_data.get("mag_x", 0.0))
        mag_y = float(raw_data.get("mag_y", 0.0))
        mag_z = float(raw_data.get("mag_z", 0.0))
        is_plugged = bool(raw_data.get("is_plugged", machine_id == "mobile_device_2"))

        # 1. Canonical 5 Model Channels (in [0.0, 1.0])
        battery_level = min(1.0, max(0.0, batt_pct / 100.0))
        battery_temp = min(1.0, max(0.0, (temp_c - 20.0) / 40.0))
        battery_current = min(1.0, max(0.0, abs(current_ma) / 2000.0))
        memory_used = min(1.0, max(0.0, mem_pct / 100.0))
        cpu_usage = min(1.0, max(0.0, cpu_pct / 100.0))

        # 2. Extended Hardware Sensors (normalized to [0.0, 1.0])
        battery_voltage = min(1.0, max(0.0, (volt_mv - 3000.0) / 1500.0))
        acc_x_norm = min(1.0, max(0.0, (accel_x + 19.6) / 39.2))
        acc_y_norm = min(1.0, max(0.0, (accel_y + 19.6) / 39.2))
        acc_z_norm = min(1.0, max(0.0, (accel_z + 19.6) / 39.2))
        vib_rms = min(1.0, max(0.0, math.sqrt(accel_x**2 + accel_y**2 + accel_z**2) / 20.0))
        gyro_x_norm = min(1.0, max(0.0, (gyro_x + 10.0) / 20.0))
        gyro_y_norm = min(1.0, max(0.0, (gyro_y + 10.0) / 20.0))
        gyro_z_norm = min(1.0, max(0.0, (gyro_z + 10.0) / 20.0))
        light_norm = min(1.0, max(0.0, light_lux / 1000.0))
        prox_norm = min(1.0, max(0.0, prox_cm / 10.0))
        mag_norm = min(1.0, max(0.0, math.sqrt(mag_x**2 + mag_y**2 + mag_z**2) / 100.0))

        # All 15 physical and compute channels exposed to dashboard & feature matrix
        features = {
            "battery_level": round(battery_level, 4),
            "battery_temp": round(battery_temp, 4),
            "battery_current": round(battery_current, 4),
            "cpu_usage": round(cpu_usage, 4),
            "memory_used_percent": round(memory_used, 4),
            "battery_voltage": round(battery_voltage, 4),
            "accel_x": round(acc_x_norm, 4),
            "accel_y": round(acc_y_norm, 4),
            "accel_z": round(acc_z_norm, 4),
            "vibration_rms": round(vib_rms, 4),
            "gyro_x": round(gyro_x_norm, 4),
            "gyro_y": round(gyro_y_norm, 4),
            "gyro_z": round(gyro_z_norm, 4),
            "ambient_light": round(light_norm, 4),
            "proximity": round(prox_norm, 4),
            "magnetic_field": round(mag_norm, 4),
        }

        # Thermal, compute, and physical vibration composite stress score
        stress_score = (
            (0.35 * battery_temp)
            + (0.25 * cpu_usage)
            + (0.20 * memory_used)
            + (0.10 * vib_rms)
            + (0.10 * (1.0 - battery_level))
        )

        uptime_seconds = int(time.time() - self._start_time)

        # Build detailed unnormalized raw features for physical engineering analysis
        full_raw_features = dict(raw_data)
        full_raw_features.update({
            "battery_percent": batt_pct,
            "temperature_c": temp_c,
            "current_ma": current_ma,
            "voltage_mv": volt_mv,
            "cpu_percent": cpu_pct,
            "memory_percent": mem_pct,
            "accel_x_mps2": accel_x,
            "accel_y_mps2": accel_y,
            "accel_z_mps2": accel_z,
            "vibration_rms_mps2": round(math.sqrt(accel_x**2 + accel_y**2 + accel_z**2), 3),
            "gyro_x_rads": gyro_x,
            "gyro_y_rads": gyro_y,
            "gyro_z_rads": gyro_z,
            "ambient_light_lux": light_lux,
            "proximity_cm": prox_cm,
            "mag_x_ut": mag_x,
            "mag_y_ut": mag_y,
            "mag_z_ut": mag_z,
            "is_plugged": is_plugged,
        })

        operational_ctx = {
            "platform": platform_label,
            "source": source_label,
            "transport": "wifi" if machine_id == "mobile_device_1" else "usb",
            "soc_architecture": "MediaTek MT6833 (Dimensity 700 8-Core)" if (is_unit_live and machine_id == "mobile_device_2") else "ARMv8-A Octa-Core",
            "accel_hardware": "Bosch Sensortec BMI320 (3-Axis Accelerometer)",
            "gyro_hardware": "Bosch Sensortec BMI320 (3-Axis Gyroscope)",
            "light_hardware": "AMS TCS3701 (Ambient Light Sensor)",
            "prox_hardware": "AMS TCS3701 (Proximity Sensor)",
            "mag_hardware": "QST QMC6308 (3-Axis Magnetometer)",
            "total_hardware_sensors": 29 if (is_unit_live and machine_id == "mobile_device_2") else 16,
        }

        metadata = {
            "source": source_label,
            "simulated": not is_unit_live,
            "transport": "wifi" if machine_id == "mobile_device_1" else "usb",
            "battery_charging": is_plugged,
            "total_channels": len(features),
        }

        return NormalizedReading(
            domain=self.domain_id,
            machine_id=machine_id,
            timestamp=NormalizedReading.timestamp_now(),
            health_index=round(stress_score, 4),
            cycle=uptime_seconds,
            rul_label=None,
            features=features,
            raw_features=full_raw_features,
            operational_ctx=operational_ctx,
            metadata=metadata,
            adapter_status=status_str,
        )
