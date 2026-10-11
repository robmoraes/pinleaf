from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from organization_fixtures import legacy_database
from pinleaf.organization import name_key
from pinleaf.storage import migrations
from pinleaf.storage.backup import database_values
from pinleaf.storage.sqlite_store import NoteStore


def schema_five(path: Path, *, active_general: bool = True) -> str:
    """Build the retained, original v5 DDL rather than downgrading a v6 DB."""
    legacy_database(path, 4)
    with sqlite3.connect(path) as connection:
        migrations._migrate_v4_to_v5(connection)
        connection.execute("UPDATE schema_version SET version=5")
        profile = connection.execute("SELECT id FROM profiles").fetchone()[0]
        for identifier, name in (("project", "Kubernetes"), ("collision", "Shared"),
                                 ("occupied", "Shared (2)"), ("portuguese", "Compartilhado")):
            connection.execute("INSERT INTO groups VALUES (?,?,?,?,0,NULL)",
                               (identifier, profile, name, name_key(name)))
        connection.execute("INSERT INTO profiles VALUES ('other','Freelancer','freelancer',NULL)")
        connection.execute("INSERT INTO groups VALUES ('other-general','other','General','general',1,NULL)")
        connection.execute("INSERT INTO groups VALUES ('other-project','other','Docker','docker',0,NULL)")
        connection.execute("INSERT INTO profile_context VALUES ('other','other-project')")
        connection.execute("INSERT INTO profiles VALUES ('deleted','Old','old','2026-01-01')")
        connection.execute("INSERT INTO groups VALUES ('deleted-general','deleted','General','general',1,'2026-01-01')")
        connection.execute("UPDATE notes SET group_id='project' WHERE id='legacy-1'")
        connection.execute("UPDATE notes SET group_id='collision' WHERE id='legacy-2'")
        if not active_general:
            connection.execute("UPDATE active_context SET group_id='project'")
            connection.execute("UPDATE profile_context SET last_group_id='project' WHERE profile_id=?", (profile,))
    return profile


class SharedMigrationTests(unittest.TestCase):
    def test_schema_five_preserves_every_note_and_setting_and_converts_ids_in_place(self):
        for active_general in (True, False):
            with self.subTest(active_general=active_general), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "notes.sqlite3"
                profile = schema_five(path, active_general=active_general)
                with sqlite3.connect(path) as source:
                    notes = tuple(source.execute("SELECT * FROM notes ORDER BY id"))
                    settings = tuple(source.execute("SELECT * FROM app_settings ORDER BY key"))
                    general_id = source.execute("SELECT id FROM groups WHERE profile_id=? AND is_general=1", (profile,)).fetchone()[0]
                    deleted = tuple(source.execute("SELECT * FROM groups WHERE profile_id='deleted'"))
                store = NoteStore(path)
                self.assertEqual(tuple(tuple(r) for r in store.connection.execute("SELECT * FROM notes ORDER BY id")), notes)
                self.assertEqual(tuple(tuple(r) for r in store.connection.execute("SELECT * FROM app_settings ORDER BY key")), settings)
                self.assertEqual(store.organization.shared(profile).id, general_id)
                self.assertEqual(store.organization.context().identity, (profile, None if active_general else "project"))
                self.assertEqual(store.organization.last_group("other").id, "other-project")
                self.assertEqual(tuple(tuple(r) for r in store.connection.execute("SELECT * FROM groups WHERE profile_id='deleted'")), deleted)
                self.assertEqual(store.connection.execute("SELECT COUNT(*) FROM groups").fetchone()[0], 8)
                self.assertIsNone(store.connection.execute("PRAGMA foreign_key_check").fetchone())
                store.close()

    def test_collisions_notice_snapshot_and_repeat_startup(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notes.sqlite3"
            profile = schema_five(path)
            store = NoteStore(path)
            self.assertEqual(store.organization.get_group("collision").name, "Shared (3)")
            self.assertEqual(store.organization.get_group("portuguese").name, "Compartilhado (2)")
            notice = store.migration_notice()
            self.assertEqual(len(notice["renames"]), 2)
            self.assertEqual(store.organization.shared(profile).name, "Shared")
            before = database_values(store.connection)
            store.close()
            backups = list((path.parent / "backups").glob("*.sqlite3"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].stat().st_mode & 0o777, 0o600)
            with sqlite3.connect(backups[0]) as snapshot:
                self.assertEqual(snapshot.execute("SELECT version FROM schema_version").fetchone()[0], 5)
                self.assertEqual(snapshot.execute("SELECT name FROM groups WHERE id='collision'").fetchone()[0], "Shared")
            store = NoteStore(path)
            self.assertEqual(database_values(store.connection), before)
            self.assertEqual(len(list((path.parent / "backups").glob("*.sqlite3"))), 1)
            store.dismiss_migration_notice()
            store.close()
            store = NoteStore(path)
            self.assertIsNone(store.migration_notice())
            store.close()

    def test_conversion_failure_and_version_failure_roll_back_exact_source(self):
        for failure in ("after-conversion", "version"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "notes.sqlite3"
                schema_five(path)
                connection = sqlite3.connect(path)
                before = database_values(connection)
                original = migrations._migrate_v5_to_v6
                def convert(db, **kwargs):
                    original(db, **kwargs)
                    if failure == "after-conversion":
                        raise OSError("Injected failure")
                if failure == "version":
                    connection.set_authorizer(lambda action, table, *_: sqlite3.SQLITE_DENY
                        if action == sqlite3.SQLITE_UPDATE and table == "schema_version" else sqlite3.SQLITE_OK)
                with patch.object(migrations, "_migrate_v5_to_v6", convert):
                    with self.assertRaises((OSError, sqlite3.DatabaseError)):
                        migrations.migrate(connection)
                connection.set_authorizer(None)
                self.assertEqual(database_values(connection), before)
                connection.close()

    def test_process_interruption_during_conversion_leaves_schema_five(self):
        import subprocess
        import sys

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notes.sqlite3"
            schema_five(path)
            with sqlite3.connect(path) as source:
                before = database_values(source)
            script = """import os, sys
from pinleaf.storage import migrations
from pinleaf.storage.sqlite_store import NoteStore
original = migrations._migrate_v5_to_v6
def stop(connection, **kwargs):
    original(connection, **kwargs)
    os._exit(17)
migrations._migrate_v5_to_v6 = stop
NoteStore(sys.argv[1])
"""
            result = subprocess.run([sys.executable, "-c", script, str(path)], check=False)
            self.assertEqual(result.returncode, 17)
            with sqlite3.connect(path) as source:
                self.assertEqual(database_values(source), before)

    def test_stale_general_or_ordinary_context_references_become_null(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notes.sqlite3"
            profile = schema_five(path, active_general=False)
            with sqlite3.connect(path) as source:
                source.execute("UPDATE notes SET deleted_at='2026-01-01' WHERE group_id='project'")
                source.execute("UPDATE groups SET deleted_at='2026-01-01' WHERE id='project'")
            store = NoteStore(path)
            self.assertEqual(store.organization.context().identity, (profile, None))
            self.assertIsNone(store.organization.last_group(profile))
            store.close()

    def test_schema_five_backup_failure_preserves_exact_source(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notes.sqlite3"
            schema_five(path)
            with sqlite3.connect(path) as source:
                before = database_values(source)
            with patch.object(migrations, "create_snapshot", side_effect=OSError("backup denied")):
                with self.assertRaises(OSError):
                    NoteStore(path)
            with sqlite3.connect(path) as source:
                self.assertEqual(database_values(source), before)
