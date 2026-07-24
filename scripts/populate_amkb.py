import argparse
import json
import logging
import os
import sys
from collections import deque
from pathlib import Path

import numpy as np
import torch

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from server.adapters.cmapss_adapter import CMAPSSAdapter
from server.atlas.amkb import AMKB, Experience
from server.atlas.machine_dna import MachineDNAEngine, DNA_DIM
from server.atlas.world_model import WorldModel, prepare_window

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ATLAS.Populate")

def main():
    parser = argparse.ArgumentParser(description="Populate AMKB and Machine DNA from C-MAPSS training data.")
    parser.add_argument("--limit", type=int, default=None, help="Process only N units (dry run).")
    parser.add_argument("--clear", action="store_true", help="Clear existing 'cmapss' rows from AMKB and Machine DNA.")
    args = parser.parse_args()

    # Init subsystems
    amkb = AMKB()
    dna_engine = MachineDNAEngine()

    if args.clear:
        logger.info("Clearing existing 'cmapss' domain data from AMKB and Machine DNA...")
        pool = amkb._get_pool()
        with pool.connection() as conn:
            conn.execute("DELETE FROM machine_dna WHERE domain = 'cmapss'")
            conn.execute("DELETE FROM amkb_experiences WHERE domain = 'cmapss'")
            conn.commit()

    # Idempotency guard: abort if not clearing and data exists
    if not args.clear:
        pool = amkb._get_pool()
        with pool.connection() as conn:
            amkb_count = conn.execute("SELECT count(*) FROM amkb_experiences WHERE domain = 'cmapss'").fetchone()[0]
            dna_count = conn.execute("SELECT count(*) FROM machine_dna WHERE domain = 'cmapss'").fetchone()[0]
        if amkb_count > 0 or dna_count > 0:
            logger.error(f"Data exists in domain 'cmapss' (AMKB: {amkb_count}, DNA: {dna_count}). Run with --clear to overwrite.")
            sys.exit(1)

    model_path = Path("data/models/cmapss_world_model.pt")
    if not model_path.exists():
        logger.error(f"WorldModel checkpoint not found at {model_path}")
        sys.exit(1)

    model = WorldModel.load(model_path)
    model.eval()

    adapter = CMAPSSAdapter(subset="FD001", split="train")
    adapter.connect()

    machine_ids = sorted(adapter.machine_ids)
    if args.limit:
        machine_ids = machine_ids[:args.limit]
        logger.info(f"Limiting processing to {args.limit} units for dry-run.")

    # --- PASS 1: Generate AMKB experiences & compute raw DNA ---
    
    logger.info("Starting Pass 1: Storing AMKB experiences and computing raw DNA...")
    raw_dnas = []
    unit_dna_mapping = {}

    for i, machine_id in enumerate(machine_ids, 1):
        readings = adapter.get_unit_history(machine_id)
        if not readings:
            continue
        
        logger.info(f"Processing unit {machine_id} ({i}/{len(machine_ids)}) - {len(readings)} cycles")
        
        buf = []
        unit_experiences = []
        
        for r in readings:
            buf.append(r.feature_vector)
            if len(buf) > 30:
                buf.pop(0)
            
            if len(buf) == 30:
                # Need to run inference
                window = prepare_window(buf, seq_len=30, feature_dim=14)
                out = model.predict(window)
                pred_rul = out.rul_pred
                sv = out.state_vector
                
                # Metadata must hold raw sensors for Machine DNA and raw_rul
                metadata = {
                    "sensors": r.raw_features,
                    "cycle": r.cycle,
                    "raw_rul": r.rul_label
                }
                
                clipped_rul = r.metadata.get("rul_capped", r.rul_label)
                
                exp_id = amkb.store_experience(
                    domain="cmapss",
                    machine_id=machine_id,
                    state_vector=sv,
                    cycle=r.cycle,
                    event_type="normal",
                    true_rul=clipped_rul,
                    predicted_rul=pred_rul,
                    health_index=r.health_index,
                    outcome=None,
                    metadata=metadata
                )
                
                # We need to construct an Experience object for compute_dna_raw
                # The AMKB store_experience just returns an ID, so we build it locally in-memory
                # to avoid hitting the DB N times.
                exp = Experience(
                    id=str(exp_id),
                    domain="cmapss",
                    machine_id=machine_id,
                    cycle=r.cycle,
                    event_type="normal",
                    state_vector=sv,
                    true_rul=clipped_rul,
                    predicted_rul=pred_rul,
                    health_index=r.health_index,
                    metadata=metadata,
                    recorded_at=None
                )
                unit_experiences.append(exp)
        
        if not unit_experiences:
            continue
            
        raw_dna = dna_engine.compute_dna_raw(unit_experiences)
        raw_dnas.append(raw_dna)
        unit_dna_mapping[machine_id] = {
            "raw_dna": raw_dna,
            "n_cycles": len(unit_experiences)
        }
        
        if args.limit:
            # Print sanity check for dimensions 10-15 (Failure signature sensors)
            logger.info(f"  Sanity check for {machine_id} Failure Dims (10-15):")
            # 10: s2, 11: s3, 12: s4, 13: s7, 14: s11, 15: s15
            logger.info(f"    s2_slope: {raw_dna[10]:.4f} (temp)")
            logger.info(f"    s3_slope: {raw_dna[11]:.4f} (temp)")
            logger.info(f"    s4_slope: {raw_dna[12]:.4f} (temp)")
            logger.info(f"    s7_slope: {raw_dna[13]:.4f} (pressure)")
            logger.info(f"    s11_slope: {raw_dna[14]:.4f} (pressure)")
            logger.info(f"    s15_slope: {raw_dna[15]:.4f} (bypass ratio)")

    # --- PASS 2: Compute global scaler and store normalized DNA ---
    
    if not raw_dnas:
        logger.warning("No DNA computed. Exiting.")
        sys.exit(0)
        
    logger.info("Starting Pass 2: Computing global scaler and storing normalized DNA...")
    stacked = np.stack(raw_dnas)  # shape (N, 16)
    
    global_mean = np.mean(stacked, axis=0)
    global_std = np.std(stacked, axis=0)
    
    scaler_path = Path("data/models/machine_dna_scaler.json")
    with open(scaler_path, "w") as f:
        json.dump({
            "mean": global_mean.tolist(),
            "std": global_std.tolist()
        }, f, indent=2)
    logger.info(f"Saved Machine DNA scaler to {scaler_path}")
    
    # Reload engine to pick up new scaler
    dna_engine = MachineDNAEngine()
    
    for machine_id, data in unit_dna_mapping.items():
        raw_vec = data["raw_dna"]
        n_cycles = data["n_cycles"]
        
        dna_engine.store_dna(
            domain="cmapss",
            machine_id=machine_id,
            dna_vector=raw_vec,  # it will be normalized inside store_dna
            components={},
            n_cycles_used=n_cycles
        )
    
    logger.info("Population complete.")

if __name__ == "__main__":
    main()
