"""
scripts/run_modbus_sim.py — Standalone Industrial Modbus TCP Asset Simulator CLI
================================================================================
Launches an in-process Modbus TCP server simulating an industrial rotating machine
(e.g., CNC milling spindle or slurry pump) over holding registers.

Usage:
  python scripts/run_modbus_sim.py [--host 127.0.0.1] [--port 5020] [--state nominal] [--interval 1.0]

Options:
  --host TEXT       Host interface to bind to [default: 127.0.0.1]
  --port INT        TCP port to listen on [default: 5020]
  --unit-id INT     Modbus slave unit ID [default: 1]
  --machine-id TEXT Machine asset ID [default: cnc_spindle_01]
  --state TEXT      Initial operating regime: idle, nominal, degraded [default: nominal]
  --interval FLOAT  Seconds between simulation steps [default: 1.0]
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server.adapters.modbus_simulator import ModbusSimulator


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ATLAS Modbus TCP Asset Simulator CLI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind")
    parser.add_argument("--port", type=int, default=5020, help="Modbus TCP port")
    parser.add_argument("--unit-id", type=int, default=1, help="Modbus slave unit identifier")
    parser.add_argument("--machine-id", default="cnc_spindle_01", help="Simulated machine asset identifier")
    parser.add_argument(
        "--state",
        choices=["idle", "nominal", "degraded"],
        default="nominal",
        help="Initial operational regime",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Step perturbation update interval in seconds",
    )

    args = parser.parse_args()

    print(f"============================================================")
    print(f" ATLAS Industrial Modbus TCP Simulator")
    print(f"============================================================")
    print(f" Binding to        : {args.host}:{args.port}")
    print(f" Machine Asset ID  : {args.machine_id}")
    print(f" Modbus Unit ID    : {args.unit_id}")
    print(f" Initial Regime    : {args.state}")
    print(f" Step Interval     : {args.interval}s")
    print(f" Holding Registers : 40001 (Temp), 40002 (Vib), 40003 (Curr),")
    print(f"                     40004 (RPM), 40005 (Press), 40006 (PF)")
    print(f" Press Ctrl+C to terminate.")
    print(f"============================================================")

    sim = ModbusSimulator(
        host=args.host,
        port=args.port,
        unit_id=args.unit_id,
        machine_id=args.machine_id,
    )

    try:
        actual_port = sim.start()
        sim.set_state(args.state)
        print(f"[OK] Simulator actively listening on {args.host}:{actual_port}")
        cycle = 0
        while True:
            time.sleep(args.interval)
            sim.step()
            cycle += 1
            if cycle % 10 == 0:
                print(f"[INFO] Cycle {cycle}: Holding registers: {sim._registers[:6]}")
    except KeyboardInterrupt:
        print("\n[STOP] Shutting down Modbus simulator...")
    finally:
        sim.stop()
        print("[OK] Modbus simulator stopped cleanly.")


if __name__ == "__main__":
    main()
