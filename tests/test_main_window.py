from __future__ import annotations

import unittest
from datetime import timedelta, timezone

from pinleaf.models import Note
from pinleaf.ui.main_window import _format_timestamp, _preview


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

    def test_format_timestamp_converts_utc_to_local_timezone(self) -> None:
        local_tz = timezone(timedelta(hours=-3))

        self.assertEqual(
            _format_timestamp("2026-06-12T12:30:00+00:00", local_tz=local_tz),
            "Jun 12, 2026 9:30 AM UTC-03:00",
        )

    def test_format_timestamp_returns_invalid_value_unchanged(self) -> None:
        self.assertEqual(_format_timestamp("not-a-timestamp"), "not-a-timestamp")


if __name__ == "__main__":
    unittest.main()
