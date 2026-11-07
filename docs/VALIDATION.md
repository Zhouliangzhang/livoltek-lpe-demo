# M1 + M2 pilot validation — 2026-11-07

## Verified scope

| Stage | Implementation | Validation |
| --- | --- | --- |
| Environment | D-drive isolated Python environment, locked npm dependencies, private GitHub origin | Dependencies installed; production build successful |
| Original baseline | 15 original files preserved; original schema and semantic validator reused | Legacy and mixed-vendor samples + rule pack PASS |
| M1 domain | Separate models/assets/nodes/ports/three edge types, L1/L2/L3, responsibility/authorization, parameters and interface mappings | Schema, missing references, duplicate IDs, SN, cycles, port domains and direction |
| M1 persistence | SQLite transactions, immutable revisions, optimistic revision check, history restore as new draft | Conflict rejection, restart persistence, history unchanged, view layout does not invalidate engineering hash |
| M1 UI | X6 icons, node drag, port editing, graphical and exact-port connections, model export, advanced JSON editor | Browser save/reload, drag, add third-party generator, reject AC-to-Ethernet edge, add valid electrical/communication edges |
| Simulation | Explicit mock E01 data; age, quality, missing and reverse handling | Unit cases plus browser reverse/stale arrow check |
| M2 | Original rule matching, source/template versions, dependency ordering, missing-input gates, third-party interface tasks, L3 boundary tasks | No unapproved third-party internal BESS task; safety gate retained when parameter absent; cycle rejected |
| Reviews | Versioned template content/rules, target comments and decisions, immutable plan snapshots | Template conflicts, old plan preservation, review target checks |
| Evidence | Append-only simulated results and evidence references | Missing evidence and blocked task rejection, FAIL retained after PASS, stale-plan rejection |
| Production boundary | No real device API, no real release | Production publish returns HTTP 403 |

Backend suite: 19 passing tests. Browser suite: 2 passing tests on Microsoft Edge. TypeScript check and Vite production build pass. Screenshots `demo-m1.png` and `demo-m2.png` are actual browser captures.

## Defects found and resolved during validation

- New-project copy retained old PROJECT parameter owner ID: remapped on copy.
- Editing while project load was pending could be overwritten: disable the form during operations; preserve selected project on reload.
- X6 parent auto-resize caused continually increasing canvas height: use a fixed-height canvas and observe width only; browser test asserts 560 px height.
- Baseline communication rule originally tested presence anywhere: restrict connection existence to the target node type.
- Manufacturer BESS guidance could match a third-party BESS: scope matching now requires LIVOLTEK equipment origin.
- Cross-account Windows test cleanup could fail on an older temporary directory: each run now gets a unique directory without sharing pytest cache.
- Required safety parameter absence could otherwise suppress a task: generate the safety gate as BLOCKED with explicit missing input.

## Known limitations

This is the LV-01 operational pilot, not full PRD delivery. LV-02/MV classification rules, real telemetry/adapters, authenticated approvals, real site permits, media uploads, offline sync and M3–M6 are not implemented. Evidence accepts references/text only. Complex parameters, interface mappings and authorization metadata are editable through the advanced schema editor. Template changes are simulation reviews, not manufacturer certification. Interface and boundary fallback tasks are built-in version-1 review checks; the three original rule templates are editable through the catalog. SQLite stores full domain snapshots, not normalized per-device SQL tables.

Current baseline input is mixed-vendor illustrative data, with a second PV added by the original source. No claim of certified vendor compatibility, protection calculation, physical wiring approval or total 100 kW PV capacity is made.

Non-blocking tooling notices: the X6-containing JavaScript bundle exceeds Vite's 500 kB advisory; the installed Starlette version warns that its HTTPX test-client adapter is deprecated. Tests pass; no production claim is based on these tools.

## Reproduce

Run `scripts/check.ps1` in PowerShell from the repository. Backend tests use a unique `.test-run-*` directory; browser tests start a dedicated API server on port 8001 with a new `.e2e-*.db`. The user demo database `demo.db` is unchanged by tests. Python packages are fixed in `backend/requirements.lock.txt`; frontend packages in `frontend/package-lock.json`.

Technical references used: https://x6.antv.antgroup.com/en/tutorial/basic/port and https://fastapi.tiangolo.com/tutorial/testing/ . Baseline revision chapters remain the product authority.

