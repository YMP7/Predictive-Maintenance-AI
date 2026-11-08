"""
scripts/modbus_bridge.py: poll a Modbus TCP device and push its registers into ATLAS.

Reads the holding registers with ModbusAdapter (engineering units) and posts each
poll to POST /api/ingest/{machine_id} with a device token, so the readings take the
same validated path as every other device. With --simulate it starts the bundled
ModbusSimulator first; print the profile with --simulate too so it is marked
simulated (SIMULATED badges).

One-time setup, as admin (the P4 onboarding wizard does this for you):
  python scripts/modbus_bridge.py --machine-id pump_m1 --simulate --print-profile > profile.json
  PUT  /api/admin/sensor-profiles/pump_m1   with profile.json
  POST /api/admin/devices {"machine_id": "pump_m1", "protocol": "modbus"}  -> token
Then:
  set ATLAS_DEVICE_TOKEN=<token>
  python scripts/modbus_bridge.py --machine-id pump_m1 --simulate
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server.adapters.modbus_adapter import DEFAULT_REGISTER_MAP, ModbusAdapter  # noqa: E402

# the channels whose rise means wear; speed, pressure and power factor are shown but not weighted
HEALTH_WEIGHTS = {"temperature_c": 1.0, "vibration_mms": 1.0, "current_a": 0.5}


def sensor_profile(machine_id: str, simulated: bool) -> dict:
    return {
        "machine_id": machine_id,
        "domain": "modbus",
        "display_name": f"Motor-driven pump {machine_id}",
        "simulated": simulated,
        "channels": [
            {"channel": c.name, "feature": c.name, "unit": c.unit, "valid_min": c.min_val, "valid_max": c.max_val,
             "sampling_hz": 1.0, "health_weight": HEALTH_WEIGHTS.get(c.name, 0.0)}
            for c in DEFAULT_REGISTER_MAP
        ],
    }


def push(api: str, machine_id: str, token: str, values: dict) -> int:
    body = json.dumps({"ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "values": values}).encode()
    req = urllib.request.Request(f"{api}/api/ingest/{machine_id}", data=body, method="POST",
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except urllib.error.URLError:
        return 599  # API unreachable; keep polling


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine-id", default="pump_m1")
    ap.add_argument("--api", default=os.environ.get("ATLAS_API", "http://127.0.0.1:8000"))
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5020)
    ap.add_argument("--simulate", action="store_true", help="start the bundled simulator on --port")
    ap.add_argument("--state", choices=["idle", "nominal", "degraded"], default="nominal")
    ap.add_argument("--interval", type=float, default=1.0)
    ap.add_argument("--print-profile", action="store_true", help="print the sensor profile JSON and exit")
    args = ap.parse_args()

    if args.print_profile:
        print(json.dumps(sensor_profile(args.machine_id, args.simulate), indent=2))
        return 0
    token = os.environ.get("ATLAS_DEVICE_TOKEN")
    if not token:
        print("Set ATLAS_DEVICE_TOKEN to the device token issued for this machine.", file=sys.stderr)
        return 2

    sim = None
    if args.simulate:
        from server.adapters.modbus_simulator import ModbusSimulator
        sim = ModbusSimulator(host=args.host, port=args.port, machine_id=args.machine_id)
        args.port = sim.start()
        sim.set_state(args.state)
    adapter = ModbusAdapter(host=args.host, port=args.port, machine_ids=[args.machine_id], domain_id="modbus")
    adapter.connect()
    print(f"Polling {args.host}:{args.port} every {args.interval}s, pushing to {args.api} as {args.machine_id}")
    try:
        while True:
            if sim is not None:
                sim.step()
            raw = adapter.get_reading(args.machine_id).raw_features
            values = {c.name: raw[c.name] for c in DEFAULT_REGISTER_MAP if isinstance(raw.get(c.name), (int, float))}
            status = push(args.api, args.machine_id, token, values)
            if status >= 400:
                print(f"push failed: HTTP {status}", file=sys.stderr)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        return 0
    finally:
        adapter.disconnect()
        if sim is not None:
            sim.stop()


if __name__ == "__main__":
    sys.exit(main())
