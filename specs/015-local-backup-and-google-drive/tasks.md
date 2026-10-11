# Tasks: Local backup and restore, then Google Drive

Order is intentional: complete and verify local backup/restore before application
network code. Checkboxes describe completed work, not authorization prompts.
The maintainer accepted Q1/Q2 and requested advancing on 2026-10-11.

## Specification and architecture

- [x] **B01 — Agreement and Check:** Resolve whole-library replacement/recovery
  and optional protection, update spec/outcome contract/package status, complete
  Check. Validate unique IDs, preservation coverage and links.
- [x] **B02 — Plan and contracts:** Record ADRs, format-1 schemas/examples,
  limits/version matrix, replacement/recovery boundaries and ordered work.
  Validate schema structure, valid/invalid fixtures and cryptographic examples
  with system jsonschema/cryptography. Product implementation is still pending.

## Slice A: local backup and restore

- [ ] **A01 — Trusted format reader/writer:** Implement canonical JSON,
  bounded parsing, payload/envelope schemas, semantic validation and optional
  Scrypt/AESGCM. Bundle contract schemas and wire packaging dependencies.
  Verify TC-BKP-001,007,008,016, duplicate keys, floats/non-finite values,
  unexpected members, fixed KDF
  bounds, wrong password/header changes, max-size boundaries and fresh randomness.
- [ ] **A02 — Consistent full-library capture:** Export raw whitelisted tables
  and portable settings after pending edit/geometry capture; no retimestamping.
  Keep worker data independent of live SQLite/GTK objects. Verify TC-BKP-001,002,
  hidden/deleted owners, null context, absent/default settings and empty library.
- [ ] **A03 — Durable local destination:** Stage, validate, fsync and publish a
  unique file with overwrite handling/cancellation; maintain private local status
  separately. Verify TC-BKP-003 and permission/space/write/fsync/rollback faults;
  prior destination and current editor text remain recoverable.
- [ ] **A04 — Read/preview and trusted staging:** Build validated staged SQLite
  from payload using trusted schema/parameterized values, before context repair.
  Expose preview counts and protection detection, with immutable selected input.
  Verify TC-BKP-004,007,008,016 and unchanged original bytes after rejection/cancel.
- [ ] **A05 — Journaled replacement and recovery copy:** Flush again at final
  confirmation, create independently readable private recovery, gate all writes,
  invalidate old editor generations and replace in one SQLite transaction.
  Verify TC-BKP-005,006,009 with text changes after preview, matching IDs,
  queued autosave/tray/dialog events and commit/reopen failures.
- [ ] **A06 — Process-interruption recovery:** Reconcile journal before NoteStore
  startup; preserve staged/recovery artifacts and choose complete old/new data.
  Kill/restart disposable subprocesses at each boundary, including post-commit
  before cleanup. Verify TC-BKP-006 and prevent accidental empty-library seeding.
- [ ] **A07 — Startup-error restoration:** Offer local Restore without a valid
  current store; preserve closed original DB/journal/WAL/SHM bytes and journal
  staged file installation. Verify TC-BKP-015 and interruption during each move;
  failed preservation must block replacement.
- [ ] **A08 — GTK workflow:** Add main-menu entry and dedicated local window,
  native choosers, unchecked protection option, validation, preview, explicit
  final Restore and progress/cancel/focus. Wire startup-error entry and restored
  context reload. Verify TC-BKP-004,009,014,016 with isolated native X11, light/
  dark/narrow screenshots and keyboard actions; inspect actual screenshots.
- [ ] **A09 — Local qualification and documentation:** Run all relevant cases
  with small/1,000-note libraries, both modes and independent installations.
  Record timings, crash evidence and platform limits. Update implemented UX docs,
  README/Unreleased, run full unittest/compileall/diff and package checks. Record
  evidence; only then mark slice A delivered. Keep changes local/version unchanged.

## Slice B: Google Drive destination

- [ ] **D01 — OAuth and credential boundary:** Add lazy integration dependencies,
  registered-client configuration, system-browser PKCE/state/loopback flow,
  bounded cancellation and Secret Service/session-only storage. Verify
  TC-BKP-010,013 with provider/credential doubles, no startup network, no plaintext
  token files, cancellation/denied scopes and disconnect without project revocation.
- [ ] **D02 — Publish and discover dated copies:** Implement marked visible
  folders, pending/complete publication, attempt reconciliation, pagination and
  metadata checks. Verify TC-BKP-010,011,012 against mock transport, duplicate
  names, absent local history, ambiguous responses and preservation of other files.
- [ ] **D03 — Download through local restore:** Add bounded download/validation
  and remote selector/status; reuse A's preview/confirmation/recovery path and
  per-file protection. Verify TC-BKP-011,012,014,016, connection loss, quota,
  revoked access, external removal and both backup modes. Local editing remains
  independent and no automatic synchronization is introduced.
- [ ] **D04 — Maintainer OAuth setup and live drill:** Once a registered desktop
  client and designated test account are available, document setup/testing expiry,
  perform explicit browser consent, save on one isolated installation and restore
  on another with no origin history. Verify TC-BKP-011,013 in real Drive; clean up
  only identified test artifacts. This operational prerequisite does not block A
  or mocked D01–D03. Do not replace daily-use notes or publish credentials.
- [ ] **D05 — Complete package evidence:** Run full regression, compileall,
  schema/example/resource/dependency/diff checks and native accessibility/layout
  validation; record live versus mocked coverage and update delivered documentation.
  Keep remote publication/version/release work deferred until the maintainer's
  separate publication instruction.

No implementation task is checked by specification-only validation. No application
network calls or user-data operations are performed by this task preparation.
