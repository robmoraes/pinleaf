from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from pinleaf.models import Note, NoteColor
from pinleaf.storage.migrations import CURRENT_SCHEMA_VERSION
from pinleaf.storage.sqlite_store import NoteStore


class SQLiteStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.database_path = Path(self.tmp.name) / "pinleaf.sqlite3"
        self.store = NoteStore(self.database_path)

    def tearDown(self) -> None:
        self.store.close()
        self.tmp.cleanup()

    def test_migration_creates_expected_schema(self) -> None:
        connection = sqlite3.connect(self.database_path)
        try:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            indexes = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'index'"
                )
            }
            version = connection.execute("SELECT version FROM schema_version").fetchone()[0]
        finally:
            connection.close()

        self.assertIn("schema_version", tables)
        self.assertIn("notes", tables)
        self.assertIn("idx_notes_deleted_updated", indexes)
        self.assertEqual(version, CURRENT_SCHEMA_VERSION)

    def test_create_get_and_list_note(self) -> None:
        note = Note.new("note-1", now="2026-06-12T00:00:00+00:00")

        self.store.create(note)

        self.assertEqual(self.store.get("note-1"), note)
        self.assertEqual(self.store.list_notes(), [note])

    def test_update_content_and_color(self) -> None:
        self.store.create(Note.new("note-1", now="2026-06-12T00:00:00+00:00"))

        updated = self.store.update_content(
            "note-1",
            "Comprar cafe",
            now="2026-06-12T01:00:00+00:00",
        )
        recolored = self.store.update_color(
            "note-1",
            "blue",
            now="2026-06-12T02:00:00+00:00",
        )

        self.assertEqual(updated.content, "Comprar cafe")
        self.assertEqual(recolored.color, NoteColor.BLUE)
        self.assertEqual(recolored.updated_at, "2026-06-12T02:00:00+00:00")

    def test_update_window_state(self) -> None:
        self.store.create(Note.new("note-1", now="2026-06-12T00:00:00+00:00"))

        note = self.store.update_window_state(
            "note-1",
            width=400,
            height=300,
            position_x=10,
            position_y=20,
            is_open=False,
            now="2026-06-12T01:00:00+00:00",
        )

        self.assertEqual(note.width, 400)
        self.assertEqual(note.height, 300)
        self.assertEqual(note.position_x, 10)
        self.assertEqual(note.position_y, 20)
        self.assertFalse(note.is_open)

    def test_soft_delete_hides_note_from_normal_reads(self) -> None:
        self.store.create(Note.new("note-1", now="2026-06-12T00:00:00+00:00"))

        self.store.soft_delete("note-1", now="2026-06-12T01:00:00+00:00")

        self.assertIsNone(self.store.get("note-1"))
        self.assertEqual(self.store.list_notes(), [])


if __name__ == "__main__":
    unittest.main()
