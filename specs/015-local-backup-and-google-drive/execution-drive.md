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

## D05 local qualification checkpoint

The live D04 helper is now prepared with two fresh libraries and independently
keyed Secret Service connections. It requires two actual browser consents and
uses 1,000 synthetic notes, both backup modes, B's own distinct save, restart and
real token refresh after A disconnects. Only this invocation's three verified
test files may be deleted by cleanup; pre-existing copies and development access
are preserved. The first A consent timed out without confirmation, before any
upload or usable connection. D04 remains pending human browser interaction.

The Google SDK packages published for Ubuntu 24.04 are older than this host's:
Google Auth 1.5.1-3 and google-auth-oauthlib 0.4.2-1. They were downloaded from
the official Ubuntu archive and extracted under `/tmp`, with six 1.16.0-4;
system packages were not downgraded. Google Auth 1.5 lacks `Credentials.to_json`.
The credential writer now uses the SDK's documented authorized-user refresh
fields when that method is unavailable, still writing only to Secret Service.
Modern SDK behavior is retained. Python/Debian minimum dependencies now reflect
the qualified APIs. SDK support for explicit PKCE was checked in the actual
0.4.2 source and its real authorization URL test passed.

Using these extracted Google SDKs, **64 focused Drive tests passed**, and the
live real-app restore passed again for both synthetic D02 copies, with 35 worker
timer callbacks. This verifies the older SDK path on the current Python 3.14
host, not a complete separate Noble OS/GTK session. Official package reference:
[OAuthlib package](https://packages.ubuntu.com/noble/python3-google-auth-oauthlib),
[Google Auth package](https://packages.ubuntu.com/noble/python3-google-auth).

Native visual/keyboard QA passed in a nested off-screen X11 server. The harness
now forces X11 even on a Wayland host, so tests cannot accidentally render into
the daily desktop. ImageMagick 6/7 capture commands are both supported. Long
filenames wrap, the session checkbox wraps at narrow widths, connection setup
controls hide while connected, and listing/preview actions reveal their results
after allocation. The copy list has a minimum useful viewport instead of
collapsing to a clipped action. Normal/light and 360-pixel dark screenshots were
inspected; actual XTest Enter cancels the final destructive dialog in both modes.
The 1,000-note native restore passed for both modes with ten worker heartbeats.

A separate AT-SPI process passed five phases: disconnected setup, connected
save/list/selection, protected-file password, validated preview/cancellation,
and final confirmation. Buttons expose focusable names and each copy's tooltip
description identifies its generic filename when GTK's computed button name
takes precedence over the requested label. Protected selection exposes no
private preview before unlock. Cancellation preserved the original library.
See [AT-SPI evidence](artifacts/drive-accessibility.json). This does not qualify
Orca speech or human screen-reader usability.

The unsigned all-architecture Debian binary built in a private temporary source
copy. Only its build copy received whitelisted desktop-client configuration;
no client contents, user credentials or databases entered the repository.
Extraction verified both schemas, Drive modules, runtime dependencies, manpage
and configuration loading without `PINLEAF_GOOGLE_CLIENT_FILE`. A manpage was
added to resolve the previous missing-manual warning. Strict Lintian passed
without errors or warnings outside the sandbox; the sandbox's man-db rendering
pipeline was restricted even though direct groff rendering passed. See
[package evidence](artifacts/package-qualification.json). The binary was neither
installed nor published and retains 0.8.0 only as a disposable unreleased build.

CI/release jobs now install the new Python runtime dependencies before tests.
The release job validates the bundled client without developer overrides before
building, preventing an unconfigured Drive binary from being published. The
maintainer's distribution-client choice remains pending; the original JSON stays
ignored and no application publishing/account setting was changed. Normal
development CI does not require a registered client.

Reproduction additions:

```bash
/usr/bin/python3 tests/gui_session.py /usr/bin/python3 tests/gui_drive.py --visual
/usr/bin/python3 tests/gui_session.py /usr/bin/python3 tests/gui_drive.py --large
/usr/bin/python3 tests/gui_session.py --a11y /usr/bin/python3 tests/gui_drive_accessibility.py
```

Set `PINLEAF_QA_SCREENSHOTS` or `PINLEAF_QA_A11Y_REPORT` to record synthetic
artifacts. The [maintainer guide](../../docs/release/google-drive-oauth.md) records
the explicit live two-installation and package qualification commands.

Final local regression: **280 tests passed, zero skips**, 17.581 seconds.
Compileall, diff whitespace checks and both schemas/nine contract examples
passed. The final configured disposable Debian build passed strict Lintian with
empty diagnostics; its SHA-256 is recorded in the package artifact manifest.

Inspected synthetic screenshots:

- [Drive copies, light](screenshots/drive-copies-light.png)
- [Drive copies, narrow dark](screenshots/drive-copies-narrow-dark.png)
- [Validated preview, light](screenshots/drive-preview-light.png)
- [Validated preview, narrow dark](screenshots/drive-preview-narrow-dark.png)
- [Protected-file password](screenshots/drive-password-dark.png)
- [Final confirmation, light](screenshots/drive-confirmation-light.png)
- [Final confirmation, narrow dark](screenshots/drive-confirmation-narrow-dark.png)

At this checkpoint D04 and final D05 closure remained pending independent
consent and distribution configuration (D04 was subsequently completed below). No version bump, package installation, push, release or PPA upload
has occurred.

## D04 completed live qualification

The maintainer completed both browser consents on 2026-10-16. The real Drive
helper passed with two fresh data directories and independent Secret Service
keys, using 1,000 synthetic notes. B discovered, downloaded and restored A's
unprotected and protected copies without origin history; recovery retained the
edit made after preview. A discovered B's distinct copy.

After A disconnected, B reopened its own saved connection, performed a real
expired-token refresh, listed and downloaded successfully. Cleanup removed
exactly the three files created by this invocation and verified every pre-existing
file remained. Disposable keyring entries and local libraries were removed.
Daily-use notes and the development connection were preserved.

The [sanitized live report](artifacts/two-installations.json) records PASS for
all checks. D01–D04 are complete. D05's technical checks have passed; final
closure still awaits the maintainer's release-client selection. No version bump,
installation, push or publication occurred.

## Distribution client selected and D05 completed

The maintainer selected the existing Pinleaf Desktop client for distribution;
a separate development client can be created later. Only the installed client's
four public desktop configuration fields were added to the bundled resource.
The original download stays ignored; no user tokens or account data are bundled.

A fresh disposable Debian build used the repository resource directly, without
client injection, and loaded it with the development override unset. Package
inspection and strict Lintian passed with empty diagnostics. The 20 focused OAuth
tests passed with loopback permission (the sandbox initially blocked listeners).
The updated [package report](artifacts/package-qualification.json) records the
artifact hash. D01–D05 are complete. Google Testing-mode limitations remain;
general distribution still requires deliberate Console publishing configuration
and the normal release process. No install, version bump, push or publication
was performed.
