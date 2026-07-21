# C-MAPSS Dataset Directory

Place the NASA C-MAPSS turbofan degradation dataset files here before running
the LSTM training script.

## Required Files

```
data/cmapss/
├── train_FD001.txt   ← Training set, subset 1 (single operating condition)
├── test_FD001.txt    ← Test set, subset 1
├── RUL_FD001.txt     ← Ground-truth RUL labels for test set (one per unit)
│
│   (Optional — for multi-condition experiments in Month 3+)
├── train_FD002.txt
├── test_FD002.txt
├── RUL_FD002.txt
├── train_FD003.txt
├── test_FD003.txt
├── RUL_FD003.txt
├── train_FD004.txt
├── test_FD004.txt
└── RUL_FD004.txt
```

## Download

**Option A — NASA PCOE (official):**
https://data.nasa.gov/dataset/C-MAPSS-Aircraft-Engine-Simulator-Data/xaut-bemq

**Option B — Kaggle mirror (faster):**
https://www.kaggle.com/datasets/behrad3d/nasa-cmaps

Download `CMAPSSData.zip`, extract, and place the `.txt` files here.

## After Download — Run Training

```powershell
# From project root
$env:PYTHONPATH="."
python server/atlas/train_rul.py --subset FD001 --epochs 50

# Quick smoke-test (5 epochs, ~30 seconds)
python server/atlas/train_rul.py --quick
```

Training output will be saved to `data/models/cmapss_world_model.pt`.

## Dataset Description

- **FD001**: 100 training units, 1 operating condition, 1 fault mode (HPC Degradation)
- **FD002**: 260 training units, 6 operating conditions, 1 fault mode
- **FD003**: 100 training units, 1 operating condition, 2 fault modes
- **FD004**: 249 training units, 6 operating conditions, 2 fault modes

Start with FD001 — it is the standard benchmark and cleanest for initial validation.

## Sensor Schema

Each row: `unit_id  cycle  op1  op2  op3  s1 s2 ... s21`

The CMAPSSAdapter automatically drops 7 constant sensors (s1, s5, s6, s10, s16, s18, s19)
and uses the remaining **14 informative sensors** as model features.

## Citation

Saxena, A., Goebel, K., Simon, D., & Eklund, N. (2008). Damage propagation modeling
for aircraft engine run-to-failure simulation. In *2008 International Conference on
Prognostics and Health Management* (pp. 1-9). IEEE.
