# Plan: General to Shared

Status: pre-approved by the maintainer on 2026-10-11, with tasks and full local
feature implementation authorized. Source: [spec](spec.md).

## Boundaries and Ownership

Keep SQLite, GTK 4/libadwaita, the existing autosave and the single transaction
owner. No dependency or network call is needed. The New menu and remote
integration remain outside this slice.

| Area | Change |
| --- | --- |
| models.py, organization.py | Shared identity, nullable ordinary context, localized labels and reserved names |
| storage/migrations.py | Atomic schema 1–5 to 6 upgrade, collision handling, context conversion and validation |
| storage/organization_store.py | Shared lookup, explicit profile context and nullable last-group recovery |
| storage/sqlite_store.py | Multi-group listing and persistent migration notice |
| services/note_service.py | Shared creation and current-context search |
| services/organization_service.py | Profile activation, Shared-aware open/move/delete and stale-preview protection |
| services/context_controller.py | Shared-plus-ordinary visibility and retained editor reuse |
| app.py | Shared creation callback and context-aware open |
| ui/main_window.py | Shared section and +, nullable title, search labels and migration notice |
| ui/organization_dialogs.py | Shared-aware opening and deletion summaries |
| tests/ | Schema-5 fixtures, migration/fault tests, context lifecycle and GTK regression checks |

## Schema 6

1. Rename groups.is_general to is_shared. Preserve every group ID, note row and
   membership. Replace the built-in partial index with idx_groups_shared.
2. Convert live profiles' captive names to Shared/shared. Before that update,
   rename conflicting ordinary Shared/Compartilhado names using the first free
   numeric suffix. Preserve their identities and note memberships. Leave deleted
   profiles' tombstoned group values intact.
3. Rebuild profile_context with nullable last_group_id and its existing composite
   ownership foreign key.
4. Rebuild active_context with profile_id NOT NULL and nullable group_id, a
   profile foreign key and composite group/profile foreign key. A null group is
   a valid state even when ordinary groups exist.
5. Add migration_notices(id PRIMARY KEY, payload NOT NULL) for a dismissible,
   persistent General-to-Shared notice and collision-renaming summaries. Keep
   existing app_settings values untouched. Fresh databases do not need a notice.

The [migration outcome contract](contracts/general-to-shared.json) is extended
with the exact target schema and invariants before implementation. No down
migration is supported. [ADR 001](adr-001-optional-context.md) records the
consequential context/storage decision.

## Migration and Recovery

- Validate recognized source versions and organization before changing data.
  Reject unknown/newer or malformed libraries without reseeding them.
- Use the existing private SQLite backup API and source-still-matches check.
- Run legacy 1–4 upgrades through the existing schema-5 step, then schema 6,
  within the same outer transaction. Schema 5 starts directly at the new step.
- Preserve an active ordinary group. Replace active/last General references
  with NULL while keeping the owning active profile. Repair removed/invalid
  ordinary references to NULL; never implicitly select another project.
- Compare all source note columns and existing settings before commit. Validate
  memberships, one live Shared per profile, nullable ordinary contexts, foreign
  keys and SQLite integrity, then update schema_version last.
- Startup at version 6 validates without snapshots or repeated conversion.
- Recovery drill: fail a disposable conversion at DDL, renaming and version
  writes; test rollback/interruption and snapshot restoration with the shipped
  schema-5 reader, preserving newer recovery files. Never open user note data.

## Domain and Service Flow

ActiveContext holds a Profile and Group | None. Group has is_shared. A context
identity is (profile_id, ordinary_group_id_or_none), so changing profiles while
both have no ordinary group still emits the context-change notification.

OrganizationStore owns set_context(profile_id, group_id_or_none), rejecting
Shared and foreign groups. activate(group_id) handles only ordinary groups;
profile activation resumes last_group or NULL. Recovery validates these states
and only writes metadata that actually changed.

NoteService creates in Shared explicitly, or in the active ordinary group with
Shared as the accepted default when absent. Current-context listing uses one
SQL IN query over Shared and the optional ordinary ID, retaining creation order.
Profile/global search retain existing normalization and hidden-note inclusion.

Opening a shared note resumes its profile only when needed; opening an ordinary
note activates its group. Delete active ordinary -> same profile / NULL. Delete
active profile -> ordinary destination, or Shared destination's owner and saved
ordinary context. Preserve stale-preview checks including nullable replacements.

## Editor Lifecycle

The controller flushes affected editors and captures their restorable state,
then applies domain changes inside the existing outer transaction. It obtains
desired windows from current-context notes filtered by is_open. Stage only new
editors before commit, dispose only removed IDs afterward, and retain the
intersection without presenting/refocusing it on a group switch. Explicit
Open/New actions retain their deliberate focus behavior. Failures preserve the
previous editors, context and pending text.

## GTK Presentation

Keep the current expander list. Shared appears first with count, explanatory
subtitle and an accessible +. It has no activation, rename or delete control.
Its rows open directly and offer the existing note actions. Ordinary sections
retain activation and management controls. With no ordinary context, the title
uses Shared notes only / Somente notas compartilhadas.

Rename the default scope to Current context / Contexto atual. Search results
in another profile's Shared offer Switch profile and open. Deletion summaries
explain NULL ordinary context or restoration of the destination profile's last
group. A wrapped, dismissible notice reports successful migration and any
renamings; text uses plain labels, never markup or note content.

## Verification and Delivery

Derive maintained cases in verification-cases.md and implement focused unit/integration
coverage for all AC-01..13. Run unittest, compileall and diff checks. Run GTK
checks in an isolated display/data/session where practical, using real editor
instances to verify shared identity, edits, profile switches and restart.
Capture panel/search/deletion screenshots and inspect normal/narrow layouts.
Benchmark representative context switches with 1,000 short notes; include
hidden notes and multiple profiles. Close every test app/helper/session afterward.

Update README, organization/recovery documentation, limitations and Unreleased
changelog to describe development behavior while preserving public 0.8.0 release
status. Record evidence and remaining platform qualification honestly. Commit,
push and prepare a reviewable feature PR; do not merge, tag or release this
larger package while its other workstreams remain undecided.
