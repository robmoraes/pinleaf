# Cloud Sync Ideas

## Purpose

Capture early thinking for cloud persistence and multi-device sync without
committing the current MVP to an account or backend architecture.

## Candidate Experience

The user can run Pinleaf on more than one machine and see the same notes,
including text, color and selected local preferences where appropriate.

## Possible Backends

- Maintainer-owned API.
- Google Drive integration.
- S3-compatible object storage.
- Git-backed storage for advanced users.

## Likely Requirements

- Account or credential setup.
- Device identity.
- Sync status in the UI.
- Offline-first local SQLite storage.
- Conflict detection and resolution.
- Backup/export story.

## Data Questions

- Should window position sync across machines with different displays?
- Should always-on-top sync?
- Should per-note font sync if the font may not exist on the target machine?
- Should note data be encrypted before leaving the machine?
- What is the source of truth: local-first merge or server-authoritative state?

## Security and Privacy Questions

- How are credentials stored?
- Is end-to-end encryption required?
- Can the server read note content?
- How does the user revoke a device?
- How are deleted notes handled?

## Risks

- Sync conflicts are product behavior, not just infrastructure.
- Social login introduces provider and deployment complexity.
- Cloud sync changes the trust model of a simple local notes app.
- Backend maintenance can become larger than the desktop app itself.

## Suggested Timing

Revisit after the local data model stabilizes and the app has enough daily-use
value to justify account, backend and privacy work.

