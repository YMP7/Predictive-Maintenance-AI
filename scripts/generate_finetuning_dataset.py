import json
import random
import os

# Phase A of Fine-Tuning architecture: Generate a synthetic dataset
# This script creates JSONL entries mimicking the input an agent sees
# and the ideal response an expert would give.

FAULTS = [
    {
        "fault_mode": "bearing_wear",
        "telemetry_desc": "High vibration RMS with slightly elevated temperature.",
        "vibration_range": (3.5, 5.5),
        "temp_range": (55, 65),
        "current_range": (2.6, 2.9),
        "alert": "Bearing Wear Warning",
        "output": "The high vibration levels combined with slightly elevated temperatures and the recent Bearing Wear Warning strongly indicate progressive bearing failure. I recommend scheduling immediate maintenance. I will create a critical work order to replace the bearings."
    },
    {
        "fault_mode": "overheating",
        "telemetry_desc": "Extreme temperature with normal vibration.",
        "vibration_range": (0.3, 0.8),
        "temp_range": (70, 95),
        "current_range": (2.4, 2.8),
        "alert": "Overheating Critical",
        "output": "The telemetry shows critical overheating without a corresponding spike in vibration, pointing toward a cooling system failure or ventilation blockage rather than mechanical wear. The machine should be stopped immediately. I am issuing a high-priority work order to inspect the cooling fans and ventilation."
    },
    {
        "fault_mode": "misalignment",
        "telemetry_desc": "Moderate vibration and fluctuating current draw.",
        "vibration_range": (2.5, 4.0),
        "temp_range": (48, 55),
        "current_range": (3.2, 4.0),
        "alert": "Motor Misalignment",
        "output": "Elevated vibration coupled with high and fluctuating current draw indicates shaft or motor misalignment. This puts excess load on the motor. I recommend realigning the shaft within the next 48 hours to prevent bearing damage. A medium-priority work order has been created."
    },
    {
        "fault_mode": "normal",
        "telemetry_desc": "All parameters within baseline.",
        "vibration_range": (0.2, 0.6),
        "temp_range": (42, 46),
        "current_range": (2.4, 2.6),
        "alert": "None",
        "output": "The machine is running optimally. Vibration, temperature, and current draw are all within stable baselines. No maintenance action is required at this time."
    }
]

def generate_entry():
    fault = random.choice(FAULTS)
    machine_id = random.choice(["M001", "M002", "M003", "M004"])
    
    vib = round(random.uniform(*fault["vibration_range"]), 2)
    temp = round(random.uniform(*fault["temp_range"]), 1)
    curr = round(random.uniform(*fault["current_range"]), 2)
    
    input_text = (
        f"Telemetry for {machine_id} -> Vibration: {vib} mm/s, "
        f"Temperature: {temp}C, Current: {curr} A. "
        f"Recent Alerts: {fault['alert']}"
    )
    
    instruction = f"Analyze the telemetry and alerts for {machine_id} and provide a diagnostic recommendation."
    
    return {
        "instruction": instruction,
        "input": input_text,
        "output": fault["output"]
    }

if __name__ == "__main__":
    output_file = "dataset_finetuning.jsonl"
    num_samples = 500
    
    with open(output_file, "w") as f:
        for _ in range(num_samples):
            f.write(json.dumps(generate_entry()) + "\n")
            
    print(f"Generated {num_samples} samples and saved to {output_file}")
