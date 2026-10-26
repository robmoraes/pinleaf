# Tasks: Profiles and note groups

Status: implementation merged in [PR #24](https://github.com/robmoraes/pinleaf/pull/24).
T01..T15 and T17 have
focused evidence; T16 and T18 retain desktop/performance qualification follow-ups.
See [execution evidence](execution-2026-10-10.md) and the final
[automated desktop qualification](automation-2026-10-10.md). The 0.8.0 changes
are promoted in [CHANGELOG.md](../../CHANGELOG.md); release preparation is
handled separately on `release/0.8.0`, with the qualification follow-ups retained.

## Sources

- [Specification](spec.md)
- [Technical plan](plan.md)
- [UX](ux.md)
- [Migration contract](contracts/migration-v5.json)
- [Architecture decision](adr-001-context-storage-and-recovery.md)
- [Maintained verification cases](verification.md)

## Execution Rules

Follow the dependency order below. Each task includes its focused verification;
do not defer all tests to the final task. Keep existing note workflows passing
through each mergeable slice. Introduce required `Note.group_id`, SQL conversion,
service creation and test-fixture changes together in T05.

Use temporary databases and synthetic notes. Desktop checks use an isolated
`XDG_DATA_HOME` and the application's development data configuration. Never
migrate or delete the developer's real note library for QA. GTK tests explicitly
skip when a display is unavailable; a skip does not satisfy desktop acceptance.

Mark a task complete only when its behavior and validation pass. Record test
results, source revision, environment, observed failures/skips and evidence in
a separate execution record created when checks run. Keep reusable scenarios
in [verification.md](verification.md) unchanged by execution results.

## Ordered Tasks

### T01: Establish isolated fixtures and contract checks

- [x] Complete T01 and its focused validation.

Depends on: none. Trace: AC-10 and the migration contract.

Create deterministic schema-1..4 fixtures containing open, hidden and deleted
notes, appearance/geometry variations and app settings. Use the shared data in verification cases;
keep checks comparing stored values independent of display defaults. Connect
contract validation to maintained automated checks rather than a one-off script.

Done when fixtures are isolated/repeatable, contract references resolve, and a
deliberately changed preservation field or target-version mismatch is detected.

### T02: Add organization identities and name rules

- [x] Complete T02 and its focused validation.

Depends on: T01. Trace: CTX-01, CTX-02, CTX-03; AC-11, AC-12.

Add Profile, Group, ActiveContext and SearchScope models plus domain name/label
helpers without GTK imports. Validate trimming, blank names, 80/81-code-point
boundaries, NFC/case-folded uniqueness and General/Geral reservation. Select
the initial localized profile name once; identify General independently of locale.

Done when focused domain tests cover composed/decomposed Unicode, case collisions,
localization without identity changes and preservation of user-entered names.

### T03: Establish explicit SQLite transaction ownership

- [x] Complete T03 and its focused validation.

Depends on: T01. Trace: CTX-09, DEL-07 and plan transaction ownership.

Refactor NoteStore/migration writes to support an outer transaction without
intermediate commits. Keep standalone writes durable. Establish shared-connection
access for OrganizationStore and explicit rollback behavior. Ensure migration
DDL executes without `executescript()` committing an enclosing transaction.

Done when a failed composite write leaves no partial changes, successful outer
transactions commit once, and existing standalone note/appearance tests pass.

### T04: Add validated private pre-upgrade snapshots

- [x] Complete T04 and its focused validation.

Depends on: T01, T03. Trace: migration contract; TC-CTX-001, TC-CTX-002.

Add the SQLite backup helper, unique filenames, private permissions and integrity/
source-version validation. Detect source changes between snapshot and write-lock
acquisition. Abort before schema changes on backup, permission, integrity or stale
snapshot failure. Do not prune or upload backups.

Done when a snapshot opens independently with its original values, permissions
match the contract, and injected failures leave the source unchanged.

### T05: Migrate to required membership and bootstrap Pessoal/Geral

- [x] Complete T05 and its focused validation.

Depends on: T02, T03, T04. Trace: CTX-01, CTX-02, CTX-04, CTX-10;
AC-10, AC-11; TC-CTX-001, TC-CTX-002.

Add schema 5, foreign keys/indexes, profile/group/context stores and the required
Note membership. Wire backup before existing-library upgrades. Rebuild notes with
explicit column mapping and one commit; migrate every retained row to the initial
Personal/Pessoal -> General/Geral. Update constructors, SQL conversions, creation
and existing fixtures together. Fresh databases use the same bootstrap. Add the
schema-5 organization fixture builder for subsequent service/controller cases.

Done when every supported legacy version preserves original note values/settings,
failure during DDL/copy/version update rolls back completely, repeat startup does
not reseed, newer/malformed/nonempty-unversioned schemas are refused without
mutation, and existing note workflows pass with required membership.

### T06: Implement profile/group creation, rename and saved context

- [x] Complete T06 and its focused validation.

Depends on: T05. Trace: CTX-02, CTX-03, CTX-04, CTX-10, FLOW-02;
AC-02, AC-11, AC-12, AC-17.

Implement OrganizationService operations with injectable IDs/clocks, live-name
uniqueness, automatic General, Create and activate, and last-used group persistence.
Validate ownership/live references and repair invalid saved-context metadata using
the documented fallback. Fail on broken memberships/missing General rather than
silently recreating a library. Return effects without manipulating GTK windows.

Done when service tests cover create/rename, conflicts, protected General, return
to each profile's last group, startup repair and actual same-context no-ops.

### T07: Make note creation, movement and search context-aware

- [x] Complete T07 and its focused validation.

Depends on: T05, T06. Trace: FLOW-01, FLOW-03, FLOW-04, FLOW-05, FLOW-06;
AC-06, AC-07, AC-08; TC-CTX-006.

Resolve active membership for new notes, including the tray service path. Add
individual movement preserving note metadata/open state, geometry-only persistence
and the three search scopes. Filter live membership in SQL, then reuse spec 010's
full-content Unicode/literal matching and creation ordering. Return breadcrumb
identity/labels without making search activate a context.

Done when service tests cover cross-profile moves into/out of the active group,
hidden/deleted filtering, later-in-content matches, accent/case/whitespace matching,
ordering, invalid destinations and no unintended context/timestamp changes.

### T08: Implement atomic container disposal and preview revalidation

- [x] Complete T08 and its focused validation.

Depends on: T06, T07. Trace: DEL-01, DEL-02, DEL-03, DEL-04, DEL-05, DEL-06,
DEL-07; AC-13, AC-14, AC-15, AC-16; TC-CTX-007, TC-CTX-008, TC-CTX-009.

Implement deletion preview and final transfer/delete operations for groups and
profiles. Transfer every retained note to one external live group, or use existing
soft deletion and container tombstones. Handle empty/only-deleted containers,
General/last-profile protection, active/last-context repair and live-name reuse.
Revalidate identities, membership/count and destination within the final transaction.

Done when tests cover both disposal modes for active/inactive containers, hidden
and retained-deleted notes, empty containers, invalid/internal destinations,
stale previews and rollback after partial SQL changes. Autosaved text alone must
not invalidate a preview; changed affected membership must require review.

### T09: Implement the save/prepare/commit/reconcile controller

- [x] Complete T09 and its focused validation.

Depends on: T06, T07, T08. Trace: CTX-05, CTX-06, CTX-07, CTX-08, CTX-09,
FLOW-02, FLOW-04, DEL-07; AC-01, AC-04, AC-05, AC-16, AC-17;
TC-CTX-004, TC-CTX-005.

Define GTK-free window interfaces and the shared transition protocol for activation,
creation, opening, movement and disposal. Guard overlapping commands, defer refresh,
flush pending text, capture geometry, stage destination editors, commit once and
reconcile only the committed active context. Preserve successful text saves when
later organizational work rolls back. Retained editors receive committed snapshots.

Done when fake-window tests prove flush/preparation/geometry/commit failures keep
the original desktop and pending text available, hidden state never changes on a
switch, callbacks are idempotent, and post-commit presentation failure is reported
and reconciled without unsafe compensating writes.

### T10: Add real note-window transition adapters

- [x] Complete T10 and its focused validation.

Depends on: T09. Trace: CTX-05, CTX-06, CTX-07, CTX-09; AC-01, AC-05, AC-16.

Implement prepare/flush/capture/dispose adapters in NoteWindow. Context disposal
bypasses the existing Hide Note persistence path and cancels completed autosave
scheduling. Explicit Hide still sets `is_open=False`. Prevent close callbacks from
writing removed notes; preserve coordinates when unsupported by the compositor.

Done when GTK tests with a display verify context disposal versus deliberate Hide,
failed flush retention, no late deleted-note writes and unchanged stored timestamps
for geometry-only transition saves. Record any compositor-only checks under T16.

### T11: Wire application lifecycle, tray and startup failures

- [x] Complete T11 and its focused validation.

Depends on: T09, T10. Trace: CTX-04, CTX-05, CTX-08, CTX-10, FLOW-01;
AC-02, AC-09; TC-CTX-010.

Wire stores/services/controller in app.py and route context-changing callbacks
through it. Restore only the active group's individually open notes on startup
and panel reopening; preserve context on shutdown. Use the active group for tray
creation. Present actionable migration/backup startup errors without opening an
empty replacement database. Keep diagnostics free of note contents/names/queries.

Done when application-level checks cover panel reopening, restart, tray-created
membership, no duplicate windows, shutdown persistence and visible startup failure.

### T12: Build profile selection and group sections in the panel

- [x] Complete T12 and its focused validation.

Depends on: T06, T11. Trace: UX-01, UX-02, UX-03, UX-04, UX-05, UX-06, UX-07;
AC-03, AC-04; TC-CTX-004, TC-CTX-012.

Add the title MenuButton/popover and ExpanderRow groups in one external scroller.
Show General first, note counts and explicit active/activation feedback. Keep
multiple independent expansions and stable focus/expansion across refreshes.
Preserve note previews/hidden styling and provide explicit Activate and open
outside the active context. Keep post-its free of organization decoration.

Done when widget tests distinguish browse/activate/open, preserve the desktop
while expanding/collapsing, handle empty/only-hidden groups and retain focus when
an editor refreshes the panel. Verify layout on the supported GTK/libadwaita target.

### T13: Add create/rename, move and deletion dialogs

- [x] Complete T13 and its focused validation.

Depends on: T08, T11, T12. Trace: FLOW-02, FLOW-03, DEL-01, DEL-04, DEL-05,
DEL-06, DEL-07, UX-07; AC-06, AC-07, AC-12, AC-13, AC-14, AC-15, AC-16, AC-17;
TC-CTX-006, TC-CTX-007, TC-CTX-008, TC-CTX-009, TC-CTX-012.

Build forms with inline validation and complete destination breadcrumbs. Use
Create and activate and the specified disposal choices/summary. Default to moving
notes and final Cancel; show explicit destructive wording for Delete all. Handle
replacement-profile selection, empty containers, protected actions, stale previews,
retry and cancellation focus. Wire final actions through the controller.

Done when widget tests verify action labels/defaults, eligible destinations,
counts including hidden notes, no writes on cancellation, context outcomes and
failure/retry behavior without closing unsaved editors.

### T14: Integrate scoped search and state restoration in the panel

- [x] Complete T14 and its focused validation.

Depends on: T07, T12, T13. Trace: FLOW-05, FLOW-06, FLOW-07, UX-04, UX-06,
UX-07; AC-08, AC-18; TC-CTX-011, TC-CTX-012.

Add Active group / Current profile / All profiles controls, matching sections
or flat global breadcrumbs, expansion snapshots and distinct no-results states.
Clear query/reset scope only after an actual committed context change. Keep
ordinary refresh/rename/browse/same-context operations stable. Retain Ctrl+F,
Escape, explicit external-result opening and keyboard focus.

Done when GTK/service regression tests cover all scopes, no implicit activation,
clear/restore behavior, failed switches retaining query/context, refresh while
typing, hidden results and global Activate and open.

### T15: Verify upgrade recovery and old-binary compatibility

- [x] Complete T15 and its focused validation.

Depends on: T05, T11. Trace: AC-10 and rollout/rollback requirements;
TC-CTX-001, TC-CTX-002, TC-CTX-003.

Execute maintained upgrade/failure cases, including process interruption inside
the transaction and a competing source write. Run an isolated snapshot-restore
drill with the pre-upgrade reader. Preserve the newer recovery set/sidecars and
demonstrate the documented loss boundary for post-snapshot changes. Confirm a
schema-4 reader refuses schema 5 without mutation.

Done when original/restored values and versions match, each failure produces
actionable output, no real user data was used, and the rollback procedure has
separate reproducible execution evidence.

### T16: Verify real desktop UX, accessibility and scale

- [ ] Complete T16 and its focused validation.

Depends on: T11, T12, T13, T14. Trace: AC-01, AC-02, AC-03, AC-04, AC-05,
AC-09, AC-11, AC-13, AC-14, AC-16, AC-18; UX-07 and quality attributes;
TC-CTX-004, TC-CTX-005, TC-CTX-007, TC-CTX-008, TC-CTX-010, TC-CTX-011, TC-CTX-012.

Run the maintained cases with real GTK windows on Wayland and X11 where available.
Check context cycling, pending-edit failure/retry, hidden notes, tray, restart,
deletion, search, keyboard/screen-reader state, long names, narrow layouts and
system themes. Record unsupported positioning as the existing compositor limit.
Measure normal startup with 100 short notes and search/context operations with
1,000 short notes, 30 groups and three profiles; report migration time separately.

Done when supported-session results, timings and concise screenshots/observations
are recorded. Mark unavailable sessions/tools as not run with a reason rather
than treating widget/fake-window tests as desktop evidence.

### T17: Update usage and recovery documentation

- [x] Complete T17 and its focused validation.

Depends on: T15, T16. Trace: UX/FLOW/DEL behavior and rollout/rollback requirements.

Document profile/group switching, General, create/move/delete choices, search
scopes, hidden-note semantics, initial migration and snapshot restore limits.
Update user-visible change notes in the development section appropriate to the
existing 0.8.0 preparation; do not promote or publish a release. Reconcile the
spec, plan, contract and ADR with the final implemented design and observed limits.

Done when documentation describes delivered behavior, local links resolve,
recovery steps match the drill and any intentional drift is explicitly resolved.

### T18: Complete regression and acceptance traceability

- [ ] Complete T18 and its focused validation.

Depends on: T01 through T17. Trace: all requirements and AC-01..18.

Run `/usr/bin/python3 -m unittest discover -s tests`,
`/usr/bin/python3 -m compileall pinleaf tests` and `git diff --check`.
Review migration-contract conformance and coverage below, distinguish GUI skips
from executed checks, and attach concise evidence to the feature review. Complete
tasks only where evidence exists; retain explicit follow-ups for unresolved checks.

Done when automated checks pass, acceptance coverage and desktop limitations
are recorded, and no untracked spec/code drift remains. Publication is outside
this task list and requires a separate user request.

## Acceptance Coverage

The test areas below now have implementation evidence linked from the execution
record. Maintained cases cover shared/high-impact risks;
simple deterministic domain assertions remain in their focused test modules.

| Acceptance example | Tasks | Planned verification |
| --- | --- | --- |
| AC-01 | T09, T10, T16 | Controller/window tests; TC-CTX-004 |
| AC-02 | T06, T11, T16 | Organization/lifecycle tests; TC-CTX-004 |
| AC-03 | T12, T16 | Panel activation tests; TC-CTX-012 |
| AC-04 | T09, T12, T16 | Controller/panel tests; TC-CTX-004 |
| AC-05 | T09, T10, T16 | Fault injection; TC-CTX-005 |
| AC-06 | T07, T13 | Service/controller/dialog tests; TC-CTX-006 |
| AC-07 | T07, T13 | Service/controller/dialog tests; TC-CTX-006 |
| AC-08 | T07, T14 | Scoped-search tests; TC-CTX-011 |
| AC-09 | T11, T16 | Lifecycle tests; TC-CTX-010 |
| AC-10 | T01, T05, T15 | Migration/backup tests; TC-CTX-001, TC-CTX-002, TC-CTX-003 |
| AC-11 | T02, T05, T06, T16 | Domain/store/locale tests and desktop label check |
| AC-12 | T02, T06, T13 | Name boundary/uniqueness and form-validation tests |
| AC-13 | T08, T13, T16 | Disposal/controller/dialog tests; TC-CTX-007 |
| AC-14 | T08, T13, T16 | Disposal/controller/dialog tests; TC-CTX-008 |
| AC-15 | T08, T13 | Protected-container service and action-state tests |
| AC-16 | T08, T09, T10, T13, T16 | Fault injection; TC-CTX-005, TC-CTX-007, TC-CTX-008 |
| AC-17 | T06, T09, T13 | Atomic-create/controller/dialog tests |
| AC-18 | T14, T16 | Search/reset and failure tests; TC-CTX-011 |

Implemented test areas: `test_organization.py`, `test_organization_service.py`,
`test_context_controller.py`, `test_migrations.py`, `test_backup.py` and
`test_organization_dialogs.py`, plus existing models/store/note-service/search/
main-window/note-window/tray tests. Final filenames may follow the implementation
split; behavior coverage and stable case/task identifiers must remain traceable.

## Progress

- Task decomposition and maintained verification definitions: prepared.
- T01..T15 and T17: complete with focused automated/native/drill evidence.
- T16: partial; automated/native X11, themes, narrow layouts and scale checks ran.
  Manual real X11 context/search/move/disposal flows, explicit hidden-note opening,
  shell indicator actions and restart restoration passed. Final automation also
  passes actual XTest keyboard, external AT-SPI names/states, visible save-error/
  retry, size restoration and profile disposal/transfer including hidden notes.
  Normal 75-open startup passes two seconds; 100-open stress peaks at 2001.47 ms.
  Wayland, human Orca speech/usability and the strict stress/private-bus diagnostic
  follow-ups remain; exact positioning retains its existing adapter limitation.
- T18: final automated regression complete (157 passed, zero skips); overall
  acceptance remains qualified by T16. Available local automation is concluded.
- Feature automation and migration recovery drill: executed; see the execution record.
- Documentation-only validation is recorded in [review.md](review.md#task-definition-validation).
