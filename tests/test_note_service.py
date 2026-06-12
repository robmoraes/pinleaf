from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pinleaf.models import NoteColor
from pinleaf.services.note_service import NoteService
from pinleaf.storage.sqlite_store import NoteStore


class NoteServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = NoteStore(Path(self.tmp.name) / "pinleaf.sqlite3")
        self.times = iter(
            [
                "2026-06-12T00:00:00+00:00",
                "2026-06-12T01:00:00+00:00",
                "2026-06-12T02:00:00+00:00",
                "2026-06-12T03:00:00+00:00",
                "2026-06-12T04:00:00+00:00",
            ]
        )
        self.service = NoteService(
            self.store,
            id_factory=lambda: "note-1",
            clock=lambda: next(self.times),
        )

    def tearDown(self) -> None:
        self.store.close()
        self.tmp.cleanup()

    def test_create_edit_close_reopen_and_delete_note(self) -> None:
        note = self.service.create_note()
        edited = self.service.update_content(note.id, "Revisar PR")
        closed = self.service.close_note(note.id, width=360, height=240)
        reopened = self.service.reopen_note(note.id)

        self.service.delete_note(note.id)

        self.assertEqual(note.id, "note-1")
        self.assertEqual(edited.content, "Revisar PR")
        self.assertFalse(closed.is_open)
        self.assertTrue(reopened.is_open)
        self.assertEqual(self.service.list_notes(), [])

    def test_update_color(self) -> None:
        note = self.service.create_note()

        updated = self.service.update_color(note.id, "pink")

        self.assertEqual(updated.color, NoteColor.PINK)

    def test_empty_note_remains_listed_until_deleted(self) -> None:
        note = self.service.create_note()

        self.assertEqual(self.service.list_notes(), [note])


if __name__ == "__main__":
    unittest.main()
