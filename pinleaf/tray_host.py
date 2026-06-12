from __future__ import annotations

import socket
import sys
from pathlib import Path

from pinleaf.config import icon_path, icon_svg_path


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        print("usage: python -m pinleaf.tray_host <socket-path>", file=sys.stderr)
        return 2

    socket_path = Path(args[0])
    try:
        import gi

        gi.require_version("Gtk", "3.0")
        gi.require_version("AyatanaAppIndicator3", "0.1")
        from gi.repository import AyatanaAppIndicator3, Gtk
    except Exception as exc:
        print(f"Pinleaf tray unavailable: {exc}", file=sys.stderr)
        return 1

    indicator = AyatanaAppIndicator3.Indicator.new(
        "pinleaf",
        str(icon_svg_path()),
        AyatanaAppIndicator3.IndicatorCategory.APPLICATION_STATUS,
    )
    indicator.set_icon_full(str(icon_svg_path()), "Pinleaf")
    indicator.set_status(AyatanaAppIndicator3.IndicatorStatus.ACTIVE)
    indicator.set_menu(_build_menu(Gtk, socket_path))
    Gtk.main()
    return 0


def _build_menu(Gtk: object, socket_path: Path) -> object:
    menu = Gtk.Menu()

    actions = [
        ("New Note", "new-note"),
        ("Show Pinleaf", "show-main"),
        ("Quit", "quit"),
    ]
    for label, action in actions:
        item = Gtk.MenuItem(label=label)
        item.connect("activate", lambda _item, selected=action: _send(socket_path, selected))
        menu.append(item)

    menu.show_all()
    return menu


def _send(socket_path: Path, action: str) -> None:
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.connect(str(socket_path))
            client.sendall(action.encode("utf-8"))
    except OSError as exc:
        print(f"Pinleaf tray action failed: {exc}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
