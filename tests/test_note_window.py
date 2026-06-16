from __future__ import annotations

import unittest

import gi

gi.require_version("Gdk", "4.0")
from gi.repository import Gdk

from pinleaf.ui.note_window import _is_escape_key, _text_left_margin_for


class NoteWindowTests(unittest.TestCase):
    def test_text_left_margin_only_adds_room_for_dancing_script(self) -> None:
        self.assertEqual(_text_left_margin_for("Dancing Script"), 4)
        self.assertEqual(_text_left_margin_for("Kavoon"), 0)
        self.assertEqual(_text_left_margin_for(None), 0)

    def test_escape_key_opens_note_action_dialog(self) -> None:
        self.assertTrue(_is_escape_key(Gdk.KEY_Escape))
        self.assertFalse(_is_escape_key(Gdk.KEY_Return))


if __name__ == "__main__":
    unittest.main()
