# Plan: Profiles and note groups

Status: implemented locally against the [ordered task breakdown](tasks.md).
Product questions are resolved in [spec.md](spec.md#open-questions).
[Execution evidence](execution-2026-10-10.md) distinguishes automated/native
checks from remaining desktop qualification. No release or publication was made.

## Basis and Boundaries

- [Specification](spec.md): CTX-01..10, UX-01..07, FLOW-01..07 and DEL-01..07.
- [UX](ux.md): title selector, independent expansion/activation, movement,
  deletion choices and search scopes.
- [Migration contract](contracts/migration-v5.json): machine-readable version,
  preservation and lifecycle requirements for later implementation checks.
- [Proposed architecture decision](adr-001-context-storage-and-recovery.md):
  schema compatibility, removed-container retention and migration recovery.

Keep Python 3.11, GTK 4/libadwaita on Ubuntu 24.04, SQLite and local XDG data.
No additional runtime dependency, remote service or application data location.
The initial profile is Personal/Pessoal and all existing notes join its General.
Container deletion is included; a restore UI, hard purge, group relocation and
bulk operations unrelated to deletion remain out of scope.

## Current Constraints

The inspected database schema is version 4. Notes and global text defaults
exist, but organization and active context do not. `NoteStore` owns one SQLite
connection and its write methods currently commit independently.

`app.py` owns the window registry and restores every individually open note.
`NoteWindow._on_close_request()` calls `close_note()`, which sets `is_open=False`.
Using that path for a context switch would incorrectly hide notes permanently.
Autosave already retains pending text after a failed flush, but the current
close handler ignores that return value. New transitions must check it before
changing context or disposing any editor.

The main panel currently rebuilds a flat list on refresh. Rebuilding expandable
groups without stable state would lose expansion and keyboard focus whenever
an editor triggers a refresh.

## Ownership and Modules

| Area | Planned responsibility |
| --- | --- |
| `pinleaf/models.py` | Profile, Group, ActiveContext, search-scope enum and required note membership |
| `pinleaf/organization.py` (new) | Name validation/keys and localized built-in labels; no GTK or SQL |
| `pinleaf/storage/migrations.py` | Version-5 upgrade, fresh bootstrap and invariant validation |
| `pinleaf/storage/backup.py` (new) | Private, validated pre-upgrade SQLite snapshots |
| `pinleaf/storage/sqlite_store.py` | Connection/transaction ownership and membership-aware note queries |
| `pinleaf/storage/organization_store.py` (new) | Organization/context SQL on that same connection |
| `pinleaf/services/organization_service.py` (new) | Create, rename, activate, move and deletion rules/previews |
| `pinleaf/services/note_service.py` | Active-group note creation and scoped normalized text search |
| `pinleaf/services/context_controller.py` (new) | Transition orchestration through testable window interfaces, without GTK imports |
| `pinleaf/app.py` | Wire services/controller and adapt real window registry/tray callbacks |
| `pinleaf/ui/main_window.py` | Profile selector, group sections, search state and panel actions |
| `pinleaf/ui/organization_dialogs.py` (new) | Create/rename, move and container-disposal forms |
| `pinleaf/ui/note_window.py` | Flush/snapshot and disposal that preserves individual open state |
| `pinleaf/resources/styles.css` | Panel spacing/state styling without adding organization badges to post-its |

Keep SQL in stores, validation in domain/services and GTK presentation in UI.
The controller owns the order of save, commit and window reconciliation. GTK
callbacks never update active context or note membership directly.

## Data Model: Schema 5

Use stable UUID strings for new profiles/groups, matching note identity style.
Add `group_id TEXT NOT NULL` to every note, with a foreign key to `groups.id`.
Rebuild the notes table transactionally rather than introduce nullable or
default-sentinel membership. Copy original columns explicitly and retain the
existing deleted/updated index.

| Table | Fields and constraints |
| --- | --- |
| `profiles` | `id`, `name`, `name_key`, nullable `deleted_at`; primary key on id, unique live name key |
| `groups` | `id`, `profile_id`, `name`, `name_key`, `is_general`, nullable `deleted_at`; profile FK, unique `(id, profile_id)` |
| `profile_context` | `profile_id` primary key, `last_group_id`; composite FK ensures that the group belongs to the profile |
| `active_context` | singleton integer key constrained to 1, `group_id` FK; derive the active profile through the group |
| `notes` | All existing fields unchanged, plus required `group_id` FK |

Use partial unique indexes for live profile names, live group names within a
profile, and one live General per profile. Index live notes by
`(group_id, created_at DESC, id DESC)` and live groups by profile. Use restrictive
foreign keys, not physical cascading deletion. Enable foreign keys before
opening a transaction.

Exactly one live General per live profile, one active-context row, one
last-group row per live profile, and live references are checked by service
transactions and migration validation. Foreign keys prevent missing identities;
they alone do not prevent references to tombstones.

Removed profiles/groups use `deleted_at` tombstones. This preserves valid
membership for retained soft-deleted notes without silently introducing a data
purge. Every ordinary query excludes removed groups and profiles as well as
deleted notes. Live names may be reused after removal. Context rows for removed
profiles are removed, and remaining last-group references are repaired in the
same transaction. No recovery interface is added.

General's identity is `is_general`, never its displayed name. Store its canonical
name/key as General/general and derive General/Geral for display. For initial
Personal/Pessoal, choose the localized initial name once and store it as an
ordinary renameable profile name. Changing locale does not rewrite profile
names, memberships or identities. This requires only built-in label selection,
not translation of the entire application.

For user names, trim outer whitespace and retain the resulting spelling.
Generate uniqueness keys with NFC normalization and Unicode case folding;
normalize again after folding. Reject blank or over-80-code-point names before
SQL. Reserve General/Geral in group names independently of current locale.
Database uniqueness handles a race after UI validation.

## Transaction and Service Contracts

`NoteStore` remains the connection owner. Add an explicit transaction context;
internal writes must not commit an enclosing transaction. `OrganizationStore`
shares that connection rather than opening another one. Composite operations
use one explicit write transaction and roll back on error. Existing standalone
note operations keep their durable-save behavior.

The service operations exposed to the controller are:

| Operation | Durable effect |
| --- | --- |
| Create profile/group and activate | Create identities and General as needed; update active/last context together |
| Rename profile/group | Validate live uniqueness; retain identities, membership and context |
| Activate group/profile | Validate live destination; update singleton and last-used context |
| Activate and open note | Set that note open and update context in the same transaction |
| Move note | Change membership only; preserve content, timestamps, appearance and open/hidden state |
| Preview container deletion | Return affected identities, visible note count, all source groups, valid destinations and resulting context |
| Delete container | Revalidate preview; move or soft-delete notes, tombstone containers, repair context together |

New notes require an actual active group at creation; do not add an optional
membership fallback that could persist orphaned notes. Pass the required group
to `Note.new()` and insert it with the note's existing default appearance.
Keep clock/ID factories injectable. Organizational changes do not count as
note-text edits and do not rewrite note timestamps; newly deleted live notes
receive the existing deletion/update timestamps, while earlier deletion times
remain intact.

Use typed validation, protected-container, stale-preview and storage errors.
Return committed context/effects to the controller instead of requesting
window side effects from inside SQL. Re-activating the current context is a
no-op and does not clear search unnecessarily.

## Desktop Transition Protocol

Use the same controller path for group/profile activation, Create and activate,
Activate and open, note movement, and container deletion. A window interface
exposes flush, capture state, show for context, present and dispose; tests can provide
fakes without importing GTK.

1. Guard against overlapping commands and defer ordinary panel refresh callbacks.
   Determine affected windows and the prospective destination context.
2. Flush pending text in outgoing/affected editors. A false return or exception
   stops the transition with all original windows and context intact. Successful
   text saves may remain saved if a later step fails; organizational changes
   have not yet occurred.
3. Capture restorable geometry without changing `is_open`.
4. In one transaction revalidate identities/preview, save captured geometry,
   perform the operation and persist resulting context. Prepare required editors
   against the uncommitted membership, without presenting them or calling
   `reopen_note()`, then commit. Preparation or commit failure rolls back SQL and
   discards staged editors without closing the original ones. This implementation
   refinement lets Create and activate use its new identities directly. Native
   construction remains inside the write lock; no main-loop iteration occurs there.
5. After commit, reconcile the registry with non-deleted, individually open notes
   in the committed active group. Dispose outgoing editors through a dedicated
   path that cancels completed autosave scheduling and bypasses user Hide Note
   persistence. Update retained editors' immutable note snapshots from committed
   data. Map staged editors and request focus for the last one, refresh once,
   and release the guard. A single explicit open still presents that note;
   batches avoid one compositor focus request per restored window.

Add a geometry-only persistence operation for these transitions; it changes
neither individual open state nor note timestamps. A save failure is subject
to the same rollback/retained-window rule as other transaction failures.

Moved notes entering the active group are displayed only if already open.
Removed notes never run a later close callback that rewrites deleted storage.
Explicit Hide Note remains a separate operation that sets `is_open=False`.
Programmatic callbacks must be idempotent and must not trigger a second switch.

Startup and panel reopening restore only the saved active group's open notes,
without reopening writes that alter timestamps. Shutdown saves current editors
without resetting context. Preserve existing unsupported-position behavior on
Wayland: retain saved coordinates when capture/restore is unavailable, as
specified in [spec 005](../005-note-window-position/spec.md).

SQLite commit is the durable boundary; the compositor cannot provide a single
atomic presentation of several native windows. Stage all required editors before
that boundary. An unexpected presentation error after commit is reported and
reconciled from committed state; do not attempt an unsafe compensating deletion
or claim unsaved edits were rolled back. Verify ordinary save/preparation/commit
failures separately from process termination.

## Container Deletion

The preview uses stable source identities, source group IDs and note IDs/states,
not note contents. Count non-deleted notes including hidden ones; retain the
complete membership set for transfer. Revalidate inside the final transaction
so a changed library cannot silently expand the confirmed destructive scope.
Source renaming, changed membership/count or an invalid destination requires
a refreshed review. Autosaved text alone does not invalidate the preview.

- Transfer changes membership of every retained note, including already-deleted
  notes, to one live destination outside the source subtree. It never revives a
  note and never duplicates the source groups.
- Delete all marks only currently live notes deleted using existing semantics;
  retained notes remain linked to tombstoned source groups.
- A container with no non-deleted notes uses simple removal without a transfer
  destination; retained deleted notes remain linked to its tombstones.
- General cannot be independently removed. The last live profile cannot be
  removed. Validate both rules in the service as well as the panel.
- Removing the active group selects its profile's General. Removing the active
  profile selects the transfer destination, or the explicitly chosen remaining
  profile's last valid group for Delete all. An empty active profile uses that
  same explicit replacement-profile choice without a note destination.
- Removing an inactive container retains active context. Reconcile moved-open
  notes if they enter the current group. Repair every affected last-group
  reference before commit.

Use the form/summary described in [UX](ux.md#excluir-um-grupo-ou-perfil). The
move choice is initially selected, Cancel is the default final response, and
Delete all uses an explicit destructive final label. Destination and replacement
controls offer live eligible entities only; authoritative validation is in the
service. No typed-name challenge or extra confirmation layer is needed.

## Main Panel and Search

Use `Adw.HeaderBar.set_title_widget()` with a `Gtk.MenuButton`/`Gtk.Popover`
showing the active profile and group subtitle. Profile creation/management is
secondary content. Keep the system window title identifying Pinleaf.

Replace the flat normal-list renderer with `Adw.ExpanderRow` sections in one
external scroller. General sorts first, then normalized alphabetical group
names; count all non-deleted notes. An Activate suffix action does not toggle
expansion. The active group expands on activation; any group may later collapse.
Keep expansion by stable group ID and focus by control/note identity across
refreshes. Row actions offer the existing note controls plus Move; inactive
notes use the explicit Activate and open action.

Store query, scope, expansion snapshot and focus in the panel, not the database.
Add `SearchScope.ACTIVE_GROUP`, `CURRENT_PROFILE` and `ALL_PROFILES` to the
service list operation. Apply SQL membership/lifecycle filtering first, then
reuse spec 010's Python Unicode/literal full-text matching and creation order.
All-profiles results carry profile/group labels; no FTS dependency or SQL LIKE
substitution is introduced.

Empty query shows normal sections for the active profile. Current-profile
search temporarily expands matching sections; global search uses a flat result
list with breadcrumbs. Clear restores the previous expansion state. A successful
actual context change clears query, resets scope and expands the active group;
rename, browse and same-context operations do not. Ctrl+F/Escape remain available.
No-results state must remain distinct from an empty active group.

Use native GTK/libadwaita controls available on the supported target, with
inline form validation, accessible hidden/active/expanded state and focus
restoration. Validate long names, narrow windows, keyboard navigation and screen
reader output during implementation. The existing HTML preview illustrates
navigation; deletion has a textual UX contract and still needs actual GTK QA.

## Migration, Backup and Compatibility

Refactor migration orchestration before adding schema 5: known upgrades run
inside one explicit transaction without nested commits. Do not use
`executescript()` inside that transaction because Python 3.11 can commit a pending
transaction before running it. Execute ordered statements with bound values.
The standard library documents [transaction control](https://docs.python.org/3.11/library/sqlite3.html#transaction-control).

For an existing version-1..4 database:

1. Read and validate the version/schema before any schema write. Refuse newer,
   malformed or nonempty unversioned databases without guessing or overwriting.
2. Use SQLite's [backup API](https://docs.python.org/3.11/library/sqlite3.html#sqlite3.Connection.backup)
   to create a snapshot under the existing private XDG data directory's
   `backups/`. Use a unique schema-version/UTC/random filename, directory mode
   0700 and file mode 0600. Validate its integrity and source version before
   proceeding. Failure to create/validate a backup aborts the upgrade.
3. Acquire the write transaction and verify that source schema, notes and
   settings still match the snapshot. If another writer changed them between
   backup and lock acquisition, abort and retry from a fresh snapshot. Do not
   migrate with a stale recovery point.
4. Apply earlier supported upgrades without intermediate commits. Create the
   initial profile, General and context, rebuild notes with membership, and
   recreate the required indexes. Copy all original note values, including
   soft-deleted rows and nullable appearance fields, without calling normal
   update methods or changing timestamps.
5. Check original row/value preservation, all membership/context invariants,
   `PRAGMA foreign_key_check` and integrity. Update the single schema-version
   row to 5 only after those checks; commit once. Any failure rolls back the
   complete upgrade, closes startup storage and shows an actionable error.

The current startup path only prints an error and quits. Wire an application
startup-error presentation for migration/backup failures before exiting; never
open an empty replacement library after a failed upgrade.

A fresh database bootstraps schema 5 and the same initial context atomically,
without a needless empty backup. An already-version-5 database performs no
upgrade or reseeding. Validate active/last context on startup. An invalid group
in a live profile falls back to its General. If no active profile can be
recovered, choose the first live profile by stable ID and activate its General.
Report this metadata recovery locally without note contents. Repair invalid
last-group references to the owning profile's General. Broken memberships,
missing General groups or no live profiles fail integrity validation rather
than silently losing notes. A removed initial profile is never recreated.

Use the supported [table-rebuild approach](https://www.sqlite.org/lang_altertable.html)
with explicit column mapping and index recreation. SQLite
[foreign-key enforcement](https://www.sqlite.org/foreignkeys.html) supports
referential checks; live-container rules remain transaction invariants.

Older Pinleaf binaries supporting schema 4 must refuse schema 5. Do not advertise
backward-read compatibility or add a speculative down-migration. To roll back,
stop Pinleaf, preserve the current database and its SQLite sidecars as a separate
recovery set, restore the validated pre-upgrade snapshot to the configured path,
and run the corresponding older binary. Work after that snapshot is absent
from the restored library; keep the newer recovery set for later recovery.
Document and test this procedure before implementation is considered complete.
Backups are local note data; do not automatically prune or upload them.

## Security, Diagnostics and Performance

Use bound SQL parameters and the existing private data-directory policy.
Profiles provide organization, without identity or access-control promises.
Diagnostic errors identify operation and failure type, without note contents,
user-entered names or search queries. Show user-facing errors in the existing
GTK error flow with retry/cancel access and retain editor buffers on failure.

Avoid windows for inactive/hidden notes and avoid querying storage once per
group: load the profile's groups/counts and scoped notes in bounded queries.
Benchmark startup with 100 short notes against the existing two-second target;
record search/context timings with 1,000 synthetic short notes across 30 groups
and three profiles. Keep normalized search linear until measurements justify a
separate indexing proposal. Backup and migration occur only during upgrades;
their duration is reported separately from normal startup measurements.

## Verification and Delivery Slices

These slices summarize the [ordered tasks](tasks.md). Each task contains its
dependencies, behavior traceability and focused validation:

| Slice | Evidence required |
| --- | --- |
| Domain/storage and migration | Names/protection rules, every supported schema upgrade, full note preservation and forced rollback/backup failures |
| Organization/controller lifecycle | Fake-window save/prepare/commit failures, active/last context, create/move/delete effects and unchanged hidden state |
| GTK organization/navigation | Profile selector, independent expand/activate, dialogs, preview revalidation, focus and scoped search |
| End-to-end verification/docs | Real restart/tray/panel reopening, Wayland/X11 checks, locale labels, rollback drill and performance observations |

The [acceptance coverage](tasks.md#acceptance-coverage) maps AC-01..18 to planned
storage/service/controller/widget tests. [Maintained cases](verification.md)
define migration/rollback, failed transitions, destructive container deletion
and desktop/accessibility checks using the playbook's Test Case Standards
(source path in the [review record](review.md#workflow)).
Keep execution results separate from reusable case definitions. GUI tests skip
explicitly on a headless environment; real desktop evidence is still required.

Before completing implementation run the repository's unittest suite,
`compileall pinleaf tests` and `git diff --check`. Test only isolated temporary
databases, including source-schema copies, and synthetic notes. Desktop checks
also use an isolated app/session bus or dedicated test desktop to avoid routing
actions to a running user instance. Do not migrate the developer's real note
library during QA.

Implementation uses a short-lived branch while keeping `main`
releasable. Usage/changelog describe delivered behavior; existing 0.8.0
preparation does not authorize a release, tag, push, PPA upload or publication.

## Alternatives and Readiness

- Tags and extra hierarchy add note decoration or nesting outside the agreed UX.
- Activating on expansion couples browsing to desktop changes; use explicit activation.
- Nullable membership or JSON settings alone weaken required membership/context
  validation; use typed organization tables and checked transactions.
- Hiding notes through the current close handler loses their stored open state;
  use dedicated context disposal.
- Physical cascading deletion would change existing data-retention semantics;
  use tombstones and the explicit disposal choice.
- Adding FTS or a new UI library is unnecessary for the specified scale/target.

No material product question remains. The accompanying ADR records the adopted
schema and recovery contract. Implementation and automated checks are local;
see [execution evidence](execution-2026-10-10.md) for native X11 observations,
the snapshot restore drill, timings and remaining qualification.
