from __future__ import annotations

import unittest

from pinleaf.config import icon_path, icon_svg_path


class IconTests(unittest.TestCase):
    def test_icon_assets_exist(self) -> None:
        for size in (None, 16, 32, 64, 256):
            self.assertTrue(icon_path(size).exists())
        self.assertTrue(icon_svg_path().exists())


if __name__ == "__main__":
    unittest.main()
