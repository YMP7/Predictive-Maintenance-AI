# Contributing to ATLAS

Thanks for your interest. This guide covers how to set up, what a good pull
request looks like, and the sign-off every commit needs.

## Developer Certificate of Origin (DCO)

Every commit in a pull request must be signed off. By signing off you certify
the [Developer Certificate of Origin 1.1](https://developercertificate.org/):
that you wrote the change, or otherwise have the right to submit it under the
project's license.

Sign off by adding `-s` when you commit:

```bash
git commit -s -m "feat(adapter): add OPC-UA adapter"
```

This appends a line with your real name and email:

```
Signed-off-by: Jane Doe <jane@example.com>
```

Forgot? Fix the last commit with `git commit --amend -s --no-edit`, or a whole
branch with `git rebase --signoff main`. CI checks every commit in the PR.

## Setup

```bash
pip install -r requirements.txt
pip install -r requirements-ml.txt --extra-index-url https://download.pytorch.org/whl/cpu
(cd client && npm ci)
pip install pre-commit && pre-commit install
```

You do not need a database or any API keys for adapter work. The backend test
suite needs TimescaleDB; see the README Quick Start, or let CI run it.

## Pull requests

- Keep each PR to one topic. Use [Conventional Commit](https://www.conventionalcommits.org/) prefixes (`feat`, `fix`, `docs`, `test`, `ci`, `chore`).
- Run `pre-commit run --all-files` before pushing.
- Add or update tests. A bug fix should come with a test that fails without it.
- Label data honestly. Any numbers in a PR description, doc or test must say
  whether they are **measured**, **simulated**, **replayed** or **estimated**,
  and on what hardware or environment.

## Adding a machine adapter

Adapters are the easiest way to contribute. An adapter subclasses
`MachineAdapter` (`server/adapters/base_adapter.py`) and is specified in
[docs/ADAPTER_SDK_SPEC.md](docs/ADAPTER_SDK_SPEC.md).

1. Implement the adapter in `server/adapters/<name>_adapter.py`.
2. Register a fixture id for it in the `adapter_instance` fixture in
   `tests/test_adapter_conformance.py`. If it talks to hardware, ship a
   simulator (see `server/adapters/modbus_simulator.py`) so CI can test it.
3. Run the conformance suite for just your adapter:
   ```bash
   python -m pytest tests/test_adapter_conformance.py --adapter <fixture-id>
   ```
4. Run the boundary gate. It is the required CI check for adapter PRs:
   ```bash
   python scripts/check_public_boundary.py
   ```

Rules that the conformance suite and reviewers enforce:

- **Read-only.** Adapters must never write to a machine (for Modbus: only
  function codes 03/04).
- **No silent fallbacks.** Unknown machine ids raise; untrained domains report
  `is_trained=False` and refuse inference.
- **Path-jailed config.** Any file path from configuration must be resolved
  and checked against a base directory.
- **Adapters must not import** `server.atlas.simulation`, `decision`,
  `machine_dna`, `explain`, `adaptive_context`, or `server.agent_tools`. The
  boundary gate fails if they do.

## Reporting security issues

Do not open public issues for vulnerabilities. See [SECURITY.md](SECURITY.md).

## Code of conduct

This project follows the [Code of Conduct](CODE_OF_CONDUCT.md).
