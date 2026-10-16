# Google Drive OAuth client and qualification

Pinleaf is a direct desktop client. The maintainer registers the OAuth
application once; users authorize their own Drive in the system browser.
There is no Pinleaf backend or user-operated Cloud project.

## Development and distribution

The accepted integration requests only
`https://www.googleapis.com/auth/drive.file`. Register an **App for desktop**,
enable Drive API and configure the OAuth consent screen/test users. Both
installations must use the same registered application/client for the qualified
discovery workflow.

Development uses the ignored downloaded JSON through
`PINLEAF_GOOGLE_CLIENT_FILE=/absolute/path/to/client.json`. The application does
not scan `tmp/` automatically. A distributed build instead uses
`pinleaf/resources/google-client.json`, containing only an `installed` object
with `client_id`, `client_secret`, `auth_uri` and `token_uri`.

A desktop client's configuration is distributed with the application; it is
not a confidential server credential. PKCE/state and the user's consent protect
authorization. User refresh/access tokens are separate and belong only in the
system Secret Service or explicitly selected session memory. They must never
enter the client resource, package, repository or portable backup. See Google's
[desktop OAuth documentation](https://developers.google.com/identity/protocols/oauth2/native-app).

Selecting the release client is a maintainer decision. At the current D05
checkpoint, the existing client is still a development override and its original
download remains ignored. The qualified local binary injected a sanitized
client into its temporary build copy only. No client contents were committed.
The release workflow validates the bundled resource, with development overrides
disabled, before building/publishing; it will refuse an unconfigured release.

Google's **Testing** mode limits access to configured test users and may expire
refresh grants after seven days for these scopes. Disconnect/reconnect remains
available. Changing the application's publishing/verification status is a
separate Google Console operation before general distribution, not a side effect
of local qualification. See [OAuth token lifecycle](https://developers.google.com/identity/protocols/oauth2).

## Two independently authorized installations

Run from the repository root in a desktop session with an unlocked system
keyring, using the designated test account:

```bash
PINLEAF_GOOGLE_CLIENT_FILE=/absolute/path/to/client.json \
  /usr/bin/python3 tests/drive_two_installations.py \
  --live --cleanup-created --report /tmp/pinleaf-two-installations-report.json
```

The helper opens consent for A, then for B. Confirm both with the same Google
account. Each has a fresh data directory and its own installation key in Secret
Service. A contains 1,000 synthetic notes; daily-use/development notes are not
read. The target discovers and restores A's protected/unprotected copies without
origin history, and its recovery preserves a synthetic edit made after preview.
B also saves a distinct copy. Disconnecting A must remove only A's key while a
fresh B object can load, refresh, list and download through its independent key.

Cleanup rechecks and deletes only the three copies created by that invocation,
preserving every pre-existing copy. Both disposable keyring items are forgotten;
the temporary libraries are removed. If a created file changes unexpectedly,
it is preserved and the local report records the remaining test IDs for
inspection. This helper is test infrastructure, not a remote deletion feature.

The completed live drill passed both independent browser authorizations,
1,000-note transfers in both modes, recovery preservation and B's actual token
refresh after A disconnected. Cleanup removed all three new copies and preserved
every pre-existing copy. See the [sanitized report](../../specs/015-local-backup-and-google-drive/artifacts/two-installations.json).

## Local package qualification

```bash
/usr/bin/python3 tests/qualify_debian_package.py \
  --client-file /absolute/path/to/client.json \
  --report /tmp/pinleaf-package-report.json
```

This copies only tracked/nonignored sources into a private temporary build tree,
injects only the whitelisted client configuration there, builds an unsigned
Debian binary, extracts it and checks schemas/modules/dependencies/manpage and
client loading without the developer override. Lintian must pass with no errors
or warnings. It neither installs the package nor publishes artifacts. The
existing version is retained solely for this disposable unreleased build; choose
a new never-uploaded release version through the normal release process later.

Build tools: `debhelper`, `dpkg-dev` and `lintian`. Native QA additionally uses
`xserver-xephyr`, `x11-utils` and ImageMagick (`import` or `magick import`).
See [Drive execution evidence](../../specs/015-local-backup-and-google-drive/execution-drive.md)
for precise coverage and remaining release prerequisites.
