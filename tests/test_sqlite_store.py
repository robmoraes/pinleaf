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
            columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(notes)").fetchall()
            }
        finally:
            connection.close()

        self.assertIn("schema_version", tables)
        self.assertIn("notes", tables)
        self.assertIn("app_settings", tables)
        self.assertIn("idx_notes_deleted_updated", indexes)
        self.assertIn("font_family", columns)
        self.assertEqual(version, CURRENT_SCHEMA_VERSION)

    def test_create_get_and_list_note(self) -> None:
        note = Note.new("note-1", now="2026-06-12T00:00:00+00:00")

        self.store.create(note)

        self.assertEqual(self.store.get("note-1"), note)
        self.assertEqual(self.store.list_notes(), [note])

    def test_list_notes_orders_by_created_at_descending(self) -> None:
        older = Note.new("note-1", now="2026-06-12T00:00:00+00:00")
        newer = Note.new("note-2", now="2026-06-12T01:00:00+00:00")
        self.store.create(older)
        self.store.create(newer)

        self.store.update_content(
            older.id,
            "Updated after newer note was created",
            now="2026-06-12T02:00:00+00:00",
        )

        self.assertEqual(
            [note.id for note in self.store.list_notes()],
            ["note-2", "note-1"],
        )

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

    def test_update_font_family(self) -> None:
        self.store.create(Note.new("note-1", now="2026-06-12T00:00:00+00:00"))

        updated = self.store.update_font_family(
            "note-1",
            "Dancing Script",
            now="2026-06-12T01:00:00+00:00",
        )
        reset = self.store.update_font_family(
            "note-1",
            "Unsupported Font",
            now="2026-06-12T02:00:00+00:00",
        )

        self.assertEqual(updated.font_family, "Dancing Script")
        self.assertIsNone(reset.font_family)

    def test_default_font_family_persists_supported_font(self) -> None:
        saved = self.store.set_default_font_family("Kavoon")

        self.assertEqual(saved, "Kavoon")
        self.assertEqual(self.store.get_default_font_family(), "Kavoon")

        self.store.close()
        self.store = NoteStore(self.database_path)

        self.assertEqual(self.store.get_default_font_family(), "Kavoon")

    def test_default_font_family_normalizes_unsupported_font(self) -> None:
        saved = self.store.set_default_font_family("Unsupported Font")

        self.assertIsNone(saved)
        self.assertIsNone(self.store.get_default_font_family())

    def test_default_text_appearance_persists_all_fields(self) -> None:
        saved = self.store.set_default_text_appearance(
            font_family="Kavoon",
            font_size=24,
            text_color="#123abc",
        )

        self.assertEqual(saved.font_family, "Kavoon")
        self.assertEqual(saved.font_size, 24)
        self.assertEqual(saved.text_color, "#123ABC")

        self.store.close()
        self.store = NoteStore(self.database_path)

        loaded = self.store.get_default_text_appearance()
        self.assertEqual(loaded.font_family, "Kavoon")
        self.assertEqual(loaded.font_size, 24)
        self.assertEqual(loaded.text_color, "#123ABC")

    def test_default_text_appearance_normalizes_unsupported_values(self) -> None:
        saved = self.store.set_default_text_appearance(
            font_family="Unsupported Font",
            font_size=100,
            text_color="blue",
        )

        self.assertIsNone(saved.font_family)
        self.assertEqual(saved.font_size, 72)
        self.assertEqual(saved.text_color, "#005BAC")

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

    def test_migrates_version_1_database_to_current_schema(self) -> None:
        self.store.close()
        connection = sqlite3.connect(self.database_path)
        try:
            connection.execute("DROP TABLE notes")
            connection.execute("DROP TABLE schema_version")
            connection.execute(
                """
                CREATE TABLE schema_version (
                  version INTEGER NOT NULL
                )
                """
            )
            connection.execute("INSERT INTO schema_version (version) VALUES (1)")
            connection.execute(
                """
                CREATE TABLE notes (
                  id TEXT PRIMARY KEY,
                  content TEXT NOT NULL DEFAULT '',
                  color TEXT NOT NULL,
                  width INTEGER NOT NULL,
                  height INTEGER NOT NULL,
                  position_x INTEGER,
                  position_y INTEGER,
                  is_open INTEGER NOT NULL DEFAULT 1,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL,
                  deleted_at TEXT
                )
                """
            )
            connection.execute(
                """
                INSERT INTO notes (
                  id, content, color, width, height, position_x, position_y,
                  is_open, created_at, updated_at, deleted_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "note-1",
                    "Legacy",
                    "yellow",
                    320,
                    280,
                    None,
                    None,
                    1,
                    "2026-06-12T00:00:00+00:00",
                    "2026-06-12T00:00:00+00:00",
                    None,
                ),
            )
            connection.commit()
        finally:
            connection.close()

        self.store = NoteStore(self.database_path)

        note = self.store.get("note-1")
        self.assertIsNotNone(note)
        assert note is not None
        self.assertIsNone(note.font_family)
        tables = {
            row[0]
            for row in self.store.connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        self.assertIn("app_settings", tables)
        version = self.store.connection.execute("SELECT version FROM schema_version").fetchone()[0]
        self.assertEqual(version, CURRENT_SCHEMA_VERSION)


if __name__ == "__main__":
    unittest.main()
