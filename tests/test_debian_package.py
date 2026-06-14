from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEBIAN = ROOT / "debian"


class DebianPackageTests(unittest.TestCase):
    def test_required_packaging_files_exist(self) -> None:
        for path in (
            "changelog",
            "control",
            "copyright",
            "rules",
            "source/format",
            "dev.pinleaf.Pinleaf.desktop",
            "pinleaf-wrapper",
        ):
            self.assertTrue((DEBIAN / path).exists(), path)

    def test_control_declares_runtime_dependencies(self) -> None:
        control = (DEBIAN / "control").read_text(encoding="utf-8")

        for dependency in (
            "python3",
            "python3-gi",
            "gir1.2-gtk-4.0",
            "gir1.2-adw-1",
            "gir1.2-ayatanaappindicator3-0.1",
            "libayatana-appindicator3-1",
            "libfontconfig1",
        ):
            self.assertIn(dependency, control)

    def test_desktop_file_uses_installed_command_and_icon(self) -> None:
        desktop_file = (DEBIAN / "dev.pinleaf.Pinleaf.desktop").read_text(encoding="utf-8")

        self.assertIn("Exec=pinleaf", desktop_file)
        self.assertIn("Icon=pinleaf", desktop_file)
        self.assertIn("StartupWMClass=dev.pinleaf.Pinleaf", desktop_file)

    def test_wrapper_uses_system_python_module_entrypoint(self) -> None:
        wrapper = (DEBIAN / "pinleaf-wrapper").read_text(encoding="utf-8")

        self.assertIn("/usr/bin/python3 -m pinleaf", wrapper)
        self.assertNotIn("wspace", wrapper)
        self.assertNotIn("repo_root", wrapper)

    def test_rules_installs_icons_and_python_package(self) -> None:
        rules = (DEBIAN / "rules").read_text(encoding="utf-8")

        self.assertIn("/usr/lib/python3/dist-packages", rules)
        self.assertIn("/usr/bin/pinleaf", rules)
        self.assertIn("/usr/share/applications/dev.pinleaf.Pinleaf.desktop", rules)
        self.assertIn("pinleaf/resources/icons/pinleaf-256.png", rules)
        self.assertIn("/usr/share/icons/hicolor/scalable/apps/pinleaf.svg", rules)


if __name__ == "__main__":
    unittest.main()
