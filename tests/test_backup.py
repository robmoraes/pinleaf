from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from organization_fixtures import legacy_database
from pinleaf.storage import backup, migrations
from pinleaf.storage.sqlite_store import NoteStore


class BackupTests(unittest.TestCase):
    def test_private_unique_independently_readable_snapshots(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notes.sqlite3"
            legacy_database(path, 4)
            connection = sqlite3.connect(path)
            before = backup.database_values(connection)
            first = backup.create_snapshot(connection, 4)
            second = backup.create_snapshot(connection, 4)
            self.assertNotEqual(first.path, second.path)
            self.assertEqual(first.path.parent.stat().st_mode & 0o777, 0o700)
            self.assertEqual(first.path.stat().st_mode & 0o777, 0o600)
            first.close()
            second.close()
            connection.close()
            with sqlite3.connect(first.path) as restored:
                self.assertEqual(backup.database_values(restored), before)

    def test_permission_failure_aborts_without_source_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notes.sqlite3"
            legacy_database(path, 4)
            with sqlite3.connect(path) as connection:
                before = backup.database_values(connection)
            with patch.object(Path, "chmod", side_effect=PermissionError("denied")):
                with self.assertRaises(PermissionError):
                    NoteStore(path)
            with sqlite3.connect(path) as connection:
                self.assertEqual(backup.database_values(connection), before)

    def test_integrity_and_version_validation_close_failed_snapshot(self) -> None:
        real_connect = sqlite3.connect
        targets = []
        for failure in ("integrity", "version"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "notes.sqlite3"
                legacy_database(path, 4)
                connection = real_connect(path)

                class InvalidSnapshot(sqlite3.Connection):
                    def execute(self, statement, *args, **kwargs):
                        if failure == "integrity" and statement == "PRAGMA integrity_check":
                            statement = "SELECT 'invalid'"
                        elif failure == "version" and statement == "SELECT version FROM schema_version":
                            statement = "SELECT 99"
                        return super().execute(statement, *args, **kwargs)

                def target_connect(*args, **kwargs):
                    target = real_connect(*args, **kwargs, factory=InvalidSnapshot)
                    targets.append(target)
                    return target
                before = backup.database_values(connection)
                with patch.object(backup.sqlite3, "connect", side_effect=target_connect):
                    with self.assertRaises(RuntimeError):
                        backup.create_snapshot(connection, 4)
                self.assertEqual(backup.database_values(connection), before)
                with self.assertRaises(sqlite3.ProgrammingError):
                    targets[-1].execute("SELECT 1")
                connection.close()

    def test_competing_writer_requires_a_new_snapshot_before_upgrade(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notes.sqlite3"
            legacy_database(path, 4)
            original = backup.create_snapshot

            def competing_writer(connection, version):
                snapshot = original(connection, version)
                with sqlite3.connect(path) as writer:
                    writer.execute("UPDATE notes SET width=777 WHERE id='legacy-0'")
                return snapshot

            with patch.object(migrations, "create_snapshot", side_effect=competing_writer):
                with self.assertRaisesRegex(RuntimeError, "changed during backup"):
                    NoteStore(path)
            with sqlite3.connect(path) as connection:
                self.assertEqual(connection.execute("SELECT version FROM schema_version").fetchone()[0], 4)
                self.assertEqual(connection.execute("SELECT width FROM notes WHERE id='legacy-0'").fetchone()[0], 777)
                self.assertEqual({row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")},
                                 {"schema_version", "notes", "app_settings"})
