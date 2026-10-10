"""Run native QA on an off-screen nested X11 server and private session bus.

Requires Xephyr and xdpyinfo, only for manual QA (not runtime dependencies).
Usage: /usr/bin/python3 tests/gui_session.py /usr/bin/python3 tests/gui_lifecycle.py
Add --desktop before the command to use the current X11 compositor instead.
Add --a11y to use a private AT-SPI service on the nested display.
"""
from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path


class Attributes(ctypes.Structure):
    _fields_ = [("background_pixmap", ctypes.c_ulong), ("background_pixel", ctypes.c_ulong),
                ("border_pixmap", ctypes.c_ulong), ("border_pixel", ctypes.c_ulong),
                ("bit_gravity", ctypes.c_int), ("win_gravity", ctypes.c_int),
                ("backing_store", ctypes.c_int), ("backing_planes", ctypes.c_ulong),
                ("backing_pixel", ctypes.c_ulong), ("save_under", ctypes.c_int),
                ("event_mask", ctypes.c_long), ("do_not_propagate_mask", ctypes.c_long),
                ("override_redirect", ctypes.c_int), ("colormap", ctypes.c_ulong),
                ("cursor", ctypes.c_ulong)]


def run_on_private_bus(command: list[str], env: dict[str, str], *, accessibility: bool = False) -> int:
    with tempfile.TemporaryDirectory(prefix="pinleaf-qa-bus-") as directory:
        config = Path(directory) / "session.conf"
        services = ""
        if accessibility:
            service_dir = Path(directory) / "services"
            service_dir.mkdir()
            (service_dir / "org.a11y.Bus.service").write_text(
                "[D-BUS Service]\nName=org.a11y.Bus\n"
                "Exec=/usr/libexec/at-spi-bus-launcher --launch-immediately --a11y=1 --screen-reader=1\n")
            services = f"<servicedir>{service_dir}</servicedir>"
        config.write_text('<busconfig><type>session</type><listen>unix:tmpdir=/tmp</listen><auth>EXTERNAL</auth>'
                          '<policy context="default"><allow send_destination="*" eavesdrop="true"/>'
                          '<allow eavesdrop="true"/><allow own="*"/></policy>' + services + '</busconfig>')
        return subprocess.run(["dbus-run-session", f"--config-file={config}", "--", *command], env=env).returncode


def main() -> int:
    command = sys.argv[1:]
    accessibility = bool(command and command[0] == "--a11y")
    if accessibility:
        command = command[1:]
    if not command:
        raise RuntimeError("Provide a QA command to run")
    env = dict(os.environ, GTK_A11Y="none", GIO_USE_VFS="local", GSETTINGS_BACKEND="memory")
    env.pop("AT_SPI_BUS_ADDRESS", None)
    if accessibility:
        env["GTK_A11Y"] = "atspi"
    if command and command[0] == "--desktop":
        if not os.environ.get("DISPLAY") or os.environ.get("XDG_SESSION_TYPE") != "x11":
            raise RuntimeError("Desktop QA requires a current X11 desktop session")
        if accessibility:
            raise RuntimeError("Private AT-SPI QA uses a nested display to avoid the desktop accessibility bus")
        return run_on_private_bus(command[1:], env)
    x11 = ctypes.CDLL("libX11.so.6")
    x11.XOpenDisplay.restype = ctypes.c_void_p
    x11.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
    x11.XDefaultRootWindow.restype = ctypes.c_ulong
    x11.XCreateSimpleWindow.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_int,
                                     ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_ulong, ctypes.c_ulong]
    x11.XCreateSimpleWindow.restype = ctypes.c_ulong
    x11.XChangeWindowAttributes.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong, ctypes.POINTER(Attributes)]
    x11.XMapWindow.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    x11.XFlush.argtypes = [ctypes.c_void_p]
    x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
    display = x11.XOpenDisplay(None)
    if not display:
        raise RuntimeError("An X11 host display is required for the nested QA server")
    parent = x11.XCreateSimpleWindow(display, x11.XDefaultRootWindow(display), -30000, -30000, 1400, 1000, 0, 0, 0)
    x11.XChangeWindowAttributes(display, parent, 1 << 9, ctypes.byref(Attributes(override_redirect=1)))
    x11.XMapWindow(display, parent)
    x11.XFlush(display)
    number = next(number for number in range(101, 150) if not Path(f"/tmp/.X{number}-lock").exists())
    server = subprocess.Popen(["Xephyr", f":{number}", "-parent", str(parent), "-screen", "1400x1000",
                               "-ac", "-nolisten", "tcp", "-noreset", "-no-host-grab"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        env["DISPLAY"] = f":{number}"
        for _ in range(50):
            if subprocess.run(["xdpyinfo"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
                break
            if server.poll() is not None:
                raise RuntimeError("Nested X11 server failed")
            time.sleep(0.1)
        else:
            raise RuntimeError("Nested X11 server timeout")
        return run_on_private_bus(command, env, accessibility=accessibility)
    finally:
        server.terminate()
        server.wait(timeout=5)
        x11.XCloseDisplay(display)


if __name__ == "__main__":
    raise SystemExit(main())
