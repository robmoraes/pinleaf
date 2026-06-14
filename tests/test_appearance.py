from __future__ import annotations

import unittest
from pathlib import Path

from pinleaf.appearance import (
    font_css_classes,
    font_option_for,
    font_options,
    normalize_font_family,
    system_font_option_count,
)


ROOT = Path(__file__).resolve().parents[1]


CURATED_FONT_FAMILIES = (
    "Dancing Script",
    "Kavoon",
    "Londrina Shadow",
    "Nabla",
    "Press Start 2P",
    "Style Script",
)

SYSTEM_FONT_VALUES = (None, "cursive", "sans-serif", "monospace")


class AppearanceTests(unittest.TestCase):
    def test_font_options_include_default(self) -> None:
        default = font_options()[0]

        self.assertIsNone(default.value)
        self.assertIsNone(default.css_class)

    def test_font_options_start_with_system_fonts(self) -> None:
        values = tuple(option.value for option in font_options()[: system_font_option_count()])

        self.assertEqual(values, SYSTEM_FONT_VALUES)

    def test_font_options_include_curated_bundled_fonts(self) -> None:
        values = tuple(option.value for option in font_options())

        for family in CURATED_FONT_FAMILIES:
            self.assertIn(family, values)

    def test_normalize_font_family_accepts_supported_font(self) -> None:
        for family in CURATED_FONT_FAMILIES:
            self.assertEqual(normalize_font_family(family), family)
        self.assertEqual(normalize_font_family("cursive"), "cursive")
        self.assertEqual(normalize_font_family("sans-serif"), "sans-serif")
        self.assertEqual(normalize_font_family("monospace"), "monospace")

    def test_normalize_font_family_returns_none_for_default_or_invalid_font(self) -> None:
        self.assertIsNone(normalize_font_family(None))
        self.assertIsNone(normalize_font_family(""))
        self.assertIsNone(normalize_font_family("Unknown Font"))

    def test_font_option_for_returns_default_for_invalid_font(self) -> None:
        self.assertIsNone(font_option_for("Unknown Font").value)

    def test_font_option_for_curated_fonts_returns_label_and_css_class(self) -> None:
        for family in CURATED_FONT_FAMILIES:
            option = font_option_for(family)

            self.assertEqual(option.value, family)
            self.assertEqual(option.label, family)
            self.assertIsNotNone(option.css_class)

    def test_font_css_classes_are_unique(self) -> None:
        css_classes = font_css_classes()

        self.assertEqual(len(css_classes), len(set(css_classes)))

    def test_font_css_classes_style_menu_samples(self) -> None:
        styles = (ROOT / "pinleaf" / "resources" / "styles.css").read_text(encoding="utf-8")

        for css_class in font_css_classes():
            self.assertIn(f".note-font-sample.{css_class}", styles)


if __name__ == "__main__":
    unittest.main()
