from __future__ import annotations

import unittest

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from pinleaf.ui.about import show_about


class AboutTests(unittest.TestCase):
    def test_show_about_is_importable(self) -> None:
        self.assertTrue(callable(show_about))


if __name__ == "__main__":
    unittest.main()
