from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from organization_fixtures import legacy_database
from pinleaf.storage import migrations
from pinleaf.storage.backup import database_values
from pinleaf.storage.sqlite_store import NoteStore


class MigrationTests(unittest.TestCase):
    def test_copy_ddl_and_version_write_failures_roll_back_all_steps(self) -> None:
        for failure in ("ddl", "copy", "version"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'notes.sqlite3'
                legacy_database(path, 1)
                connection = sqlite3.connect(path)
                before = database_values(connection)
                def deny(action, first, _second, _database, _trigger):
                    blocked = ((failure == 'ddl' and action == sqlite3.SQLITE_CREATE_TABLE and first == 'groups')
                               or (failure == 'copy' and action == sqlite3.SQLITE_INSERT and first == 'notes_new')
                               or (failure == 'version' and action == sqlite3.SQLITE_UPDATE and first == 'schema_version'))
                    return sqlite3.SQLITE_DENY if blocked else sqlite3.SQLITE_OK
                connection.set_authorizer(deny)
                with self.assertRaises(sqlite3.DatabaseError):
                    migrations.migrate(connection)
                connection.set_authorizer(None)
                self.assertEqual(database_values(connection), before)
                connection.close()

    def test_process_interruption_restores_entire_source_transaction(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'notes.sqlite3'
            legacy_database(path, 1)
            with sqlite3.connect(path) as connection:
                before = database_values(connection)
            script = '''import os,sys
from pinleaf.storage import migrations
from pinleaf.storage.sqlite_store import NoteStore
original = migrations._migrate_v4_to_v5
def interrupt(connection):
    original(connection)
    os._exit(17)
migrations._migrate_v4_to_v5 = interrupt
NoteStore(sys.argv[1])
'''
            result = subprocess.run([sys.executable, '-c', script, str(path)], check=False)
            self.assertEqual(result.returncode, 17)
            with sqlite3.connect(path) as connection:
                self.assertEqual(database_values(connection), before)
                self.assertEqual(connection.execute('PRAGMA integrity_check').fetchone()[0], 'ok')

    def test_all_legacy_versions_preserve_original_values_and_backup(self) -> None:
        for version in range(1, 5):
            with self.subTest(version=version), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "pinleaf.sqlite3"
                columns, before = legacy_database(path, version)
                with patch.dict("os.environ", {"LC_ALL": "pt_BR.UTF-8"}):
                    store = NoteStore(path)
                try:
                    after = tuple(tuple(row) for row in store.connection.execute(
                        f"SELECT {','.join(columns)} FROM notes ORDER BY id"))
                    self.assertEqual(before, after)
                    self.assertEqual(store.organization.context().profile.name, "Pessoal")
                    self.assertEqual(store.connection.execute("SELECT COUNT(DISTINCT group_id) FROM notes").fetchone()[0], 1)
                    self.assertEqual(store.connection.execute("PRAGMA foreign_key_check").fetchall(), [])
                    if version >= 3:
                        self.assertEqual(store.get_default_font_family(), "Kavoon")
                    backups = list((Path(directory) / "backups").glob('*.sqlite3'))
                    self.assertEqual(len(backups), 1)
                    self.assertEqual(backups[0].stat().st_mode & 0o777, 0o600)
                    backup = sqlite3.connect(backups[0])
                    self.assertEqual(backup.execute("SELECT version FROM schema_version").fetchone()[0], version)
                    self.assertEqual(tuple(backup.execute("SELECT * FROM notes ORDER BY id")), before)
                    backup.close()
                finally:
                    store.close()
                reopened = NoteStore(path)
                reopened.close()
                self.assertEqual(len(list((Path(directory) / "backups").glob('*.sqlite3'))), 1)

    def test_failure_after_rebuild_rolls_back_schema_and_data(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'pinleaf.sqlite3'
            legacy_database(path, 1)
            connection = sqlite3.connect(path)
            before = database_values(connection)
            connection.close()
            original = migrations._migrate_v4_to_v5
            def fail(connection):
                original(connection)
                raise RuntimeError('injected failure')
            with patch.object(migrations, '_migrate_v4_to_v5', side_effect=fail):
                with self.assertRaises(RuntimeError):
                    NoteStore(path)
            connection = sqlite3.connect(path)
            self.assertEqual(database_values(connection), before)
            connection.close()

    def test_backup_failure_and_newer_schema_do_not_mutate(self) -> None:
        for failure in ('backup', 'newer', 'unversioned'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'pinleaf.sqlite3'
                legacy_database(path, 4)
                connection = sqlite3.connect(path)
                if failure == 'newer':
                    connection.execute('UPDATE schema_version SET version=99')
                elif failure == 'unversioned':
                    connection.execute('DROP TABLE schema_version')
                connection.commit()
                before = database_values(connection)
                connection.close()
                with patch.object(migrations, 'create_snapshot', side_effect=OSError('backup denied')):
                    with self.assertRaises((RuntimeError, OSError)):
                        NoteStore(path)
                connection = sqlite3.connect(path)
                self.assertEqual(database_values(connection), before)
                connection.close()

    def test_machine_readable_contract_matches_schema(self) -> None:
        root = Path(__file__).resolve().parents[1]
        contract = json.loads((root / 'docs/.specs/011-profiles-and-groups/contracts/migration-v5.json').read_text())
        store = NoteStore(':memory:')
        try:
            self.assertEqual(contract['target_schema_version'], migrations.CURRENT_SCHEMA_VERSION)
            for table, definition in contract['schema'].items():
                info = store.connection.execute(f'PRAGMA table_info({table})').fetchall()
                columns = {row['name'] for row in info}
                self.assertTrue(set(definition.get('required_columns', [])) <= columns)
            columns = {row['name'] for row in store.connection.execute('PRAGMA table_info(notes)')}
            self.assertEqual(columns - {'group_id'}, set(contract['preservation']['existing_note_columns']))
            membership = next(row for row in store.connection.execute('PRAGMA table_info(notes)') if row['name'] == 'group_id')
            self.assertEqual(membership['notnull'], 1)
        finally:
            store.close()
