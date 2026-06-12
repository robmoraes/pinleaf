from __future__ import annotations

import unittest

from pinleaf.fonts import bundled_font_paths, load_bundled_fonts


class FontTests(unittest.TestCase):
    def test_bundled_font_paths_returns_list(self) -> None:
        self.assertIsInstance(bundled_font_paths(), list)

    def test_load_bundled_fonts_registers_packaged_fonts(self) -> None:
        self.assertGreaterEqual(load_bundled_fonts(), 4)


if __name__ == "__main__":
    unittest.main()
