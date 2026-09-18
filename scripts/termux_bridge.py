"""
ATLAS Mobile Bridge — Termux:API HTTP Server
===========================================
Runs on Android devices inside Termux (or on any test host) to expose live hardware
telemetry (battery, thermals, CPU, memory) over HTTP for ATLAS MobileAdapter.

Usage on Android:
  1. Install Termux & Termux:API from F-Droid
  2. In Termux terminal:
       pkg update && pkg install python termux-api
       python termux_bridge.py
  3. Set TERMUX_API_URL in .env:
       TERMUX_API_URL=http://<PHONE_WIFI_IP>:8088
     Or via USB with ADB:
       adb forward tcp:8088 tcp:8088
       TERMUX_API_URL=http://127.0.0.1:8088
"""

import http.server
import json
import os
import shutil
import socketserver
import subprocess
import sys

PORT = int(os.environ.get("TERMUX_BRIDGE_PORT", 8088))
HAS_TERMUX = shutil.which("termux-battery-status") is not None


def get_live_mobile_telemetry() -> dict:
    """Fetch live battery status from Termux:API, falling back to psutil if testing."""
    if HAS_TERMUX:
        try:
            raw = subprocess.check_output(["termux-battery-status"], timeout=2.0)
            data = json.loads(raw.decode("utf-8"))
            # Termux keys: percentage, temperature, current, plugged, status
            return {
                "percentage": data.get("percentage", 85.0),
                "temperature": data.get("temperature", 32.0),
                "current": data.get("current", 350.0),
                "status": data.get("status", "DISCHARGING"),
                "plugged": data.get("plugged", "UNPLUGGED"),
            }
        except Exception as e:
            return {"error": str(e), "percentage": 80.0, "temperature": 30.0, "current": 300.0}

    # Fallback when testing bridge on non-Android machines
    try:
        import psutil
        battery = psutil.sensors_battery()
        pct = battery.percent if battery else 88.0
        return {
            "percentage": pct,
            "temperature": 31.5,
            "current": 420.0,
            "cpu_percent": psutil.cpu_percent(interval=None),
            "memory_percent": psutil.virtual_memory().percent,
            "source": "host_fallback"
        }
    except Exception:
        return {"percentage": 85.0, "temperature": 32.0, "current": 350.0}


class TermuxBridgeHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Concise logging
        sys.stderr.write(f"[TermuxBridge] {self.address_string()} - {args[0]} {args[1]}\n")

    def do_GET(self):
        if self.path in ("/battery", "/battery/"):
            data = get_live_mobile_telemetry()
            payload = json.dumps(data).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Connection", "close")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(payload)
        elif self.path == "/health":
            payload = b'{"status":"ok","bridge":"atlas-termux-bridge"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Connection", "close")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(payload)
        else:
            self.send_response(404)
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(b'{"error":"Not Found"}')


class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def main():
    print(f"==================================================")
    print(f" ATLAS Mobile Bridge Server (Multi-Threaded)")
    print(f" Listening on http://0.0.0.0:{PORT}")
    print(f" Termux:API detected: {HAS_TERMUX}")
    print(f" Endpoints: http://<IP>:{PORT}/battery")
    print(f"==================================================")
    with ThreadingHTTPServer(("0.0.0.0", PORT), TermuxBridgeHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down bridge...")


if __name__ == "__main__":
    main()
