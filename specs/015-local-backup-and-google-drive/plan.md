# Plan: Local backup and restore, then Google Drive

Status: prepared on 2026-10-11 after Q1/Q2 were resolved; local slice A implemented
and qualified in [execution](execution.md). Drive D01–D03 are implemented and
qualified in [Drive execution](execution-drive.md); D04/D05 remain pending. The [spec](spec.md)
owns product behavior; [tasks](tasks.md) order delivery and verification.
Architecture decisions: [ADR 001](adr-001-portable-backup-and-recovery.md),
[ADR 002](adr-002-google-drive-destination.md).

## Architecture and ownership

| Boundary / proposed module | Responsibility |
| --- | --- |
| `pinleaf/backup_format.py` | Versioned payload/envelope reader and writer, canonical JSON, limits, optional encryption; no GTK, network or live store |
| `pinleaf/storage/library_backup.py` | Capture whitelisted raw rows, validate references, reconstruct trusted staged SQLite and replace logical library data |
| `pinleaf/storage/restore_recovery.py` | Durable recovery copy/journal, startup reconciliation and preservation of unreadable original files |
| `pinleaf/storage/atomic_files.py` | Private staging, durable publication, overwrite rollback and filesystem synchronization shared by backups/status/journals |
| `pinleaf/services/backup_service.py` | Immutable capture, operation lifecycle, cancellation and worker jobs; separate local/Drive destination interfaces |
| `pinleaf/ui/backup_window.py` | Local creation, protection option, preview, explicit final restore, progress/status and later Drive actions |
| `pinleaf/app.py`, `ui/main_window.py`, context controller/editor lifecycle | Menu/startup-error wiring, flush/geometry boundary, generation guard, disposal and reload of restored context |
| `pinleaf/integrations/google_drive.py`, `google_auth.py` | Slice B only: OAuth, credential facility, bounded HTTP transport, dated file publication and discovery |

Keep NoteService focused on notes. One operation owner serializes backup/restore;
GTK and its SQLite connection stay on the main thread. Workers receive copied
payloads or use their own disposable staging connections. Progress/results
return through GLib with an operation token. Restore is serialized through that
owner; application generation guards reject old panel/tray actions, disposed
editors reject callbacks and the retired store connection is closed after the
transaction, before recreating services/editors. A cancelled/destroyed operation
cannot accept a stale worker result.

## Portable format and compatibility

Use a UTF-8 JSON `.pinleaf-backup` file, not an archive or a raw database. It has
one version-1 envelope and one logical payload; no filesystem paths, executable
SQL, schema supplied by the backup, compression or extraction are involved.
Contracts and exact crypto/checksum rules: [protocol](contracts/format-v1.md),
[payload schema](contracts/backup-payload.schema.json),
[envelope schema](contracts/backup-envelope.schema.json), [examples](contracts/examples/README.md).

The payload contains capture UUID/time, producer version, library schema version
and exact whitelisted library records. Query raw rows, including soft-deleted
owners/notes, rather than list_notes(), which filters them. Include only the
three portable text-setting keys; do not synthesize absent defaults or retimestamp
records. Context's singleton is an object with its fixed internal row ID rebuilt
by trusted code. Migration notices and device/credential/history files stay out.

| Input | First reader outcome |
| --- | --- |
| Envelope 1, payload 1, library schema 6, either protection mode | Validate and restore |
| Envelope/payload version other than 1 | Reject with supported-version message |
| Library schema 1–5, or a raw SQLite migration snapshot | Not portable format-v1 input; reject, retain source |
| Library schema above 6 | Reject; never downgrade or reinterpret fields |
| A supported older portable version after a future format/schema addition | Add an explicit adapter and fixtures, upgrade only staged data |

The existing 1–5 startup migrations remain supported for installed legacy
libraries; they do not automatically become portable import formats. A future
adapter must update this matrix and tests before widening accepted input.
Released 0.8.0 has no portable reader and already refuses Shared's schema 6.

Limits: file 64 MiB; decoded canonical payload 32 MiB; JSON depth 16; 10,000
profiles/contexts, 100,000 groups and 100,000 notes; password 1–1,024 UTF-8 bytes
when enabled, without trimming/normalization. Validate bounds before expensive
work and fixed KDF parameters before derivation. Reject duplicate JSON keys,
NaN/Infinity, unknown members, invalid UTF-8/base64, booleans in integer fields,
duplicate IDs/keys and invalid ownership/context. Check normalized name keys and
live-name uniqueness. Stored geometry remains signed SQLite integers and is
normalized only by the existing presentation layer. Do not clamp backup values.

Use `jsonschema>=4.10` for bundled trusted schemas and `cryptography>=41` for
Scrypt/AESGCM. Never load schemas/refs from the input or fetch remote schemas.
Copy the canonical contract schemas into packaged resources during implementation
and verify equality; package the JSON files. Add Debian dependencies
`python3-jsonschema` and `python3-cryptography`, and development setup guidance.
The inspected system provides 4.10.3/41.0.7; verify on noble in packaging checks.

## Local create/read flow

1. User chooses protection, then a native local destination. Cancel writes
   nothing. Validate enabled password/confirmation; preserve exact password bytes.
2. On the main thread, serialize the operation, flush all pending editors and
   capture supported geometry through the existing context transition boundary.
   Read an immutable whitelisted payload within a consistent transaction.
   Abort on save failure, retaining unsaved editor text. Resume ordinary editing
   after capture; encoding and I/O run on a worker against the immutable copy.
3. Validate the payload, encode the selected envelope and stage privately in the
   destination directory. Require overwrite confirmation for an existing file.
   Write, flush/fsync, reread/validate, then atomically publish and fsync the
   directory. Retain a recoverable previous copy during overwrite until the new
   file is durable; precommit failure/cancellation retains the previous file.
   If the filesystem also rejects rollback, retain both artifacts and identify
   recovery paths rather than reporting success or discarding either copy.
4. Record success only after durable publication, with the capture time and
   location. Status failures are reported separately from library state. Never
   store passwords in operation history. Discard transient password/key references
   on completion; Python does not promise zeroization of immutable strings.
5. Reading uses a bounded file stream and parser, automatic protection detection,
   optional password prompt, then schema/semantic validation and a trusted staged
   SQLite database. Internal code creates tables and uses parameterized inserts;
   validate data/context/FKs/integrity before NoteStore can repair any context.
   Build preview from the validated payload, not filename/Drive metadata.

Keep status/configuration in private atomic `backup-state.json` beside the local
database (no application schema bump). It contains local operation outcome,
capture time, location and later account/folder references; no portable content,
passwords or tokens. A missing/corrupt status file does not block local notes.
The restore journal is a separate recovery-critical file and must not be ignored
or treated like optional status when corrupt.

## Restore transaction and crash recovery

Preview holds an immutable validated input/staged database, not a live external
path that can change between preview and confirmation. Final confirmation is
destructive-styled, default/close response Cancel. Capture the latest current
edits again so the recovery copy includes changes made while preview was open.

For a readable current library:
1. Briefly gate editor, organization and tray writes. Flush/capture current data,
   generate an unprotected private portable recovery copy under `backups/`, and
   verify and fsync it. This local copy has the database's private trust boundary
   and remains independently restorable without the selected backup's password.
2. Durably create a private restore journal with attempt ID, validated recovery
   and stage paths, and digests of the old/new logical library. Paths are fixed
   within app-owned staging/recovery directories, never supplied by the backup.
3. Advance the library generation, dispose every old editor/dialog and cancel
   autosave/queued callbacks. Replace whitelisted records in one `BEGIN IMMEDIATE`
   transaction on the live connection with `synchronous=FULL`. Delete children
   before parents; insert parents before children, retaining the internal schema.
   Clear migration notices, validate exact restored values/context/FKs and commit.
4. Reload service/context/panel state and recreate eligible restored windows;
   even matching note IDs receive new editors. Validate the committed digest,
   finish/fsync the journal and report success/recovery location. A display failure
   after durable commit reports restored data plus a reopen action, not rollback
   success or an attempt to revive old callbacks.

Before opening NoteStore at startup, reconcile any restore journal. SQLite's
transaction is the readable-library commit boundary. A complete matching old
digest means the interrupted transaction did not commit; matching new means it
did. Report the recovered outcome and retain the recovery copy. If neither
matches, preserve files/staging and offer explicit recovery; do not seed empty
data or guess. Fault injection must prove every named boundary using fresh
processes, not only mocked exceptions.

For a storage-startup error, expose local Restore with no capture/export action.
Close failed connections/helpers first. Copy the original database and any
existing `-journal`, `-wal`, `-shm` files byte-for-byte to a private attempt
directory, record hashes, reread and fsync. Preserve that complete set before
moving any original file. Journal every move and install only the validated
clean staged SQLite file; do not pair it with old journal/WAL/SHM files. Startup
reconciliation before NoteStore deterministically finishes the verified new
installation or restores the preserved original set. Failure to preserve stops
replacement. Never open the damaged source as a migration/import payload.

Cancellation is honored before commit preparation; once the journaled commit
boundary starts, finish/recover and report its actual outcome. Network/file jobs
remain cancellable independently of library commit. Always remove disposable
staging after safe completion; retain journals/artifacts needed for recovery.

## Google Drive slice

Use the same encoded bytes through a destination interface; no remote domain
model or note edits. Adopt system-browser desktop OAuth with loopback on
127.0.0.1/random port, validated state and explicit PKCE S256 using
google-auth-oauthlib. No embedded browser, OOB copy/paste, service account or
Pinleaf backend. Only `drive.file` is requested. Bound consent waiting and close
its listener on cancel/timeout. User configures no Cloud project in the UI.

Use requests/google-auth for Drive v3 HTTPS transport, connect/read timeouts of
10/30 seconds, bounded/paginated listings and downloads capped at 64 MiB. Disable
automatic application-level retries; token refresh may occur within a deliberate
operation. Only expected Google API hosts/upload URLs are followed. Errors are
mapped to Retry/Reconnect/refresh without logging remote bodies/tokens.

Mark app-created folders and files with appProperties rather than trust folder
names. Locate/create visible Pinleaf / Backups; discover backups across matching
app folders even if local folder history is absent or duplicated. Keep distinct
UUIDs per Save and preserve the attempt UUID for Retry. Upload as pending, verify
returned size/checksum, then mark complete; list only completed compatible copies.
An ambiguous upload response is reconciled by attempt UUID before retry creates
another copy. Cleanup can remove only that attempt's incomplete app-created file.
Download to private staging and run the identical local validation/preview path.

Store refresh/access credentials with SecretStorage's Secret Service, keyed by
application/client/account. No generic keyring backend with plaintext fallbacks.
If unavailable/locked/declined, offer clearly labelled session-only authorization.
Disconnect drops this installation's item/session and cancels its operation;
do not revoke the Google project or delete backups. Account identity/configuration
does not travel in the portable payload. Add slice-B dependencies only then:
google-auth-oauthlib, requests and SecretStorage with matching Debian packages.

Maintainer setup is an operational dependency for live qualification: enable
Drive API, configure desktop OAuth/consent and supply the registered public-client
configuration through a package resource or private development override. Do not
commit test refresh tokens or fabricate a client ID. A desktop client secret is
not a secure application secret; it never replaces PKCE/state. Testing-mode
expiry/reconnect is documented. Until this setup exists, use provider doubles
and report live OAuth/two-installation coverage as pending, without blocking A.

## Verification and delivery

Map tasks to [maintained cases](verification.md), using synthetic data only.
Validate contracts and valid/invalid examples now. During implementation run
focused unit/integration, real-process crash recovery, generation/autosave and
native X11 keyboard/narrow/theme checks. Compare every preserved field, not just
visible notes; include deleted owners, null context, unknown fonts, storage
failures and both protection modes. Measure the 1,000-note fixture and responsive
progress under delayed work. Keep screenshots, counts and actual results in a
separate execution record; do not claim Wayland/Orca qualification without evidence.

Finish each slice with unittest, compileall, diff/contract checks and packaging
dependency/resource checks. Update README/Unreleased only for implemented
behavior. Keep application version 0.8.0 and schema 6; no push, remote PR edits,
hosted pipelines, tag or release. Code rollback leaves portable/recovery files
intact and continues the existing schema compatibility policy.
