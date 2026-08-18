import sys
import time
from pathlib import Path
import numpy as np

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from server.adapters.laptop_adapter import LaptopAdapter
from server.atlas.rul_engine import RULEngine

def main():
    print("=== SPOT CHECK: Raw Health Index vs EMA Smoothing (25 readings) ===")
    adapter = LaptopAdapter()
    adapter.connect()
    machine_id = adapter.machine_ids[0]

    engine = RULEngine(domain="laptop", cycles_per_day=0.14)

    raw_history = []
    ema_history = []

    print(f"{'Idx':<4} | {'Raw Health':<12} | {'EMA Smoothed':<12} | {'RUL Days':<10} | {'Status':<16} | {'Confidence':<10}")
    print("-" * 75)

    for i in range(1, 26):
        reading = adapter.get_reading(machine_id)
        pred = engine.update(machine_id, reading)

        raw_val = reading.health_index
        raw_history.append(raw_val)

        # Access internal EMA fallback state
        hist = engine._ema._history[machine_id]
        if len(hist) >= engine._ema.MIN_HISTORY:
            y_raw = np.array(hist)
            # median filter window=5
            y_med = np.copy(y_raw)
            for j in range(len(y_raw)):
                s, e = max(0, j - 2), min(len(y_raw), j + 3)
                y_med[j] = np.median(y_raw[s:e])
            # EMA with alpha=0.15
            y_ema = np.zeros_like(y_med)
            y_ema[0] = y_med[0]
            for j in range(1, len(y_med)):
                y_ema[j] = 0.15 * y_med[j] + 0.85 * y_ema[j - 1]
            ema_val = float(y_ema[-1])
            ema_history.append(ema_val)
            ema_str = f"{ema_val:.4f}"
        else:
            ema_str = "Warming Up"

        print(f"{i:<4} | {raw_val:<12.4f} | {ema_str:<12} | {pred.rul_days:<10.1f} | {pred.status:<16} | {pred.confidence:<10.4f}")
        time.sleep(0.5)

    adapter.disconnect()

    raw_arr = np.array(raw_history)
    ema_arr = np.array(ema_history)

    print("-" * 75)
    print("=== SUMMARY METRICS ===")
    print(f"Raw Health Variance:   {np.var(raw_arr):.6f} (Std: {np.std(raw_arr):.4f}, Range: [{np.min(raw_arr):.4f}, {np.max(raw_arr):.4f}])")
    if len(ema_arr) > 0:
        print(f"EMA Health Variance:   {np.var(ema_arr):.6f} (Std: {np.std(ema_arr):.4f}, Range: [{np.min(ema_arr):.4f}, {np.max(ema_arr):.4f}])")
        noise_reduction = (1.0 - (np.var(ema_arr) / np.var(raw_arr))) * 100.0
        print(f"Noise Variance Reduction: {noise_reduction:.1f}%")

if __name__ == "__main__":
    main()
