from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pinleaf.config import DB_FILENAME, default_data_dir, ensure_data_dir, load_config, resource_path


class ConfigTests(unittest.TestCase):
    def test_default_data_dir_uses_xdg_data_home_when_present(self) -> None:
        data_dir = default_data_dir({"XDG_DATA_HOME": "/tmp/example"})

        self.assertEqual(data_dir, Path("/tmp/example/pinleaf"))

    def test_load_config_sets_database_path(self) -> None:
        config = load_config({"XDG_DATA_HOME": "/tmp/example"})

        self.assertEqual(config.database_path, Path("/tmp/example/pinleaf") / DB_FILENAME)

    def test_ensure_data_dir_creates_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pinleaf"

            ensure_data_dir(path)

            self.assertTrue(path.is_dir())

    def test_resource_path_resolves_package_resource(self) -> None:
        path = resource_path("resources", "styles.css")

        self.assertEqual(path.name, "styles.css")
        self.assertTrue(path.exists())


if __name__ == "__main__":
    unittest.main()
