# ADR 002: Direct Google Drive backup destination

Status: accepted for slice B planning on 2026-10-11; not implemented or configured.
Traceability: BK-01/03, GD-01–06, PR-02 in [spec](spec.md).

## Context

The maintainer wants personal portability using an existing Google account and
complete offline notes. Operating a service and reconciling concurrent edits are
outside this iteration. The local portable format is the reusable boundary.

## Decision

Connect the desktop app directly to Drive v3 through system-browser OAuth and
the narrow drive.file scope. Use explicit PKCE S256/state and a temporary local
loopback listener. The registered desktop client is configured once by the
maintainer; user refresh tokens belong only in Secret Service or session memory.
Never treat the distributed desktop client secret as a secure backend secret.

Upload the local format as distinct visible files in app-marked folders, with
pending/complete publication and attempt UUID reconciliation. Discover through
Drive, not another device's local folder/history. Downloads pass through the
same local reader and explicit replacement/recovery workflow. No remote note
edits, polling, sync pointer, automatic retries/pruning or Pinleaf account exists.
Disconnect forgets local access without revoking the project's other devices.

## Alternatives and consequences

- User-owned S3 adds bucket/credential setup; an operated S3 service adds an
  account/backend, costs and support. Both can be later destinations.
- A hidden appDataFolder would reduce direct user access to portable copies;
  visible files fit the recovery goal and the agreed reviewable default.
- Synchronizing SQLite or overwriting one latest file cannot reconcile independent
  edits safely and hides useful older recovery points.

Drive OAuth setup and two-installation access must be qualified with the
maintainer's designated account; mocks cannot establish real provider behavior.
Client distribution/consent configuration is an operational prerequisite for
slice B, not a reason to block local export/import. Testing-mode authorization
may require reconnecting after Google's refresh-token expiry. The added transport,
OAuth and SecretStorage dependencies remain isolated from local startup.

## Reference basis

Consulted 2026-10-11:
- [Google desktop OAuth](https://developers.google.com/identity/protocols/oauth2/native-app),
  [Drive scopes](https://developers.google.com/workspace/drive/api/guides/api-specific-auth)
  and [OAuth token lifecycle](https://developers.google.com/identity/protocols/oauth2).
- [InstalledAppFlow](https://google-auth-oauthlib.readthedocs.io/en/latest/reference/google_auth_oauthlib.flow.html),
  [Drive upload protocol](https://developers.google.com/workspace/drive/api/guides/manage-uploads)
  and [paginated file listing](https://developers.google.com/workspace/drive/api/reference/rest/v3/files/list).
- [SecretStorage](https://secretstorage.readthedocs.io/en/latest/) provides access
  to the desktop Secret Service; no generic plaintext credential fallback is used.
