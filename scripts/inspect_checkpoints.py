import os
import torch

def main():
    print("=== INSPECTING PYTORCH CHECKPOINTS IN data/models ===")
    models_dir = "data/models"
    if not os.path.exists(models_dir):
        print(f"Directory {models_dir} does not exist!")
        return

    for f in sorted(os.listdir(models_dir)):
        if f.endswith(".pt"):
            path = os.path.join(models_dir, f)
            try:
                ckpt = torch.load(path, map_location="cpu", weights_only=False)
                if isinstance(ckpt, dict):
                    cfg = ckpt.get("config")
                    sd = ckpt.get("model_state_dict", ckpt)
                    lstm_w = sd.get("lstm.weight_ih_l0")
                    fc_w = sd.get("encoder.0.weight")
                    feat_dim = None
                    if hasattr(cfg, "feature_dim"):
                        feat_dim = cfg.feature_dim
                    elif isinstance(cfg, dict):
                        feat_dim = cfg.get("feature_dim")
                    
                    shape_info = f"lstm.weight_ih_l0={list(lstm_w.shape)}" if lstm_w is not None else (f"encoder={list(fc_w.shape)}" if fc_w is not None else "no-lstm")
                    print(f"{f:<26} | config.feature_dim={feat_dim} | {shape_info}")
                else:
                    print(f"{f:<26} | type: {type(ckpt)}")
            except Exception as e:
                print(f"{f:<26} | Error: {e}")

if __name__ == "__main__":
    main()

