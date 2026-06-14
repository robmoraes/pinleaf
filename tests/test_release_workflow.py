from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"


class ReleaseWorkflowTests(unittest.TestCase):
    def test_release_workflow_exists(self) -> None:
        self.assertTrue(WORKFLOW.exists())

    def test_release_workflow_publishes_debian_artifacts_on_tags(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn('tags:', workflow)
        self.assertIn('- "v*"', workflow)
        self.assertIn("contents: write", workflow)
        self.assertIn("dpkg-buildpackage -us -uc -b", workflow)
        self.assertIn("pinleaf_*.deb", workflow)
        self.assertIn("pinleaf_*.buildinfo", workflow)
        self.assertIn("pinleaf_*.changes", workflow)
        self.assertIn("gh release upload", workflow)


if __name__ == "__main__":
    unittest.main()
