from __future__ import annotations

import unittest

from pinleaf.appearance import DEFAULT_FONT_SIZE, DEFAULT_TEXT_COLOR
from pinleaf.models import DEFAULT_HEIGHT, DEFAULT_WIDTH, Note, NoteColor, validate_color


class ModelTests(unittest.TestCase):
    def test_new_note_defaults(self) -> None:
        note = Note.new("note-1", now="2026-06-12T00:00:00+00:00")

        self.assertEqual(note.id, "note-1")
        self.assertEqual(note.content, "")
        self.assertEqual(note.color, NoteColor.YELLOW)
        self.assertEqual(note.width, DEFAULT_WIDTH)
        self.assertEqual(note.height, DEFAULT_HEIGHT)
        self.assertIsNone(note.position_x)
        self.assertIsNone(note.position_y)
        self.assertIsNone(note.font_family)
        self.assertEqual(note.font_size, DEFAULT_FONT_SIZE)
        self.assertEqual(note.text_color, DEFAULT_TEXT_COLOR)
        self.assertTrue(note.is_open)
        self.assertIsNone(note.deleted_at)

    def test_new_note_normalizes_text_appearance(self) -> None:
        note = Note.new(
            "note-1",
            now="2026-06-12T00:00:00+00:00",
            font_family="Kavoon",
            font_size=100,
            text_color="#abc",
        )

        self.assertEqual(note.font_family, "Kavoon")
        self.assertEqual(note.font_size, 72)
        self.assertEqual(note.text_color, "#AABBCC")

    def test_validate_color_accepts_supported_values(self) -> None:
        self.assertEqual(validate_color("blue"), NoteColor.BLUE)

    def test_validate_color_rejects_unsupported_values(self) -> None:
        with self.assertRaises(ValueError):
            validate_color("orange")


if __name__ == "__main__":
    unittest.main()
