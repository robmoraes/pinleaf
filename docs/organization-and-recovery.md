# Organization and database recovery

This page describes the development branch's Shared feature. Published 0.8.0
uses General and schema 5. Shared is not yet released.

Every live profile has one permanent Shared (Compartilhado in pt-BR). Each note
belongs to one group. Profiles organize local data, with no separate accounts
or permissions. The initial profile name is localized once and can be renamed;
custom names remain unchanged when switching language.

The title selects a profile and resumes its last ordinary group, which may be
absent. Shared's open notes appear with the project's open notes. **Activate**
changes the ordinary group; Shared has no activation control. Its **+** creates
there without switching context. Normal New and tray creation target the active
ordinary group, falling back to Shared. New profiles contain only Shared.

Switching projects reuses shared editors. Switching profiles removes the old
profile's windows without marking them hidden. Hidden notes stay crossed through
until explicit Open. Moves preserve note metadata and do not activate groups.
Search defaults to **Current context** (Shared plus the project, or Shared alone),
with Current profile and All profiles available. A foreign Shared result offers
**Switch profile and open**, restoring its owner's remembered ordinary context.

Deleting a profile includes all its groups. Transfer moves live and retained
deleted notes to one external destination without reviving deleted rows. Delete
all uses existing soft deletion, including hidden notes. Container tombstones
remain; no trash or purge UI is provided. Removing an active ordinary group
leaves Shared only. Removing an active profile with transfer activates an ordinary
destination, or resumes the Shared destination's profile and remembered context.
Delete all or an empty profile requires a replacement profile. Shared is protected
independently and the last profile cannot be removed. Changed scope, destination
or replacement context requires a new confirmation.

## Upgrade

Opening a known schema-1..5 library first creates a validated SQLite snapshot in
`backups/` beside `pinleaf.sqlite3`. The directory is private (0700), files are
private (0600), and filenames include the source version, UTC time and a unique
suffix. They are not uploaded or automatically pruned.

The upgrade to schema 6 is one transaction. Each live schema-5 General converts
to Shared without changing group IDs, note memberships or any note/settings
values. Valid ordinary contexts remain; General context references become null.
Earlier libraries enter Personal / Shared (Pessoal / Compartilhado in pt-BR).
Ordinary Shared/Compartilhado collisions receive the first free numeric suffix,
starting at (2), with IDs and notes preserved. A dismissible panel notice explains
the change and any renames. Deleted profiles and group tombstones remain intact.

A backup, validation or commit failure aborts the upgrade. Newer or malformed
databases are refused rather than replaced. Stale context metadata is repaired
to an available profile and null ordinary context, or its valid remembered
context when the original profile is gone. Missing memberships or Shared groups
are integrity failures; Pinleaf does not silently replace the library.

## Return to an older version

Published 0.8.0 (schema 5) refuses schema 6. There is no in-place downgrade. A
snapshot restore returns the library to the snapshot's point in time; later
notes and edits will be absent from that restored view. Keep the newer database
and its SQLite sidecars separately so that work can be recovered using a
compatible newer binary on a copy.

1. Quit Pinleaf completely, including its tray process, before touching files.
   Do not restore while another process can write the database.
2. Locate the configured data directory: normally
   `${XDG_DATA_HOME:-$HOME/.local/share}/pinleaf`. Select the correct pre-upgrade
   `backups/pinleaf-schema-v5-…sqlite3` snapshot (or a supported earlier version).
3. Validate the selected snapshot without opening it for writes:

   ```bash
   /usr/bin/python3 - /absolute/path/to/selected-snapshot.sqlite3 <<'PY'
   import sqlite3, sys
   from pathlib import Path
   uri = Path(sys.argv[1]).resolve().as_uri() + '?mode=ro'
   with sqlite3.connect(uri, uri=True) as connection:
       assert connection.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
       rows = connection.execute('SELECT version FROM schema_version').fetchall()
       assert len(rows) == 1 and rows[0][0] in (1, 2, 3, 4, 5)
       print('Validated source schema:', rows[0][0])
   PY
   ```

4. Create a new private recovery directory. Move the **current** database and
   every present sidecar (`pinleaf.sqlite3-wal`, `pinleaf.sqlite3-shm`,
   `pinleaf.sqlite3-journal`) into it together. Preserve their names and contents;
   do not delete them or mix them with the snapshot.
5. Copy the validated snapshot to the original `pinleaf.sqlite3` path, preserving
   private permissions. Leave the snapshot in `backups/`. Only the restored
   database should now occupy the original path, with no newer sidecars beside it.
6. Start the compatible older binary. Check the expected notes. Keep the newer
   recovery directory and snapshots until their retention is deliberately decided.

The isolated drill in `tests/migration_recovery.py` checks refusal by the actual
`v0.8.0` migrator, exact snapshot restoration and recovery of newer work from a
preserved real WAL set. It uses temporary synthetic libraries only. Run:

```bash
/usr/bin/python3 tests/migration_recovery.py
```

Results and native qualification are in the [Shared execution record](../specs/013-general-to-shared/execution.md).
