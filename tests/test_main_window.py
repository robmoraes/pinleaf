from __future__ import annotations

import unittest

from pinleaf.models import Note
from pinleaf.ui.main_window import _preview


class MainWindowPreviewTests(unittest.TestCase):
    def test_preview_ignores_layout_whitespace(self) -> None:
        note = Note.new("note-1", now="2026-06-12T00:00:00+00:00").with_content(
            "\n\n        Comprar cafe\n        e leite\n\n",
            now="2026-06-12T01:00:00+00:00",
        )

        self.assertEqual(_preview(note), "Comprar cafe e leite")

    def test_preview_handles_empty_note(self) -> None:
        note = Note.new("note-1", now="2026-06-12T00:00:00+00:00").with_content(
            "\n    \n",
            now="2026-06-12T01:00:00+00:00",
        )

        self.assertEqual(_preview(note), "Empty note")


if __name__ == "__main__":
    unittest.main()
