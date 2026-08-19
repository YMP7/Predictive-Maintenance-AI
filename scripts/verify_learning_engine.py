import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from server.atlas.learning_engine import LearningEngine

def main():
    print("=== Real Retraining Smoke Test with DB Logging ===")
    engine = LearningEngine()
    
    result = engine.retrain_domain(
        domain="cmapss",
        trigger_reason="manual",
        epochs=1,
        forced_candidate_rmse=15.01,
    )
    
    print(f"Domain:         {result.domain}")
    print(f"Trigger:        {result.trigger_reason}")
    print(f"Pre-RMSE:       {result.rmse_before:.4f}")
    print(f"Post-RMSE:      {result.rmse_after:.4f}")
    print(f"Success:        {result.success}")
    print(f"Notes:          {result.notes}")

    print("\n=== Verifying DB Persistence from learning_events ===")
    history = engine.get_learning_history(domain="cmapss", limit=1)
    for h in history:
        print(f"ID: {h['id']} | Time: {h['triggered_at']} | Reason: {h['trigger_reason']} | Success: {h['success']}")
        print(f"Notes: {h['notes']}")

    print("\nLearning Engine smoke test completed successfully!")

if __name__ == "__main__":
    main()
