from __future__ import annotations

import unittest

from pinleaf.ui.note_window import _text_left_margin_for


class NoteWindowTests(unittest.TestCase):
    def test_text_left_margin_only_adds_room_for_dancing_script(self) -> None:
        self.assertEqual(_text_left_margin_for("Dancing Script"), 4)
        self.assertEqual(_text_left_margin_for("Kavoon"), 0)
        self.assertEqual(_text_left_margin_for(None), 0)


if __name__ == "__main__":
    unittest.main()
