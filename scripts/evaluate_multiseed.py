import sys
from pathlib import Path
import numpy as np
import logging

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from server.atlas.train_rul import train

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("ATLAS.multiseed")

def run_multiseed_evaluation():
    seeds = [42, 43, 44, 45, 46]
    
    rmses = []
    phms = []
    
    logger.info(f"Starting multi-seed evaluation with seeds: {seeds}")
    
    for s in seeds:
        logger.info(f"--- Running training for seed {s} ---")
        metrics = train(
            subset="FD001",
            epochs=50,
            batch_size=256,
            lr=1e-3,
            seq_len=30,
            hidden_size=64,
            num_layers=2,
            dropout=0.2,
            quick=False,
            seed=s
        )
        
        rmse = metrics["benchmark"]["rmse"]
        phm = metrics["benchmark"]["phm_score"]
        
        rmses.append(rmse)
        phms.append(phm)
        
        logger.info(f"Seed {s} Results - RMSE: {rmse:.4f}, PHM: {phm:.2f}")

    mean_rmse = np.mean(rmses)
    std_rmse = np.std(rmses)
    
    mean_phm = np.mean(phms)
    std_phm = np.std(phms)
    
    logger.info("=========================================")
    logger.info("       MULTI-SEED EVALUATION RESULTS      ")
    logger.info("=========================================")
    logger.info(f"Seeds tested: {seeds}")
    logger.info(f"RMSE: {mean_rmse:.4f} ± {std_rmse:.4f}")
    logger.info(f"PHM Score: {mean_phm:.2f} ± {std_phm:.2f}")
    logger.info("=========================================")
    
    # Validation criteria — PHM is the PRIMARY lock-in gate (asymmetric,
    # industrially meaningful metric). RMSE is reported but is secondary;
    # see ATLAS_PROJECT_CONTEXT.md decisions log for the reasoning.
    target_rmse = 15.0
    target_phm = 400.0
    phm_std_limit = 0.25 * mean_phm

    rmse_pass = mean_rmse < target_rmse
    phm_pass = mean_phm < target_phm
    phm_std_pass = std_phm < phm_std_limit

    logger.info(f"RMSE target (<{target_rmse}):          {'PASS' if rmse_pass else 'MISS'} ({mean_rmse:.4f})")
    logger.info(f"PHM target (<{target_phm}):             {'PASS' if phm_pass else 'MISS'} ({mean_phm:.2f})")
    logger.info(f"PHM Std target (<{phm_std_limit:.2f}):  {'PASS' if phm_std_pass else 'MISS'} ({std_phm:.2f})")
    logger.info("=========================================")

    if phm_pass and phm_std_pass:
        logger.info("CONCLUSION: LOCKED IN — PHM criteria (primary gate) satisfied and stable across seeds.")
        if not rmse_pass:
            logger.info(f"NOTE: RMSE ({mean_rmse:.4f}) is marginally above the {target_rmse} target, "
                        f"but PHM is the accepted lock-in metric per project policy.")
    else:
        logger.info("CONCLUSION: NEEDS REVIEW — PHM mean or stability criteria not met. "
                    "Consider architectural escalation.")

if __name__ == "__main__":
    run_multiseed_evaluation()
