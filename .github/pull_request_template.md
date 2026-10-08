## What and why

<!-- One or two sentences. Link the issue: Fixes #123 -->

## How it was tested

<!-- Commands you ran and their result. Say what environment (OS, Python, DB running or not). -->

## Checklist

- [ ] Every commit is signed off (`git commit -s`, see CONTRIBUTING.md).
- [ ] `pre-commit run --all-files` passes.
- [ ] Tests added or updated; a bug fix includes a test that fails without it.
- [ ] Adapter PRs: `python scripts/check_public_boundary.py` passes, and the adapter is registered in the conformance fixture.
- [ ] Numbers in this PR are labelled **measured**, **simulated**, **replayed** or **estimated**.
- [ ] No credentials, hostnames, or machine identifiers in code, logs or screenshots.
