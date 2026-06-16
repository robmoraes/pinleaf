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

    def test_update_font_family(self) -> None:
        note = self.service.create_note()

        updated = self.service.update_font_family(note.id, "Dancing Script")
        reset = self.service.update_font_family(note.id, None)

        self.assertEqual(updated.font_family, "Dancing Script")
        self.assertIsNone(reset.font_family)

    def test_create_note_uses_default_font_family(self) -> None:
        self.service.set_default_font_family("Kavoon")

        note = self.service.create_note()

        self.assertEqual(note.font_family, "Kavoon")

    def test_create_note_uses_default_text_appearance(self) -> None:
        self.service.set_default_text_appearance(
            font_family="Kavoon",
            font_size=24,
            text_color="#123abc",
        )

        note = self.service.create_note()
        appearance = self.service.get_default_text_appearance()

        self.assertEqual(note.font_family, "Kavoon")
        self.assertEqual(note.font_size, 24)
        self.assertEqual(note.text_color, "#123ABC")
        self.assertEqual(appearance.font_size, 24)
        self.assertEqual(appearance.text_color, "#123ABC")

    def test_update_text_appearance(self) -> None:
        note = self.service.create_note()

        updated = self.service.update_text_appearance(
            note.id,
            font_family="Kavoon",
            font_size=24,
            text_color="#123abc",
        )

        self.assertEqual(updated.font_family, "Kavoon")
        self.assertEqual(updated.font_size, 24)
        self.assertEqual(updated.text_color, "#123ABC")

    def test_individual_note_font_is_independent_from_default_font(self) -> None:
        self.service.set_default_font_family("Dancing Script")
        note = self.service.create_note()

        updated = self.service.update_font_family(note.id, "monospace")
        self.service.set_default_font_family("Kavoon")

        current = self.service.get_note(note.id)
        self.assertEqual(updated.font_family, "monospace")
        self.assertIsNotNone(current)
        assert current is not None
        self.assertEqual(current.font_family, "monospace")
        self.assertEqual(self.service.get_default_font_family(), "Kavoon")

    def test_save_open_note_window_preserves_open_state_and_geometry(self) -> None:
        note = self.service.create_note()

        updated = self.service.save_open_note_window(
            note.id,
            width=500,
            height=350,
            position_x=12,
            position_y=24,
        )

        self.assertTrue(updated.is_open)
        self.assertEqual(updated.width, 500)
        self.assertEqual(updated.height, 350)
        self.assertEqual(updated.position_x, 12)
        self.assertEqual(updated.position_y, 24)

    def test_empty_note_remains_listed_until_deleted(self) -> None:
        note = self.service.create_note()

        self.assertEqual(self.service.list_notes(), [note])


if __name__ == "__main__":
    unittest.main()
