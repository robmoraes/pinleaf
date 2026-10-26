# Maintained verification cases: Backup and restore

Local cases TC-BKP-001–009 and 015 are automated; local portions of 014/016 are
automated. Drive cases 010–013 and remote portions of 014/016 have provider,
GTK and native checks, complemented by a live two-installation drill. These are
reusable definitions; actual results and remaining qualification limits are in
[local execution](execution.md) and [Drive execution](execution-drive.md).

## Shared preconditions, data and cleanup

Use disposable app data directories and isolated application/session identities;
never read or restore the daily-use library. Fixture L has two profiles (Pessoal
and Trabalho), Shared in each and Kubernetes in Pessoal. Notes have deterministic
IDs and timestamps: `shared-open` (AWS tags, open), `project-open` (Kubernetes,
open), `project-hidden` (Café checklist, hidden) and `project-deleted` (deleted).
Set nondefault text appearance and Pessoal / Kubernetes active; include a second
profile's null ordinary context. Generate 1,000 notes deterministically for the
large fixture, including hidden/deleted populations. Compare raw retained fields
with the [preservation contract](contracts/backup-outcomes.json), not just the
currently visible note list. Use synthetic passwords, never real credentials.
Extend round-trip fixtures with a retained deleted profile/group and their
deleted notes to ensure that all retained records, not just live owners, survive.

For local cases the network is unavailable. Drive cases use controlled provider
responses for repeatability. The live cross-installation case additionally needs
a maintainer-designated test account, configured OAuth application, explicit
browser consent on each isolated installation and a dedicated disposable folder.
Changing Google publishing/account settings is a later explicit operational
action, not a side effect of defining these cases.

Cleanup for every case: stop/reap test app and tray processes, close stores,
remove staging/temp directories and test IPC, and discard disposable libraries.
For live Drive qualification, remove only identified test-created backup files
and test-local credentials with explicit test cleanup authorization; preserve
unrelated remote files and connections. Keep no tokens/passwords in evidence.

## Cases

| ID / title | Traceability | Risk / classification | Objective; Given / When / Then |
| --- | --- | --- | --- |
| TC-BKP-001 Whole-library offline round trip | BK-01, BK-02, BK-03, BK-05, BK-06; AC-01, AC-10 | Critical / storage integration | Given L or an empty library offline, when creating a portable file and restoring to another disposable installation, then all preserved values match, excluded data is absent and no account/network is required. |
| TC-BKP-002 Capture pending edits at one boundary | BK-04, BK-06; UX-02; AC-02 | High / application integration | Given delayed autosave and controlled encoding/upload delay, when capturing before a second edit, then the first edit is backed up, the second stays local and status identifies the capture time. |
| TC-BKP-003 Failed export preserves previous data | BK-04, BK-05; AC-03 | Critical / fault injection | Given an existing destination and injected flush, permission, write, validation or space failure, when saving/cancelling, then previous file and library remain usable, unsaved text stays in its editor and success is not reported. |
| TC-BKP-004 Preview and cancellation are read-only | RS-01, RS-03; UX-01; AC-04, AC-15 | High / GTK integration | Given L and a different backup, when opening/closing chooser or cancelling preview by keyboard, then no library/context/connection is replaced and focus returns. |
| TC-BKP-005 Restore replacement is reversible | RS-03, RS-05; AC-05 | Critical / application integration | Given L and a current edit after preview, when confirming replacement, then a separately validated recovery copy includes the edit and can restore the exact former library; selected data replaces without merging. |
| TC-BKP-006 Recover every interrupted commit boundary | RS-03, RS-04; AC-06 | Critical / process and fault injection | Given deterministic hooks for recovery-copy, stage validation, commit and reopen boundaries, when injecting failures or killing/restarting a test process at each, then startup yields a complete old/new library, retains recovery and never combines their rows. |
| TC-BKP-007 Reject untrusted and incompatible input | RS-01, RS-02; AC-07 | Critical / format and security integration | Given truncated, malformed, duplicate-ID, invalid-reference, unsupported-version, traversal and size-limit fixtures, when reading/restoring, then rejection precedes replacement and cannot write beyond private staging. |
| TC-BKP-008 Authenticate password-protected content | PR-01, PR-02; AC-08 | Critical / cryptographic integration | Given L and a synthetic password, when enabling protection, inspecting export and trying wrong passwords/altered bytes before correct restore, then private data is not plaintext, invalid authentication reveals no private preview, no plaintext fallback is attempted and correct round trip succeeds. |
| TC-BKP-009 Preserve restored visibility and portability | RS-05, RS-06; BK-02; AC-09 | High / GTK and native integration | Given a backup with open/hidden/deleted notes, nullable contexts, unavailable font and differing display bounds, when restoring twice, then IDs/timestamps are exact, no hidden/deleted note is revived and supported visibility/font behavior remains usable. |
| TC-BKP-010 Drive consent and isolated dated saves | GD-01, GD-02; PR-02; AC-11 | High / provider contract integration | Given cancelled consent, limited scopes and deterministic account/storage responses, when connecting then saving twice, then cancellation stores no connection, copies have unique IDs and no full-Drive access or plaintext credential fallback occurs. |
| TC-BKP-011 Discover and restore on another installation | GD-02, GD-03; BK-03; AC-12 | Critical / two-installation provider acceptance | Given two isolated installations, the same designated account and no origin history on the second, when saving on the first and selecting/restoring on the second, then discovery handles pages/duplicate names and uses the local validated restore reader. Live consent/Drive qualification complements automated provider doubles. |
| TC-BKP-012 Remote errors keep local work available | GD-02, GD-04, GD-06; BK-01; AC-13 | High / provider fault integration | Given injected timeout, network loss, quota denial, revoked token or externally missing/corrupted file, when saving/listing/restoring, then local editing continues, earlier copies survive, failed status is truthful and retry/reconnect/refresh is actionable. |
| TC-BKP-013 Disconnect and restart are local operations | GD-04, GD-05, GD-06; BK-01; AC-14 | High / lifecycle and provider contract | Given two connections and uploaded copies, when disconnecting one then restarting, then local credentials are forgotten, notes/files and the other installation's access are not deliberately removed/revoked, and no startup transfer/restore occurs. |
| TC-BKP-014 Accessible responsive workflow | UX-01, UX-02; AC-15 | Medium / native UI and accessibility | Given a 1,000-note fixture, narrow/light/dark layouts and controlled slow storage/provider work, when using keyboard selection/cancellation and final Restore, then controls remain reachable, progress remains responsive and final replacement requires explicit selection. |
| TC-BKP-015 Recover from storage startup failure | RS-07; AC-16 | Critical / startup and recovery integration | Given a damaged disposable database and journal/WAL/SHM artifacts, when selecting a valid backup from the startup error, then original file bytes are preserved before confirmed replacement; an injected preservation failure leaves them intact and prevents commit. |
| TC-BKP-016 Optional protection keeps password-free recovery available | PR-01, PR-02, BK-05; AC-17 | High / GTK and format integration | Given L, offline local creation and mocked Drive creation, when leaving protection off, retrying empty/mismatched enabled passwords and creating a protected copy, then unprotected files round-trip without a password, invalid input creates no file, the next creation defaults off and restore requests a password only according to the selected file's mode. |

Detailed format fixtures, commit hooks, provider doubles and exact limits are
defined by the [plan](plan.md) and [tasks](tasks.md). Q1/Q2 are resolved; update
this ledger whenever accepted behavior changes. Real OAuth qualification is not
replaced by passing a mock.

## Drive delivery evidence

Connection, upload/discovery and download/restore evidence is maintained in
[Drive execution](execution-drive.md). Provider/transport/storage/GTK tests
cover TC-BKP-010–014/016 error and preservation boundaries. Live D03 restores
used the designated account and disposable target libraries in both protection
modes; D05 additionally qualified Noble's Google SDKs, 1,000-note native restore,
actual default-Cancel keyboard input, responsive layouts, AT-SPI controls and a
configured disposable Debian binary. Independent A/B browser authorizations subsequently passed with 1,000 notes in
both modes. After A disconnected, a fresh B connection refreshed its own token
and downloaded successfully. Scoped cleanup removed all three new files and
preserved every pre-existing file; see [live report](artifacts/two-installations.json).
