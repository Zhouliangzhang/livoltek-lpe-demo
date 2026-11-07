# Read-only grouped topology

Large models (more than 30 objects) use four independent zoomable diagrams. This is a presentation-only partition: no engineering model, saved layout, device asset, port or edge is changed.

The main distribution group follows recorded electrical paths between PCC, transformer and load boundaries. PV and BESS groups follow their electrical branches up to the main path and arrange descendants beneath each collection board. Remaining support objects and all communication/control relationships appear in the communication-control group. This heuristic is verified for the CI-20 single-zone project; unusual multi-zone or meshed topologies require further layout validation.

Each real node belongs to exactly one group. Each original edge is drawn exactly once, retaining its two port IDs. A cross-group endpoint appears as a dashed reference node, labelled 引用, without creating a new asset. Compact labels come from existing node names, not inferred device ratings. Four independent fit/zoom controls and pointer-centered wheel zoom are the only canvas interactions; dragging, panning, selection editing and connection creation remain disabled.

CI-20 distribution:

| Group | Owned objects | Reference appearances | Edges |
|---|---:|---:|---:|
| Main distribution | 8 | 0 | 6 |
| PV collection | 34 | 1 | 34 |
| BESS collection | 24 | 1 | 24 |
| Communication/control | 7 | 23 | 50 |
| Total | 73 | 25 appearances, not additional assets | 114 |

PV and BESS display two five-device collection trees. Communication/control references the twenty main devices instead of mixing those lines into the electrical diagrams. Animated simulation direction remains visible; numeric power labels are retained on the main-distribution diagram to avoid branch-label collisions.

Verification covers unique node ownership, exact edge conservation, endpoint availability, non-overlapping node rectangles in CI-20, deterministic layout after input ordering changes, model non-mutation, disabled dragging, zoom/fit operation, unchanged Save state and zoom retention across telemetry refresh. Small-project layout and the existing M1/M2 workflows remain covered by the browser suite.

The control group now uses the user-confirmed single-iEMS architecture and five small read-only views. See SINGLE_IEMS_CONTROL.md for current screenshots and edge accounting. Earlier ci20-grouped-control.png is the historical pre-correction view.
