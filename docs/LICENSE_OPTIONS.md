# License Options

**Status:** decision pending with the project owner. No license change has been
made. This is an engineering summary, **not legal advice**. Patent and
licensing consequences depend on jurisdiction and should be confirmed with a
patent attorney before anything is published or relicensed.

## Starting point (facts, measured 2026-10-08)

- The repository already contains an **MIT** `LICENSE` file, present since the
  initial commit. GitHub reports the repository license as MIT.
- The repository is **public**. Code already distributed under MIT stays
  available under MIT to anyone who obtained it. A later license change
  applies to new versions only.
- Third-party research PDFs have been removed from the tree in v1.1 (they
  remain in git history). See `docs/REFERENCES.md`.

## Options compared

| | MIT (current) | Apache-2.0 | Open-core split | Source-available (e.g. BSL 1.1, Elastic 2.0, PolyForm) | Defensive publication |
|---|---|---|---|---|---|
| OSI open source | Yes | Yes | Public part yes; private part no | **No** | n/a (a disclosure strategy, combined with any license) |
| Express patent grant to users | **No** (silent; any implied license is uncertain) | **Yes**, from each contributor, for patents their contribution necessarily infringes (§3) | Only for the public part, if that part is Apache-2.0 | Varies; usually limited or none | n/a |
| Patent retaliation clause | No | **Yes**: a user who sues claiming the work infringes a patent loses their patent license (§3) | Public part only | Varies | n/a |
| Owner can still license patents on the code it publishes | Unclear (implied-license risk) | **No** for the published code: the owner's own contributions carry the §3 grant | **Yes** for methods kept only in the private part | Generally yes, subject to license terms | **No**: publishing is intended to make the method unpatentable by anyone, including the owner |
| Commercial use by others | Allowed | Allowed | Public part allowed; private part by separate agreement | Restricted (until a change date, for BSL) | n/a |
| Attracts outside contributors | High | High (preferred by many companies for the patent clarity) | Medium to high for the SDK | Low to medium | n/a |
| Contribution paperwork | DCO is enough | DCO is enough | DCO for the public part; a CLA if outside code may flow into the private part | Usually a CLA | n/a |
| Obligations on users | Keep copyright notice | Keep notices, state changes, carry `NOTICE` file | Per part | Per license | n/a |

### MIT (status quo)
Simple and widely accepted. It says nothing explicit about patents, which cuts
both ways: users get no clear patent license, and the owner's position on any
patent covering the published code is uncertain.

### Apache-2.0
Permissive like MIT, plus an **express patent grant** (Section 3) and a
**patent-retaliation** termination. For a project that wants outside
contributors and corporate adopters, this is the common choice. The key
consequence for the owner: any code the owner publishes under Apache-2.0
comes with a royalty-free patent license to everyone for that code. Methods
the owner may want to patent or license should not be published under
Apache-2.0 first.

### Open-core split
Publish the Adapter SDK, adapters, and conformance suite (under Apache-2.0 or
MIT), and keep engine-internal modules in a private repository. v1.1 already
enforces this boundary technically: `scripts/check_public_boundary.py` proves
the public part builds and passes its tests with the internal modules
import-blocked (69 tests passed, 0 import violations, measured 2026-10-08).
The cost is maintaining two repositories and a stable interface between them.

### Source-available
Licenses such as Business Source License 1.1, Elastic License 2.0, or the
PolyForm family publish source while restricting commercial or competing use.
They are not open source by the OSI definition, so some contributors and
companies will not engage. BSL converts to an open-source license after a
change date chosen by the licensor.

### Defensive publication
Deliberately publishing a detailed description of a method so it becomes
prior art and no one, including the owner, can patent it. It is cheap and
fast, and fits if the goal is freedom to operate rather than exclusivity. It
is irreversible.

## Decision needed

Choose one license (or the open-core combination) for the public part.
Until then, v1.1 does not add or change any license file.
