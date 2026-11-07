# Generated L5 system settings

The shared `config/l5-catalog.json` is a versioned DRAFT checklist. L1 operation modes and energy features filter applicability; L3 device types and recorded port domains select communication, EMS and storage candidates. Each displayed row identifies its device model and master-data version. This is generic candidate generation, not an imported manufacturer-approved parameter catalogue.

The UI groups settings and supports device filtering. Planned and observed site values remain separate. Missing manufacturer evidence is always pending; manually entering a document reference does not verify applicability. No defaults or approved values are inferred and no commands are sent to equipment.

Values persist in the baseline schema's open `node.attributes.l5_settings` extension, keyed by setting key. Each record has planned, actual, reference_doc, model_id, master_data_version and template_version. The original baselines are unchanged. Model or checklist version mismatch disables editing until explicit reinitialization archives the record to l5_settings_history. Inactive settings remain stored after mode/interface changes, but are excluded from current applicable rows.

Backend checks validate the record shape, scalar types, IPv4 syntax, integer ports, universal numeric bounds and SOC minimum/maximum ordering. Bounds are format/logical checks, not manufacturer-safe operating ranges. L6 exposes missing values, stale versions and pending manufacturer evidence. Static validation does not establish normal system operation.

Validation: 27 backend tests; 11 frontend/browser suite tests; production TypeScript/Vite build. Coverage includes generation by mode/interface, empty defaults, stale-version archival, inactive-record retention, save/reload persistence and invalidation of previous L6 results.
