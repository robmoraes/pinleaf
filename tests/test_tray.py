from __future__ import annotations

import unittest
from unittest.mock import patch

from pinleaf.ui.tray import TrayController, _socket_path


class TrayControllerTests(unittest.TestCase):
    def test_handle_payload_accepts_known_actions(self) -> None:
        actions: list[str] = []
        tray = TrayController(actions.append)

        tray._handle_payload("new-note")
        tray._handle_payload("show-main")
        tray._handle_payload("quit")

        self.assertEqual(actions, ["new-note", "show-main", "quit"])

    def test_handle_payload_ignores_unknown_actions(self) -> None:
        actions: list[str] = []
        tray = TrayController(actions.append)

        tray._handle_payload("unknown")

        self.assertEqual(actions, [])

    def test_socket_path_falls_back_when_runtime_dir_is_not_writable(self) -> None:
        with patch.dict("os.environ", {"XDG_RUNTIME_DIR": "/not-writable"}, clear=False):
            with patch("os.access", return_value=False):
                path = _socket_path()

        self.assertEqual(path.parent.name, "tmp")


if __name__ == "__main__":
    unittest.main()
