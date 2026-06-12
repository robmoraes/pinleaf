from __future__ import annotations

import os
import socket
import subprocess
import sys
import tempfile
import threading
from collections.abc import Callable
from pathlib import Path


TrayActionHandler = Callable[[str], None]


class TrayController:
    def __init__(self, on_action: TrayActionHandler) -> None:
        self.on_action = on_action
        self.socket_path = _socket_path()
        self._socket: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._process: subprocess.Popen[str] | None = None
        self._stopped = threading.Event()

    def start(self) -> None:
        try:
            self.socket_path.unlink(missing_ok=True)
            server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server.bind(str(self.socket_path))
            server.listen(8)
        except OSError as exc:
            print(f"Pinleaf tray disabled: could not create IPC socket: {exc}", file=sys.stderr)
            return

        self._socket = server
        self._thread = threading.Thread(target=self._serve, name="pinleaf-tray-ipc", daemon=True)
        self._thread.start()

        try:
            self._process = subprocess.Popen(
                [sys.executable, "-m", "pinleaf.tray_host", str(self.socket_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
        except OSError as exc:
            print(f"Pinleaf tray disabled: could not start tray helper: {exc}", file=sys.stderr)
            self.stop()

    def stop(self) -> None:
        self._stopped.set()
        if self._process is not None and self._process.poll() is None:
            self._process.terminate()
        if self._socket is not None:
            try:
                self._socket.close()
            except OSError:
                pass
        try:
            self.socket_path.unlink(missing_ok=True)
        except OSError:
            pass

    def _serve(self) -> None:
        assert self._socket is not None
        while not self._stopped.is_set():
            try:
                connection, _ = self._socket.accept()
            except OSError:
                return
            with connection:
                try:
                    payload = connection.recv(128).decode("utf-8").strip()
                except OSError:
                    continue
            if payload:
                self._handle_payload(payload)

    def _handle_payload(self, payload: str) -> None:
        if payload in {"new-note", "show-main", "quit"}:
            self.on_action(payload)


def _socket_path() -> Path:
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
    base = Path(runtime_dir) if runtime_dir and os.access(runtime_dir, os.W_OK) else Path(tempfile.gettempdir())
    return base / f"pinleaf-{os.getuid()}-{os.getpid()}.sock"
