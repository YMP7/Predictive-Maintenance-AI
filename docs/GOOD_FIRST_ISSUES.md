# Good First Issues (drafts)

Ready to paste into GitHub issues once the repository is opened to
contributors. Each one can be done without a database, hardware, or API keys
unless noted. Labels assume `good first issue` plus the listed area.

All adapter issues follow [CONTRIBUTING.md](../CONTRIBUTING.md#adding-a-machine-adapter):
read-only access, a simulator or fixture for CI, path-jailed config, and a
passing `python scripts/check_public_boundary.py`.

---

## 1. OPC-UA adapter (read-only)
**Labels:** `adapter`
Add `server/adapters/opcua_adapter.py` that reads configured node ids from an
OPC-UA server and returns `NormalizedReading`s.
- Use `asyncua` (or its sync wrapper). Only read services; no writes, no method calls.
- Ship a small in-process OPC-UA test server, like `server/adapters/modbus_simulator.py`.
- Node map from a JSON file, path-jailed like the Modbus register map (DEF-013).

**Done when:** `pytest tests/test_adapter_conformance.py --adapter opcua` passes, plus a test proving a write call raises.

## 2. Generic REST/JSON polling adapter
**Labels:** `adapter`
An adapter that polls an HTTP endpoint and maps JSON fields to channels via a
config file (field path, unit, min, max).
- HTTPS only by default; timeouts on every request; no credentials in config files (env vars only).
- Test with a local `http.server` fixture.

**Done when:** conformance passes for the new fixture id, and malformed or missing fields raise a clear error instead of returning zeros.

## 3. Prometheus adapter
**Labels:** `adapter`
Read host metrics (CPU, memory, disk, temperature) from a Prometheus HTTP API
(`/api/v1/query`) for a list of instances.
- Map PromQL queries to channels in config; normalize with documented min/max.
- Test against a recorded JSON response fixture.

**Done when:** conformance passes; an unknown instance raises `UnknownMachineError`.

## 4. Dataset loader: NASA IMS bearing dataset
**Labels:** `dataset`
A replay adapter for the IMS run-to-failure bearing data, similar to `CMAPSSAdapter`.
- Download at runtime into an ignored directory; do not commit data. Check and document the dataset's terms.
- Readings must be marked as replayed data in `metadata`, never as live.
- Compute per-window RMS and kurtosis features.

**Done when:** conformance passes when the data is present and the tests skip cleanly when it is not.

## 5. Dataset loader: AI4I 2020 predictive maintenance (UCI)
**Labels:** `dataset`
Same pattern as #4 for the AI4I 2020 tabular dataset.
- Sort by time/product id before windowing and add a test with shuffled rows (DEF-002).

**Done when:** conformance passes; shuffled input produces identical windows.

## 6. Monte Carlo dropout uncertainty for RUL
**Labels:** `ml`
`WorldModel` uses dropout between its LSTM layers (`dropout=0.2`,
`server/atlas/world_model.py`). Add an option to run N stochastic forward
passes at inference and return the mean and standard deviation of the
predicted RUL.
- Default off; existing outputs must not change when disabled.
- Seed the passes so tests are deterministic.
- Label the result as an estimate in the API response.

**Done when:** a test shows std > 0 with N > 1 and identical output to today with the option off.

## 7. Dashboard accessibility pass
**Labels:** `frontend`, `a11y`
Run axe (e.g. `@axe-core/react` in dev) on the main pages and fix what it finds.
- Keyboard navigation for tabs and dialogs, visible focus, `aria-label`s on icon buttons.
- Chart colors must not be the only way to tell series apart.

**Done when:** no axe violations of "serious" or "critical" impact on the monitoring and work-order pages; list remaining minor ones in the PR.

## 8. Tutorial: write your first adapter
**Labels:** `docs`
A step-by-step guide in `docs/tutorials/first_adapter.md` that builds the
`MinimalVibrationAdapter` from `tests/test_adapter_conformance.py` from
scratch and runs the conformance suite on it.

**Done when:** a new contributor can follow it on a fresh clone without a database; every command in it has been run.

## 9. Tutorial: train and evaluate the RUL model on C-MAPSS FD001
**Labels:** `docs`, `ml`
A notebook or markdown tutorial that preprocesses FD001, trains the world
model with a fixed seed on CPU, and reports RMSE.
- State hardware, run time, and seed next to every number.
- Save checkpoints under a new filename; never overwrite `data/models/`.

**Done when:** the tutorial runs end to end on CPU and its reported numbers are reproducible with the stated seed.

## 10. Lint cleanup: unused imports, then widen ruff
**Labels:** `chore`
`ruff.toml` currently checks only bug-class rules. Running the default rules
reports 323 findings (146 unused imports, 128 late imports, 23 unused
variables, 21 placeholder-less f-strings, measured 2026-10-08).
- Fix one rule per PR, starting with `F401`.
- Then add that rule to `select` in `ruff.toml`.

**Done when:** `ruff check .` passes with the widened rule set and the test suite is unchanged.
