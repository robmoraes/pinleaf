from __future__ import annotations

import unittest

from pinleaf.appearance import font_option_for, font_options, normalize_font_family


class AppearanceTests(unittest.TestCase):
    def test_font_options_include_default(self) -> None:
        default = font_options()[0]

        self.assertIsNone(default.value)
        self.assertIsNone(default.css_class)

    def test_normalize_font_family_accepts_supported_font(self) -> None:
        self.assertEqual(normalize_font_family("Dancing Script"), "Dancing Script")
        self.assertEqual(normalize_font_family("cursive"), "cursive")
        self.assertEqual(normalize_font_family("sans-serif"), "sans-serif")

    def test_normalize_font_family_returns_none_for_default_or_invalid_font(self) -> None:
        self.assertIsNone(normalize_font_family(None))
        self.assertIsNone(normalize_font_family(""))
        self.assertIsNone(normalize_font_family("Unknown Font"))

    def test_font_option_for_returns_default_for_invalid_font(self) -> None:
        self.assertIsNone(font_option_for("Unknown Font").value)


if __name__ == "__main__":
    unittest.main()
