from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / "scripts" / "install-local"
UNINSTALL = ROOT / "scripts" / "uninstall-local"


class InstallScriptTests(unittest.TestCase):
    def test_scripts_are_valid_shell(self) -> None:
        subprocess.run(["sh", "-n", str(INSTALL)], check=True)
        subprocess.run(["sh", "-n", str(UNINSTALL)], check=True)

    def test_install_and_uninstall_with_temporary_home(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            env = os.environ | {"HOME": str(home)}

            subprocess.run([str(INSTALL)], cwd=ROOT, env=env, check=True)

            wrapper = home / ".local/bin/pinleaf"
            desktop = home / ".local/share/applications/dev.pinleaf.Pinleaf.desktop"
            data_dir = home / ".local/share/pinleaf"
            data_dir.mkdir(parents=True)

            self.assertTrue(wrapper.exists())
            self.assertTrue(desktop.exists())
            self.assertTrue(wrapper.stat().st_mode & stat.S_IXUSR)
            self.assertTrue((home / ".local/share/icons/hicolor/16x16/apps/pinleaf.png").exists())
            self.assertTrue((home / ".local/share/icons/hicolor/32x32/apps/pinleaf.png").exists())
            self.assertTrue((home / ".local/share/icons/hicolor/64x64/apps/pinleaf.png").exists())
            self.assertTrue((home / ".local/share/icons/hicolor/256x256/apps/pinleaf.png").exists())
            self.assertTrue((home / ".local/share/icons/hicolor/scalable/apps/pinleaf.svg").exists())
            self.assertIn("Exec=", desktop.read_text(encoding="utf-8"))
            self.assertIn("Icon=pinleaf", desktop.read_text(encoding="utf-8"))

            subprocess.run([str(UNINSTALL)], cwd=ROOT, env=env, check=True)

            self.assertFalse(wrapper.exists())
            self.assertFalse(desktop.exists())
            self.assertFalse((home / ".local/share/icons/hicolor/16x16/apps/pinleaf.png").exists())
            self.assertFalse((home / ".local/share/icons/hicolor/scalable/apps/pinleaf.svg").exists())
            self.assertTrue(data_dir.exists())


if __name__ == "__main__":
    unittest.main()
