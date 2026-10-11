# Maintained verification cases: Shared

All cases are automated regression cases, executed with isolated temporary or
in-memory libraries, deterministic synthetic notes and non-unique GTK test apps.
Cleanup closes stores and disposes every test window; temporary directories are
removed. No personal notes or desktop session configuration are used.

| ID / title | Traceability | Risk / classification | Objective and Given / When / Then | Automation |
| --- | --- | --- | --- | --- |
| SH-T01 Fresh profile | SH-01, CTX-01–03, CR-02, AC-06 | High / integration | Given a fresh library, when creating a profile and a note, then exactly one Shared exists, ordinary context is null and creation targets Shared; restart resumes null. | test_shared.SharedBehaviorTests |
| SH-T02 In-place upgrade | MIG-01–03, AC-01–02 | Critical / migration | Given schema 5 with General and ordinary contexts, hidden and deleted notes, when upgrading, then all note fields, IDs, settings and valid ordinary contexts are exact; General context becomes null. | test_shared_migration.SharedMigrationTests |
| SH-T03 Collisions and locale | SH-04, MIG-04, AC-11 | High / migration | Given ordinary Shared, Shared (2) and Compartilhado, when converting, then suffixes avoid collisions without moving notes; locale changes labels only. | test_shared_migration, test_organization |
| SH-T04 Snapshot and rollback | MIG-06, AC-12 | Critical / recovery | Given a supported library, when snapshot, DDL or version publication fails or process stops, then schema/data/context remain original and snapshot is private; repeat startup is idempotent. | test_migrations, test_shared_migration |
| SH-T05 Shared window intersection | CTX-04–06, AC-03 | High / controller | Given Shared and two projects, when switching projects, then Shared editor identity survives without presentation/disposal and only the new project's open editors map. | test_shared.SharedDesktopTests |
| SH-T06 Hidden and deleted | CTX-07, SEARCH-01, AC-04 | High / integration | Given open, hidden and deleted Shared notes, when switching and searching, then hidden is searchable but stays closed and deleted is absent. | test_shared |
| SH-T07 Creation and opening | UX-03, CR-01–02, SEARCH-03, AC-05–06 | High / integration/UI | Given an ordinary group or null, when using Shared +, normal New or opening Shared, then the proper destination is used and ordinary context is retained. | test_shared, test_shared_panel |
| SH-T08 Move eligibility | FLOW-01–02, AC-07 | High / controller | Given notes across memberships, when moving into/out of Shared, then metadata/open flags persist, visible intersection is reused and foreign notes disappear. | test_shared |
| SH-T09 Deletion | DEL-01–03, AC-08–09 | High / integration/UI | Given an active group/profile, when deleting with transfer or Delete all, then context and confirmation agree, Shared is protected, and rollback/stale-preview guards remain. | test_shared, test_organization_service, test_organization_dialogs |
| SH-T10 Search context | SEARCH-01–04, AC-10 | Medium / integration/UI | Given Shared notes across profiles, when searching/opening or switching, then union is unique, breadcrumbs accurate, foreign Shared restores profile's saved context and successful switches clear search. | test_shared, test_shared_panel, test_panel_context |
| SH-T11 Save failure | CTX-08, AC-13 | Critical / controller/UI | Given pending edits and injected save/prepare/commit errors, when switching, then transaction rolls back, buffers and editor identities survive and retry works. | test_context_controller, test_panel_context, test_shared |
| SH-T12 Notice | MIG-07 | Medium / UI/persistence | Given a migrated library with collision metadata, when opening/dismissing notice, then no note text is exposed and dismissal survives restart. | test_shared_migration, test_shared_panel |
| SH-T13 Recovery drill | MIG-06 | Critical / operational | Given an upgraded copy and validated schema-5 snapshot, when old v0.8.0 reader rejects schema 6 and snapshot is restored with app stopped, then old reader opens all original values; newer DB and WAL/SHM recovery files are preserved. | isolated recovery script and execution record |
| SH-T14 Native mapping and performance | UX-01–03, CTX-04–08 | Medium / desktop | Given an isolated X11 session and synthetic notes, when creating, switching, moving, hiding and restarting, then GTK windows match the union; record timing and screenshots. | isolated native harness and execution record |

Exact commands, environment, outcomes and qualification limits are recorded in
[execution.md](execution.md) when verification is complete. Wayland compositor
placement and Orca speech require their own environment; no claim is inferred
from X11 or GTK accessible properties.
