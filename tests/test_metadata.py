from __future__ import annotations

import unittest

from pinleaf import metadata


class MetadataTests(unittest.TestCase):
    def test_public_metadata_is_populated(self) -> None:
        self.assertEqual(metadata.APP_NAME, "Pinleaf")
        self.assertEqual(metadata.APP_ID, "dev.pinleaf.Pinleaf")
        self.assertTrue(metadata.APP_VERSION)
        self.assertTrue(metadata.BUILD_DATE)
        self.assertEqual(metadata.MAINTAINER_NAME, "Carlos R Moraes")
        self.assertEqual(metadata.MAINTAINER_WEBSITE, "https://about.robmoraes.dev.br")
        self.assertEqual(metadata.PROJECT_WEBSITE, "https://robmoraes.github.io/pinleaf/")
        self.assertTrue(metadata.APP_DESCRIPTION)
        self.assertEqual(metadata.APP_LICENSE, "MIT")
        self.assertIn("SIL Open Font License", metadata.FONT_CREDIT)


if __name__ == "__main__":
    unittest.main()
