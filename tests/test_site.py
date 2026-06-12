from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "docs" / "site"
PAGE_URL = "https://robmoraes.github.io/pinleaf/"


class SiteTests(unittest.TestCase):
    def test_site_files_exist(self) -> None:
        self.assertTrue((SITE / "index.html").exists())
        self.assertTrue((SITE / "styles.css").exists())

    def test_expected_screenshots_exist(self) -> None:
        screenshots = SITE / "assets" / "screenshots"
        for name in ("overview.png", "panel.png", "notes.png", "indicator.png", "launcher.png"):
            self.assertTrue((screenshots / name).exists())

    def test_readme_links_project_page(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn(PAGE_URL, readme)

    def test_site_has_accessible_image_alt_text(self) -> None:
        html = (SITE / "index.html").read_text(encoding="utf-8")

        self.assertIn('alt="Pinleaf desktop', html)
        self.assertIn('alt="Pinleaf main panel', html)
        self.assertIn('alt="Four overlapping Pinleaf', html)


if __name__ == "__main__":
    unittest.main()
