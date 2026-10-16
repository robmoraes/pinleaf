# Execution: Google Drive connection

Date: 2026-10-16. Boundary: D01 implementation, before Drive transfers.

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
be selected explicitly. Saved access is loaded/refreshed only during Connect.
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

Real keyring persistence/restart, two installations,
native screenshot/accessibility qualification and Ubuntu 24.04 packaging remain
pending. Current machine is Ubuntu 26.04 / Python 3.14 / Wayland. Google testing
mode may expire grants; reconnect must remain available. The client is currently
development-only; a release distribution configuration is still required.

No Drive upload/list/download, backup replacement, release version, Git push,
PR modification or package publication is part of this slice.
