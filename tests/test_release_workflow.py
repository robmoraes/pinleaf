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

    def test_workflows_install_runtime_python_dependencies_before_tests(self) -> None:
        for name in ("ci.yml", "release.yml"):
            workflow = (WORKFLOW.parent / name).read_text(encoding="utf-8")
            with self.subTest(workflow=name):
                for dependency in ("python3-jsonschema", "python3-cryptography",
                                   "python3-google-auth-oauthlib", "python3-requests", "python3-secretstorage"):
                    self.assertIn(dependency, workflow)
                    self.assertLess(workflow.index(dependency), workflow.index("Run unit tests"))

    def test_release_requires_a_bundled_client_before_build_or_publication(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("env -u PINLEAF_GOOGLE_CLIENT_FILE", workflow)
        self.assertIn("client_configuration()", workflow)
        self.assertLess(workflow.index("Validate bundled Google Drive client"), workflow.index("Build Debian package"))


if __name__ == "__main__":
    unittest.main()
