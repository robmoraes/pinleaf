# Execution: Google Drive connection

Date: 2026-10-16. Boundary: D01 connection, D02 upload/discovery and D03 restore.

The maintainer enabled Drive API, registered a desktop OAuth client with
`drive.file`, downloaded its configuration under ignored `tmp/`, and added the
designated Google account as a test user. No client contents or user credentials
are committed. Use `PINLEAF_GOOGLE_CLIENT_FILE` for the explicit development
override; no implicit JSON discovery is performed by the application.

Implemented browser authorization with a random-port IPv4 loopback listener,
explicit random state/PKCE S256, three-minute consent timeout, cancellation,
bounded token exchange, exact granted-scope validation and Drive account lookup.
Invalid callbacks cannot complete authorization. Provider errors and HTTP logs
do not expose callback codes, tokens or response bodies. Browser return only
instructs the user to check Pinleaf; it does not claim success before exchange.

Credentials use Secret Service with application/client/account/installation
attributes. Locked/unavailable storage fails visibly; session-only access must
be selected explicitly. Saved access is loaded only during Connect; tokens are
refreshed only during deliberate account/Drive operations.
Disconnect forgets local access without remote revocation or file deletion.
The backup worker runs account operations off the GTK thread, preserving local
note editing. Startup and importing local storage need no OAuth libraries or
network. Dependencies are declared for Python and Debian packaging.

Automated cases in `tests/test_drive_auth.py` exercise state, actual PKCE URL
generation, declined/browser-failed/timed-out/cancelled consent, listener cleanup,
scope/offline rejection, safe errors, keyring failure, explicit session mode,
saved/revoked/expired credentials and isolated disconnect. GTK worker tests in
`tests/test_drive_ui.py` cover account status, cancellation and local controls.
Loopback tests require socket permissions outside the execution sandbox.

Full regression on this machine: **233 tests passed, zero skips**, 11.521 seconds.
Compileall and diff whitespace checks passed. GTK emitted a nonfatal popup
stacking warning; existing GTK/Python deprecations are not changed by this slice.

Live browser consent and Drive account lookup passed on 2026-10-16: the
maintainer completed browser authorization and explicitly confirmed that
`Connected: <email>` appeared in the development Backup & Restore window.
This confirms the real OAuth round trip; it does not establish persistence
across restart or access from a second installation. No account address or
credential is recorded in this evidence.

Real keyring access was then reused successfully from a fresh Python process
without browser authorization. Two independent installation authorizations,
native screenshot/accessibility qualification and Ubuntu 24.04 packaging remain
pending. Current machine is Ubuntu 26.04 / Python 3.14 / Wayland. Google testing
mode may expire grants; reconnect must remain available. The client is currently
development-only; a release distribution configuration is still required.

## D02: upload and discovery

The destination uses only Drive v3 HTTPS endpoints, no redirects, 10/30-second
connect/read timeouts, bounded metadata and paginated listings (100 pages/10,000
unique items). Visible root/backup folders are identified by private
`appProperties`, not their names. Discovery covers matching backup folders even
when names are duplicated or the destination has no folder/history cache.

Each deliberate save captures and validates the existing portable format in a
worker. Each attempt gets a UUID and a pre-generated Drive file ID before its
first upload, then uses resumable 256-KiB chunks. The file remains marked pending
until provider size/MD5 match the exact encoded bytes; publication and reread
must confirm complete before success is reported. MD5 here detects transport
corruption, not malicious modification; portable reader validation remains
mandatory for future downloads. Partial/unsupported/unmarked files are excluded
from discovery. No remote file is overwritten or deleted by this implementation.

Retry retains the original capture, encoded bytes, UUID, reserved file ID and
resumable URL in memory. It reads provider state first, resumes from the received
offset and reconciles lost upload/publication responses before any further
transfer. A stable reserved ID avoids duplicate copies even if a previous create
response was lost. Retry is explicit and bound to the originating client/account.
The retained source is cleared after success, a new save, Disconnect or shutdown;
retry across process restart is not implemented. After restart, completed copies
remain discoverable, pending copies stay excluded and a new Save starts a new
attempt. No automatic pruning or incomplete-file cleanup is performed.

Local and Drive statuses are separate. Failure preserves the last successful
upload timestamp. A success whose optional local status write fails is reported
with a warning, without pretending the cloud copy failed. Refresh clears stale
displayed results before requesting the current listing. Cancellation can race
with remote completion; the UI directs Retry/Refresh to establish the outcome.

Stateful provider tests cover distinct saves, both protection modes, exact
payload preservation, ambiguous completion, interrupted chunks, resumed offsets,
quota denial, checksum mismatch, cancellation before publication, deleted/newer/
malformed entries, pagination, duplicate names, cross-folder discovery, account
isolation, local-status faults and preservation of earlier/unrelated files.
Transport tests reject unexpected hosts/redirects and bound errors/metadata.
GTK tests use actual buttons and the real worker for default-off protection,
save/list, failure/retry preserving the original capture despite later edits,
removal of stale results after an offline refresh, and Disconnect cancelling an
active transfer before forgetting the session. Local editing remains
independent; pending edits are captured by the same application callback as A.

Live provider drill: two synthetic contract-fixture copies were uploaded, one
unprotected and one protected with a synthetic password. Both passed provider
size/checksum and complete-publication rereads. A newly constructed destination
with no origin folder/history discovered both. Only synthetic fixture data was
uploaded; daily-use notes were not read. The copies are intentionally retained
for the forthcoming D03 restore drill. The local development result manifest
contains only generic names, file IDs and protection mode under ignored `tmp/`;
no credentials or user account address are recorded. This validates real Drive
upload/discovery, not independent installation consent or restoration.

Final D02 regression: **259 tests passed, zero skips**, 13.581 seconds on the
current Wayland desktop. Compileall, `git diff --check` and the two schemas/nine
contract fixtures passed. The same nonfatal GTK popup stacking warning remains.

No Drive download, library replacement, release version, Git push, PR
modification or package publication is part of D02. D03–D05 remain pending.

## D03: download, preview and restore

The inline selector adds **Preview & Restore…** to each discovered copy. Selection
rechecks complete status, size/MD5, captured time, protection mode, name, marked
parent folder and `capabilities.canDownload` before download. The transport uses
only the fixed Drive `files.get?alt=media` endpoint, disables redirects and streams
into an exclusive 0600 file inside a private temporary directory. Declared and
actual length cannot exceed the expected size or 64 MiB; truncated, oversized or
checksum-mismatched responses are rejected. Metadata is reread after transfer to
reject concurrent replacement/removal. Temporary files are removed on every
completion, failure or cancellation; a remote filename is never a local path.

The selected bytes pass through the same portable reader and trusted SQLite
staging as local input. Password detection comes from the file, not the checkbox
or listing. Wrong passwords/authentication failures reveal no private preview;
an explicit password retry reuses the immutable downloaded bytes. The validated
payload's capture time and protection mode must match the selection metadata.
Selecting another copy discards an older preview before download, so a failed
new selection cannot leave a stale Restore action enabled.

**Cancel Preview** removes the staged selection. Final **Restore This Backup…**
uses A's default-Cancel destructive confirmation, captures pending edits again,
preserves a validated local recovery copy and applies the same journaled
replacement and application/editor-generation reload. No network request is
needed once a preview is validated. Restore preserves this installation's
connection and status; credentials/history never travel in the portable payload.
There is no automatic restore or sync. A cancelled download restarts only on an
explicit new selection, without reusing an unverified partial file.

Automated coverage adds selection rechecks, restricted/moved/deleted files,
concurrent metadata changes, response limits, redirects, corruption/truncation,
midstream cancellation/network failure, exclusive/private output, malformed
portable data, metadata mismatch, cleanup and password retry without redownload.
Two isolated service directories demonstrate discovery without origin history,
full-library round trips in both modes, repeated restore without duplication,
preserved hidden/deleted/context/appearance values, edits after preview in
recovery, unchanged target data on rejection/cancel, and offline final restore.
GTK tests click actual row/password/cancel controls and ensure failed selection
cannot leave an old preview restorable.

`tests/gui_drive.py` runs the full application with a unique application ID,
disposable library and explicit helper cleanup. Both simulated and live Drive
runs passed for unprotected and protected copies. They select actual rows,
reject one synthetic wrong password, preview without replacing data, verify
default Cancel, then restore after a pending editor change. Every retained
library field matches the synthetic fixture, only its two eligible note windows
open, hidden/deleted notes stay closed, and local recovery includes the last edit
made after preview. The connected account object survives library replacement.
The simulated run observed two worker timer heartbeats; the live run observed
37, demonstrating that the GUI loop continued while network/crypto work ran.
These are workflow observations, not performance guarantees.

Reproduction on a graphical desktop:

```bash
/usr/bin/python3 tests/gui_drive.py
/usr/bin/python3 tests/gui_drive.py --live
```

Live mode requires the maintainer's ignored development JSON/result manifest and
saved development keyring access. It selects only the two identified synthetic
D02 files, requests no new consent, creates no cloud files and replaces only its
own disposable library. The remote fixtures remain intact. This qualifies the
live storage/UI path into a separate library on this machine; it does not replace
the D04 independent-authorization/disconnection drill on two installations.

Final D03 regression: **277 tests passed, zero skips**, 17.392 seconds.
Compileall, whitespace checks and both schemas/nine format fixtures passed.
An additional race test confirms that Disconnect at download completion cannot
start a preview; offline restore after validation is also covered. The final
simulated native run passed after helper-cleanup checks were tightened. Existing
nonfatal GTK popup stacking and Ayatana deprecation diagnostics remain.

D04/D05 remain pending: independent installation authorization, deliberate test
cleanup, release client distribution, native screenshots/accessibility and final
packaging qualification. Version and remote publication remain unchanged.
