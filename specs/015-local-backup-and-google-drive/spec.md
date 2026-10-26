# Feature: Local backup and restore, with Google Drive as a backup destination

Status: local slice A implemented on 2026-10-11; qualification is recorded in
[execution](execution.md). Google Drive slice B remains pending. Version change
and remote publication remain deferred.
Source: [package workstream 3](../012-shared-notes-and-remote-backup/spec.md).
Decision record and quality check: [review.md](review.md).
Machine-readable behavior contract: [backup-outcomes.json](contracts/backup-outcomes.json).

## Intent

Let the maintainer recover a lost computer or carry the complete Pinleaf library
to another computer, while continuing to create and use notes locally and
offline. Begin with a reliable local backup/restore workflow, then let Google
Drive store and retrieve the same portable backups.

The first beneficiary is the maintainer using their own Google account. This
iteration does not introduce an operated Pinleaf account or storage service.

## Scope and delivery slices

| Slice | User outcome | Dependency |
| --- | --- | --- |
| A: Local | Create a backup file and restore it on this or another computer without internet | Implement and verify the format and recovery design in the technical plan |
| B: Google Drive | Connect a Google account, save a backup and restore a selected remote copy | Slice A verified; OAuth application configured; Drive qualification on two isolated installations |

Both slices belong to this specification and the larger development package.
Implement and verify A before adding application networking in B. The local
slice must not require Drive libraries, credentials or account setup to run.

Out of scope: automatic/scheduled uploads, bidirectional synchronization,
merging concurrent edits, selecting individual notes/profiles for export,
continuous remote database access, S3, a Pinleaf backend/account, collaboration,
cloud deletion management and automatic retention/pruning. Selective/merge
restore is deferred, not silently added to the implementation.

## Agreed direction and design defaults

Confirmed by the maintainer:
- Local/offline use remains complete and independent of cloud availability.
- Start with local backup and restore; Google Drive is the first integration.
- Use the user's Google account rather than operate a Pinleaf storage service.
- Password protection is optional for local and Drive backups, so forgotten
  passwords do not become a prerequisite for recovering every backup.
- Back up the whole library and restore by replacement, with a validated local
  recovery copy of the current library. The maintainer accepted this recommendation
  and requested advancing the workflow on 2026-10-11.
- Keep version 0.8.0 and delivery local until the larger package is ready.

Design defaults used by the plan:
- Leave Protect with password off for each new backup. When deliberately
  enabled, restoring that copy requires its password; Pinleaf cannot recover it.
- Store separate dated copies in a visible Pinleaf / Backups folder on Drive;
  never overwrite one shared "latest database" file.
- Use deliberate Save/Restore actions, with no unattended transfer or startup
  polling in this iteration. A cloud backup is not described as synchronization.

Q1 (whole-library replacement) and Q2 (optional password protection) are resolved.
No material product clarification remains before planning or task breakdown.

## UX

Add **Backup & Restore…** to the panel's main menu, opening a dedicated window
with two sections. Keep the note list and New menu focused on notes and groups.
Labels below describe the intended actions; use the project's localization
conventions when implementing them.

**Local backups** offers Create Backup… and Restore Backup…. Creation uses a
native Save dialog, proposes a filename containing a timestamp and unique backup
identifier, and shows the captured time and saved location on success. Restore
uses a native Open dialog, validates the file, then shows a preview before a
separate final Restore action. Opening a chooser or preview changes nothing.

For both local creation and Save Backup to Drive, offer an initially unchecked
**Protect with password** option. Show password and confirmation fields only
when enabled. Empty or mismatched passwords are validation errors while enabled;
they never silently select unprotected output. A new backup starts unchecked
even if the previous copy used a password; no persistent protection/password
preference is introduced. Explain inline that an unprotected file can be read by
anyone with access to it, and that a protected copy cannot be restored if its
password is forgotten. Do not add another confirmation dialog for this choice.

The preview shows backup date, source application version, live profile/group/
note counts, hidden-note count and the replacement effect from Q1. It identifies
where the current library's recovery copy will be kept. For a protected backup,
request the password before reading or displaying its private contents. Do not
show note contents in a preview.

**Google Drive** offers Connect Google Drive, then shows the connected account,
Save Backup to Drive, Refresh Drive Copies and Disconnect. The inline restore
selector lists dated copies newest first, with Preview & Restore per copy;
selection leads through the same validation, preview and confirmation as a
local file. Cancel Preview discards a selection. A downloaded backup can also
be restored through the local flow.

Local and remote status are distinct: never backed up, in progress, successful
at a captured time, or failed/cancelled. A successful upload describes a copy
captured at that time; it does not say all subsequent edits are synchronized.
Failure leaves the last successful timestamp intact and offers a deliberate
retry. A local file's existence and a cloud copy's existence are separate facts.

## Behavior

### Local authority and backup creation

- **BK-01:** Starting Pinleaf and creating, editing, hiding, organizing and
  searching notes require neither network access nor a Google account. No
  network request occurs before a deliberate connection or Drive operation.
- **BK-02:** Every backup contains the whole
  library, independently of active profile, group, search or desktop visibility.
  Preserve stable IDs, memberships, text, appearance, timestamps, open/hidden
  state, retained soft-deleted records, active profile, optional ordinary group,
  each profile's last group and portable default text preferences. Deleted
  records remain deleted; a backup is not an undelete operation.
- **BK-03:** Exclude Google tokens, passwords, keyring contents, OAuth session
  state, device/account configuration, local backup history/paths, older backup
  files, logs, caches, executable code, installed fonts and migration notices.
  Restore does not copy another computer's identity or account connection.
- **BK-04:** Capture a consistent point-in-time library after saving pending
  editor text and current supported geometry. If any pending save fails, abort
  creation and retain its unsaved editor. Later edits during encoding/upload
  belong to a later backup and must not be lost or silently claimed as included.
- **BK-05:** Create one self-contained, versioned portable file with a generic
  filename. It must restore without access to the source computer, original
  path, account or an older backup. Explicit confirmation is required before
  replacing an existing user-selected destination file. Publish success only
  after a complete validated file is durable; failure/cancellation preserves
  any previous destination and does not leave a file presented as usable.
- **BK-06:** Backing up is read-only with respect to note identity, content,
  organization and timestamps, apart from saving genuine pending user changes
  and supported current geometry. It never changes the active context or
  opens hidden notes. An empty live library is a valid backup.

### Validation, replacement and recovery

- **RS-01:** Treat an input file as untrusted. Before final confirmation, validate
  its format/version, completeness, integrity, data types and library invariants
  including unique IDs, references, one Shared per live profile and valid
  nullable context. Bound work and extraction; reject malformed, oversized or
  unexpected contents without executing embedded SQL/code or writing outside
  private staging. Numeric limits belong to the format/technical plan.
- **RS-02:** Restore supported older backup/library versions by upgrading only
  a staged copy with existing supported migration rules. Reject newer or
  unsupported versions with an actionable explanation, leaving source and
  current library intact. The first portable format supports libraries produced
  by its own delivery; raw pre-upgrade SQLite snapshots are not portable input.
- **RS-03:** Final Restore replaces the entire
  current library, with no merge, duplication or per-profile selection. Before
  replacement of a readable current library, save pending edits and create and
  validate a private, independently recoverable local copy. If either step
  fails, replacement must not start. Recheck the current library at confirmation
  so edits made after preview are included in that recovery copy.
- **RS-04:** Coordinate replacement with every editor, autosave callback, store
  connection and tray/context action. No callback from the old library may write
  into the restored library. A failed/cancelled restore leaves the current
  library usable. After process interruption, startup must select a complete
  validated old or new library, retain recovery artifacts and report recovery;
  a mixture of the two is never accepted.
- **RS-05:** On success, reload the restored library's context and recreate only
  its eligible open Shared and ordinary-group notes, as defined by spec 013.
  Hidden notes stay hidden/struck, deleted records stay excluded, IDs/timestamps
  remain preserved and repeated restoration introduces no duplicate records.
  Recovery copies are retained until the user deliberately removes them.
- **RS-06:** Preserve stored appearance and geometry in the backup. Missing
  fonts use the existing fallback; geometry application respects current
  GTK/compositor support and must not block restoring notes on another display.
  Do not promise absolute Wayland positioning or install fonts from a backup.
  Private pre-restore recovery copies are protected like the local database;
  they are not automatically exported or uploaded.
- **RS-07:** Local Restore remains available from a storage-startup error. If
  the existing library cannot be opened/validated, explain that condition and
  preserve the closed database and any journal/WAL/SHM recovery files as private,
  byte-verified recovery artifacts before replacing them. Do not require that a
  corrupted source pass a logical snapshot check; do require successful
  preservation and a fully validated selected backup. Never silently delete or
  repair the original corrupt files as part of restoring.

### Google Drive destination

- **GD-01:** Support one connected Google account per installation. Connect via
  the system browser, with consent scoped to Pinleaf-created/explicitly selected
  backup files, not the entire Drive. The maintainer configures the OAuth
  application once; end users are not required to create a Google Cloud project,
  supply AWS credentials or run a backend. Cancelling consent changes no notes
  and stores no usable connection.
- **GD-02:** Save exactly the portable backup format from slice A, under the same
  protection policy. Each deliberate save creates a distinct backup identifier
  and file. Uploads from computer B never overwrite computer A's copy. Do not
  publish success or a restorable history entry for incomplete transfers.
- **GD-03:** Discover previously completed backups from Drive using the same
  account/application on a second installation, without relying on the first
  computer's local history or folder ID. Handle pagination and duplicate folder
  names without choosing an unrelated folder by its name alone. Verify downloaded
  bytes through the same local reader before offering final Restore.
- **GD-04:** Internet loss, timeout, quota exhaustion, access denial, missing
  files and expired/revoked authorization leave local notes and earlier backups
  usable. Explain Retry, Reconnect or Select another backup as appropriate;
  retry begins only on deliberate action. Never restore automatically when
  connecting, starting the app or noticing another computer's backup.
- **GD-05:** Disconnect forgets this installation's stored connection and stops
  its pending remote work without deleting local notes or remote backups.
  Explain that Google-side revocation is managed through the Google account;
  do not silently revoke another installation's access or switch its account.
- **GD-06:** No automatic pruning, shared latest pointer, remote deletion UI,
  background synchronization or conflict resolution is introduced. Users may
  manage the visible files in Drive themselves. Remotely removed or corrupted
  files are not offered as successfully validated backups merely because a
  local status record remembers them.

### Protection and interaction

- **PR-01:** Support both unprotected and password-protected portable files,
  locally and on Drive. Protection is optional and initially off per new backup;
  creating/restoring an unprotected file never requires a password. Validate
  integrity in both modes, without describing an unprotected file as confidential
  or authenticated against deliberate changes. When enabled, encrypt and
  authenticate private contents before export/upload, rejecting wrong passwords
  or tampering before revealing private metadata or replacing data. Never
  silently downgrade a protected operation or provide a password recovery
  fallback. Exact standard format, algorithms and password derivation belong to
  the plan and ADR; do not invent cryptography in application code.
- **PR-02:** Ask for a new backup's password and confirmation only when protection
  is enabled. Restore detects protection from the selected file and asks for a
  password only for a protected copy, regardless of the last creation choice.
  No remembered-password option is in this iteration. Never include passwords
  or Google tokens in backups,
  SQLite app settings, logs, filenames or diagnostic messages. Store persistent
  Google authorization only through an OS credential facility; if unavailable,
  offer session-only authorization rather than a silent plaintext fallback.
- **UX-01:** Actions, selectors, password inputs, status and final confirmation
  are keyboard accessible and named for assistive technology. Escape cancels
  noncommitted dialogs and returns focus. Label replacement explicitly; an
  ordinary default Enter must not unexpectedly confirm destruction.
- **UX-02:** Keep the interface responsive during file/crypto/network work;
  show progress and permit cancellation before the replacement commit boundary.
  Briefly block library-changing actions only while capturing or committing a
  coordinated state. Serialize backup/restore operations and explain busy state.
  After commit begins, report its outcome rather than claiming it was cancelled.

## Acceptance examples

The synthetic library fixture used below has Pessoal and Trabalho, Shared in
each, an ordinary Kubernetes group, three live notes (Shared open, Kubernetes
open, Kubernetes hidden), one soft-deleted note, portable text defaults and
Pessoal / Kubernetes active. No personal data or credentials are test fixtures.

| ID | Given / When | Then |
| --- | --- | --- |
| AC-01 | Offline, with no Google connection, create a local backup and restore it into a separate empty installation | The complete fixture round-trips with exact IDs, content, timestamps, memberships, preferences and context; hidden/deleted states are preserved |
| AC-02 | A text edit is pending when Create Backup runs, then another edit is made after capture | The first edit is in the backup; the later edit remains local; backup status names its capture time |
| AC-03 | A pending edit cannot be saved, or export runs out of space/is cancelled | No successful backup is reported, an existing destination remains intact and the current editor/data remain available |
| AC-04 | Preview a valid backup over a different current library, then cancel | No library, context, credentials or note window is replaced |
| AC-05 | Confirm restoring that backup after a new current edit was made following preview | The pre-restore recovery copy includes the new edit; the selected library replaces the old one; restoring the recovery copy recovers the old library |
| AC-06 | Recovery-copy creation, replacement or staged migration fails; also interrupt the process at every commit/recovery boundary | Current data remains recoverable, startup selects a complete library and old autosave/tray callbacks cannot modify restored data |
| AC-07 | Select truncated, malformed, inconsistent, newer, path-traversal or resource-limit-exceeding input | Reject it before replacement; keep current/source data intact and explain the relevant failure |
| AC-08 | Enable protection and create a backup, inspect its bytes, try a wrong password/tampering, then restore with the correct password | Private content is not plaintext; invalid authentication writes no library data and cannot fall back to unprotected reading; correct password restores the fixture |
| AC-09 | Restore twice on a different display without the requested font | No duplicate or revived note appears; eligible windows follow restored context and supported placement; existing font fallback works |
| AC-10 | Create a backup with no live notes, only the initial profile and Shared | Restore succeeds with zero notes, Shared-only context and no accidental ordinary group |
| AC-11 | Connect Google Drive, cancel once, then consent and save twice | Cancellation leaves data/connection unchanged; consent enables two distinct complete copies; no full-Drive permission is requested |
| AC-12 | On an isolated second installation, connect the same account with no local history and select a backup from the first | Discover and download it, preview it and restore through the same local path; credentials/device settings from the first are absent |
| AC-13 | Disconnect the network during upload, exhaust quota, revoke access or delete a listed file externally | No partial copy is reported as successful; local editing and earlier backups remain usable; Retry/Reconnect/refresh is actionable |
| AC-14 | Disconnect on one installation, then restart both without selecting a Drive action | Notes and cloud files remain; the other connection is not deliberately revoked; no background transfer or automatic restore occurs |
| AC-15 | Use only keyboard navigation in normal/narrow/light/dark layouts with delayed file/network operations | Actions and progress remain reachable; precommit cancellation returns focus and writes no replacement; final destruction requires explicit selection |
| AC-16 | Pinleaf cannot initialize a damaged disposable library; select a valid local backup from the startup error | Preserve and verify the original database/recovery files, validate the backup and explicitly restore a usable library; failed preservation prevents replacement |
| AC-17 | Create a local/Drive backup with the initially unchecked protection option, then try empty/mismatched passwords when enabled and finally create a protected copy | Unprotected copies round-trip without any password; invalid password input creates no copy; protection is recorded per file and starts off again for the next backup; restore prompts only for protected files |

## Data, contracts and architecture handoff

Inputs: a consistent local library, a selected portable file, a transient backup
password only when protection is selected, and explicit Google authorization
for slice B.
Outputs: a self-contained portable file, a dated Drive copy, or a validated
replacement library plus the private pre-restore recovery copy.

The [behavior contract](contracts/backup-outcomes.json) fixes included/excluded
data and agreed safety outcomes. The [plan](plan.md) defines the portable format,
reader limits, compatibility matrix and replacement/recovery procedure, with
machine-readable [payload](contracts/backup-payload.schema.json) and
[envelope](contracts/backup-envelope.schema.json) schemas and [examples](contracts/examples/README.md).
Backup format version remains separate from application and library schema versions.

Consequential decisions are recorded in [ADR 001](adr-001-portable-backup-and-recovery.md)
and [ADR 002](adr-002-google-drive-destination.md). Existing SQLite migration
snapshots remain useful prior art. Device/account configuration and operation
status are local state outside the portable payload, not new note settings.

## Quality, verification and operations

Privacy: Google receives only deliberately uploaded backups and the metadata
needed to store them. Generic filenames reveal no note/profile/group titles.
Unprotected backups contain readable library data; Drive account access control
does not make the portable file password-protected. Describe the selected mode
honestly without making protection a prerequisite for local or remote backup.
No telemetry, note text, passwords or tokens in diagnostics. Plaintext staging
and recovery artifacts remain private like the database and are cleaned up or
retained only according to their documented recovery role.

Reliability: automate round-trip comparisons across all preserved fields,
failure injection, process-interruption recovery and stale-editor protection.
Exercise both a small fixture and 1,000-note multi-profile library. Use controlled
slow storage/network work to verify responsiveness; measure results rather than
claim untested timings. Delivered local and Drive slices are recorded in
[local execution](execution.md) and [Drive execution](execution-drive.md).

Verification design: [maintained cases](verification.md). Use disposable data and
mocked Drive for repeatable tests. Qualify real OAuth/Drive discovery and restore
on two isolated installations with the maintainer's explicitly designated test
account/folder; never replace the daily-use library for qualification. Record
actual provider limitations separately from automated coverage.

The local feature is independent of Google deployment. For Drive, document the
maintainer's OAuth project/client setup, requested scopes and credential handling
in the plan. Account configuration and browser consent remain explicit later
actions; this spec does not access or configure a Google account. Testing-mode
token expiry must be documented, not treated as a product storage failure.

Rollout: deliver and verify local behavior first, then the Drive destination.
Keep product documentation honest about delivered slices. Restore supported
backups on copies during compatibility qualification; retain the existing
newer-schema refusal and downgrade/recovery policy. Do not bump versions, push,
update remote PRs, publish tags/releases or trigger hosted pipelines for this
specification work.

## Clarification outcome and delivery

No material product questions remain. Q1 is whole-library replacement with a
recoverable local copy; Q2 is optional password protection, initially off.
The [plan](plan.md) and [tasks](tasks.md) advance local backup/restore first,
followed by the Drive destination. Scheduling and bidirectional synchronization
remain deferred.

The live Drive qualification requires the maintainer's OAuth application
configuration and designated test account; this is an operational dependency,
not an unresolved local-feature requirement. It does not block local work.

## Provider reference basis

Consulted 2026-10-11; these support the proposed integration, not test evidence:
- Google documents system-browser authorization for installed apps and the
  desktop loopback redirect: [OAuth for desktop apps](https://developers.google.com/identity/protocols/oauth2/native-app).
- `drive.file` is a non-sensitive scope for files created or explicitly opened/
  shared with an app: [Drive scopes](https://developers.google.com/workspace/drive/api/guides/api-specific-auth).
- Refresh tokens may expire/be revoked; external OAuth projects in Testing
  have a seven-day refresh-token lifetime for these scopes:
  [OAuth lifecycle](https://developers.google.com/identity/protocols/oauth2).
