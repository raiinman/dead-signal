# Dead Signal Ultimate Planner v1.2.4

## Loadout Report cleanup
- Removed the user-facing **Data Audit** section from the Combined Loadout / Loadout Report.
- Removed the report-only `selectedRecords()` and `renderDataAudit()` helpers.
- Kept record provenance, verification, pending-detail, and community-conflict metadata in the underlying catalog so pickers/data curation can still use it without cluttering the build report.
- Preserved equipped-item stats, set activation, Combined Build Effects, and Build Systems reporting.

## Version
- Planner: 1.2.4
- Schema: 14
