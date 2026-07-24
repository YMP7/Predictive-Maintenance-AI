import os
import sys
from pathlib import Path
import numpy as np

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from server.atlas.amkb import AMKB

def main():
    amkb = AMKB()
    pool = amkb._get_pool()
    
    with pool.connection() as conn:
        amkb_count = conn.execute("SELECT count(*) FROM amkb_experiences WHERE domain = 'cmapss'").fetchone()[0]
        dna_count = conn.execute("SELECT count(*) FROM machine_dna WHERE domain = 'cmapss'").fetchone()[0]
        
        print("=== Final Database Counts ===")
        print(f"amkb_experiences count: {amkb_count}")
        print(f"machine_dna count: {dna_count}")
        print("=============================\n")
        
        # Test 3 different near-failure queries from DIFFERENT units
        fail_queries = conn.execute(
            """
            SELECT id, machine_id, cycle, rul_cycles, embedding FROM amkb_experiences 
            WHERE domain = 'cmapss' AND rul_cycles <= 5 
            AND machine_id IN ('unit_1', 'unit_2', 'unit_3')
            ORDER BY machine_id, cycle DESC
            """
        ).fetchall()
        
        # Keep just one per unit
        fail_queries = {row[1]: row for row in fail_queries}.values()
        
        # Test 3 different healthy queries from DIFFERENT units
        health_queries = conn.execute(
            """
            SELECT id, machine_id, cycle, rul_cycles, embedding FROM amkb_experiences 
            WHERE domain = 'cmapss' AND rul_cycles >= 120 
            AND machine_id IN ('unit_4', 'unit_5', 'unit_6')
            ORDER BY machine_id, cycle ASC
            """
        ).fetchall()
        
        health_queries = {row[1]: row for row in health_queries}.values()

    def run_query(q_name, queries):
        print(f"=== {q_name} ===")
        for row in queries:
            q_id, q_machine_id, q_cycle, q_rul, q_emb_str = row
            sv = np.array([float(x) for x in str(q_emb_str).strip("[]").split(",")], dtype=np.float32)
            
            # Request k=11 to allow filtering out the exact self-match
            results = amkb.retrieve_similar(sv, k=11, domain="cmapss")
            
            # Exclude self
            neighbors = [r for r in results if r.id != str(q_id)][:10]
            neighbor_ruls = [r.true_rul for r in neighbors if r.true_rul is not None]
            
            avg = sum(neighbor_ruls) / len(neighbor_ruls) if neighbor_ruls else 0.0
            print(f"Query: {q_machine_id} @ cycle {q_cycle} (true_rul = {q_rul})")
            print(f"Neighbors (N={len(neighbor_ruls)}): {[round(x, 1) for x in neighbor_ruls]}")
            print(f"Average Neighbor RUL: {avg:.2f}\n")

    run_query("Near-Failure Retrieval Tests", fail_queries)
    run_query("Healthy Retrieval Tests", health_queries)

if __name__ == "__main__":
    main()
