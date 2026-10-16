# Execution: local backup and restore

Date: 2026-10-11 (America/Sao_Paulo). Delivery boundary: slice A only,
on `feat/shared-groups-and-remote-backup`. Application version stays 0.8.0 and
SQLite schema stays 6. No push, remote PR edit, release or Google access.
All data/passwords were synthetic and all libraries disposable. Daily-use
application data and credentials were not used.

## Results and reproducibility

- Full regression: **214 tests passed**, 18.067 seconds, isolated native X11;
  includes GTK tests with no display-related skips.
- Format/storage/recovery: 26 focused tests, including both protection modes,
  all nine contract files, strict parsing/limits, all 15 note fields, legacy
  null appearance, deleted owners, missing fonts, duplicate IDs/ownership,
  offline operation, immutable preview and multiple independent installations.
- Process recovery: forced `os._exit` in fresh disposable processes at six
  logical boundaries (validated stage, recovery file, journal, uncommitted rows,
  committed rows, reconciliation), seven damaged-source installation boundaries
  and five original-file fallback boundaries. Restart selects complete old/new
  data or restores the exact original file set. Corrupt/unmatched journals
  block empty-library seeding.
- Filesystem faults: failed validation/preservation, cancelled preparation,
  stale current data, no-clobber publication, failed directory fsync/rollback,
  transaction rollback and damaged optional status. Previous destination or
  explicit recovery paths survive; failed preparation can be retried.
- Native real-app GTK: chooser cancellation, password mismatch/wrong password,
  password-free/default-off creation, protected creation, preview cancellation,
  default-Cancel destructive confirmation, edits after preview in recovery,
  matching note IDs with new editors, delayed autosave/panel/tray callbacks,
  hidden state, missing-font fallback, Escape/focus, reopen, light/dark/narrow
  layouts, helper cleanup. Healthy small and 1,000-note fixtures plus startup
  failure with byte-preserved database/WAL were executed.
- Real AT-SPI: create/restore buttons, protection checkbox, both password fields,
  Cancel and Choose Location expose names, roles and focusable state through a
  separate process on a private accessibility bus. This does not qualify Orca
  speech or human usability.
- Debian binary built locally in `/tmp` with `dpkg-buildpackage -us -uc -b`.
  Both JSON schema resources and runtime dependencies were inspected in the
  resulting package. It was neither installed nor published.

Commands from the repository root:

```bash
/usr/bin/python3 tests/gui_session.py /usr/bin/python3 -m unittest discover -s tests
/usr/bin/python3 tests/gui_session.py /usr/bin/python3 tests/gui_backup.py
/usr/bin/python3 tests/gui_session.py /usr/bin/python3 tests/gui_backup.py --large
/usr/bin/python3 tests/gui_session.py /usr/bin/python3 tests/gui_backup.py --corrupt
/usr/bin/python3 tests/gui_session.py --a11y /usr/bin/python3 tests/gui_backup_accessibility.py
/usr/bin/python3 specs/015-local-backup-and-google-drive/contracts/validate_examples.py
/usr/bin/python3 -m compileall pinleaf tests
git diff --check
```

## Performance sample

One 1,000-note, approximately 539-KB logical fixture, native system Python;
single samples, not a statistical benchmark or a platform promise:

| Operation | Unprotected | Protected |
| --- | ---: | ---: |
| Encode | 175.93 ms | 435.44 ms |
| Decode | 173.19 ms | 489.83 ms |
| Trusted SQLite staging | 232.89 ms | 235.94 ms |
| Commit and reconciliation | 116.19 ms | 113.30 ms |
| File size | 538,511 bytes | 718,034 bytes |

Recovery creation was 4.08 ms for the initial empty library and 332.39 ms for
the already restored 1,000-note library; these inputs differ and are not a
protection comparison. Encode/decode/staging/recovery I/O execute on a worker.
Commit and UI recreation run on the main thread. The 1,000-note native workflow
observed six regular GTK timer callbacks during worker jobs in the final run.

## Screenshots

Only this disposable test application's windows were captured:

- [Local window](screenshots/local-backups-light.png)
- [Optional protection](screenshots/create-protected-light.png)
- [Validated preview](screenshots/restore-preview-light.png)
- [Final confirmation](screenshots/restore-confirmation-light.png)
- [Narrow dark layout](screenshots/local-backups-narrow-dark.png)
- [Startup-error preview](screenshots/startup-restore-preview.png)
- [Startup-error completion](screenshots/startup-restore-complete.png)

## Limits and next slice

Google Drive D01–D05 have not been implemented: there is no OAuth client,
connection, credential persistence, Drive list/upload/download or network call
in this slice. Real provider qualification needs a registered desktop client
and an explicitly designated test account/consent.

Wayland positioning and Orca speech were not qualified. Existing geometry/font
fallbacks remain the presentation boundary. No physical power-loss/storage-device
failure was simulated; process termination and filesystem fault injection are
the measured recovery evidence. Local recovery copies are deliberately
unprotected inside private 0700 directories with 0600 files, as planned.

Implementation findings reconciled with the plan/contracts: raw legacy null
appearance must remain null; a read-only preflight is needed before opening a
damaged SQLite library writable; damaged-source fallback must be repeatable even
if a verified stage later disappears. No new product behavior was added.
