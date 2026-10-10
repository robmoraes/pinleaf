# Organization and database recovery

Profiles contain groups; each note belongs to one group. A profile's permanent
General group is labeled Geral in pt-BR. The initial profile name is localized
once and can be renamed; user-created names do not change with the language.
Profiles organize local data and do not provide separate accounts or permissions.

The panel title selects a profile and restores its last active group. Expand
sections to browse; **Activate** changes which group's open notes appear on the
desktop. Context switches preserve individual hidden/open state. Hidden notes
stay crossed through until an explicit **Open** or **Activate and open** action.
Create and activate explicitly switches context. Moving a note keeps the active
group and all note properties; an open note entering that group appears there.

Search defaults to the active group, with current-profile and all-profile scopes.
External results show their destination and require **Activate and open**.
Clearing search restores the previous expansion; switching context clears the
query. Organization labels stay in the panel, leaving sticky notes unchanged.

Deleting a profile covers all its groups. Choose transfer to one existing
external group or deletion of every live note, including hidden notes. Transfer
also moves retained deleted rows without reviving them. Deletion uses the
existing soft-deletion policy; removed containers remain as internal tombstones.
There is no trash, restore or permanent-purge UI in this version.

Deleting the active group selects General in that profile. Deleting the active
profile with transfer selects the destination group; deletion of its notes or
an empty profile requires selecting a remaining profile to resume. Removing an
inactive container keeps the current context. General is protected independently
and the last profile cannot be removed. A changed deletion scope or destination
requires a new review before confirmation.

## Upgrade

Opening a known schema-1..4 library first creates a validated SQLite snapshot in
`backups/` beside `pinleaf.sqlite3`. The directory is private (0700), files are
private (0600), and filenames include the source version, UTC time and a unique
suffix. They are not uploaded or automatically pruned.

The upgrade to schema 5 is one transaction. All retained notes enter Personal /
General (Pessoal / Geral in pt-BR); original values and settings are preserved.
A backup, validation or commit failure aborts the upgrade. Newer or malformed
databases are refused rather than replaced. Invalid saved context metadata can
be repaired to an existing General group; missing memberships or General groups
are treated as integrity failures.

## Return to an older version

An older schema-4 binary refuses schema 5. There is no in-place downgrade. A
snapshot restore returns the library to the snapshot's point in time; later
notes and edits will be absent from that restored view. Keep the newer database
and its SQLite sidecars separately so that work can be recovered using a
compatible newer binary on a copy.

1. Quit Pinleaf completely, including its tray process, before touching files.
   Do not restore while another process can write the database.
2. Locate the configured data directory: normally
   `${XDG_DATA_HOME:-$HOME/.local/share}/pinleaf`. Select the correct pre-upgrade
   `backups/pinleaf-schema-v4-…sqlite3` snapshot (or a supported earlier version).
3. Validate the selected snapshot without opening it for writes:

   ```bash
   /usr/bin/python3 - /absolute/path/to/selected-snapshot.sqlite3 <<'PY'
   import sqlite3, sys
   from pathlib import Path
   uri = Path(sys.argv[1]).resolve().as_uri() + '?mode=ro'
   with sqlite3.connect(uri, uri=True) as connection:
       assert connection.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
       rows = connection.execute('SELECT version FROM schema_version').fetchall()
       assert len(rows) == 1 and rows[0][0] in (1, 2, 3, 4)
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

The isolated drill in `tests/migration_recovery.py` checks refusal by the
`v0.7.0` migrator, exact snapshot restoration and recovery of newer work from a
preserved real WAL set. It uses temporary synthetic libraries only. Execution
results are recorded in the [feature evidence](.specs/011-profiles-and-groups/execution-2026-10-10.md).
