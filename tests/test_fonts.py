from __future__ import annotations

import unittest

from pinleaf.fonts import bundled_font_paths, load_bundled_fonts


CURATED_FONT_FILES = {
    "Dancing_Script/DancingScript-VariableFont_wght.ttf",
    "Kavoon/Kavoon-Regular.ttf",
    "Londrina_Shadow/LondrinaShadow-Regular.ttf",
    "Nabla/Nabla-Regular-VariableFont_EDPT,EHLT.ttf",
    "Press_Start_2P/PressStart2P-Regular.ttf",
    "Style_Script/StyleScript-Regular.ttf",
}


class FontTests(unittest.TestCase):
    def test_bundled_font_paths_returns_list(self) -> None:
        self.assertIsInstance(bundled_font_paths(), list)

    def test_bundled_font_paths_include_curated_fonts(self) -> None:
        relative_paths = {
            f"{path.parent.name}/{path.name}"
            for path in bundled_font_paths()
            if path.parent.name != "static"
        }

        self.assertTrue(CURATED_FONT_FILES.issubset(relative_paths))

    def test_load_bundled_fonts_registers_packaged_fonts(self) -> None:
        self.assertGreaterEqual(load_bundled_fonts(), 4)


if __name__ == "__main__":
    unittest.main()
