# Product scope and L5-L6 interpretation

LIVOLTEK Project Engineer 是主设备厂家提供给 EPC 工程师的系统感知型安装调试辅助、现场故障排查及远程技术支持协同工具。它不取代 EPC 专业电气设计、施工管理、法定检验或合同验收工具。

- L1: Project definition and initial system framework.
- L2: Recorded electrical structure and boundaries.
- L3: Manufacturer models and installed assets, including third-party equipment.
- L4: Recorded device-to-device port relationships.
- L5 Configuration: System settings, planned settings and observed site values with sources. It does not design the electrical installation or dispatch commands merely because values are entered.
- L6 Engineering Rules & Review: Review L1-L5 for completeness, consistency, interface conditions and prerequisites for installation/commissioning. Outputs identify gaps, conflicts, technical-support questions and on-site verification requirements. A valid data model is not proof of normal system operation or acceptance.

The demo currently edits existing numeric settings. Communication addressing, control strategies, manufacturer-specific setting forms and verified operating thresholds still require controlled product templates and source documents. Existing approved values are retained as read-only reference records, not fabricated by this UI. No real device control, legal inspection certification, commissioning authorization or contractual acceptance is performed.

L6 uses explicit demo static checks and separately labels field commissioning/operating results as pending. Changing model data invalidates the previously displayed check result. Technical collaboration comments are distinct from formal approval and from manufacturer SOP template version governance.
