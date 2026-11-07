# M1 + M2 implementation and acceptance plan

Goal: operational LV-01 engineering prototype using the recovered original baselines.
Status (2026-11-07): stages 1–4 implemented and validated for the LV-01 pilot; see VALIDATION.md for evidence and remaining production/product scope.
Architecture: React/TypeScript/X6 renders a schema-backed engineering model; FastAPI validates domain data and SQLite stores immutable revisions, plans, templates and reviews. View positions stay separate from engineering facts. No real-device endpoints or production release are implemented.

1. Preserve the 15 original baseline files; validate both original samples and rule pack. Implement schema plus semantic validation, optimistic revision persistence and immutable history. Test invalid references, domains, duplicate IDs/SNs, authorization and conflicts.
2. Implement LV-01 project, model/asset catalogue, three edge layers, editable properties/ports/JSON, add/remove/drag/connect, version save/load/export. Build with TypeScript; exercise browser save/reload.
3. Implement deterministic rule matching, versioned template review, dependent work packages, third-party interface-only tasks, missing input gates, immutable plan source snapshots, comments and simulated evidence records. Test draft production block, dependency ordering, stale-plan block and revision retention.
4. Implement explicitly simulated telemetry with quality/age/direction gating; test stale/missing values. Run API tests, production frontend build, browser workflow and record results.

Baseline precedence: revision chapters supersede legacy wording. Schema V1.1 intentionally still requires schema_version `1.0.0`; preserve it. The mixed-vendor example adds a second illustrative PV; the pilot labels both clearly and does not claim a certified 100 kW total. Runtime pilot enrichments are documented separately; original files remain unchanged.

Demo constraints: all approvals are local simulated engineering reviews, not authenticated manufacturer approvals. All SOP content is review guidance without invented wiring values. Production publishing always returns a block. LV-02/MV, real telemetry, RSP sync, media upload, identities and formal site permits are outside this pilot.
