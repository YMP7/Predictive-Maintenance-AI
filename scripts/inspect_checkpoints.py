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
                    keys = list(ckpt.keys())
                    # Check if it has an encoder or lstm or input layer
                    input_shape = None
                    for k in ckpt:
                        if "weight" in k and ("encoder" in k or "lstm" in k or "fc" in k or "linear" in k or "input" in k):
                            input_shape = (k, ckpt[k].shape)
                            break
                    if input_shape:
                        print(f"{f:<26} | key: {input_shape[0]:<30} | shape: {input_shape[1]}")
                    else:
                        first_k = keys[0] if keys else "empty"
                        shape = ckpt[first_k].shape if hasattr(ckpt[first_k], "shape") else type(ckpt[first_k])
                        print(f"{f:<26} | first: {first_k:<28} | shape: {shape}")
                else:
                    print(f"{f:<26} | type: {type(ckpt)}")
            except Exception as e:
                print(f"{f:<26} | Error: {e}")

if __name__ == "__main__":
    main()
