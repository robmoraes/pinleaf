from __future__ import annotations

import sys
from collections.abc import Sequence

from pinleaf.config import ensure_data_dir, icon_path, load_config, resource_path
from pinleaf.fonts import load_bundled_fonts
from pinleaf.metadata import APP_ID
from pinleaf.services.note_service import NoteService
from pinleaf.storage.sqlite_store import NoteStore


def run(argv: Sequence[str] | None = None) -> int:
    """Run the GTK application.

    GTK is imported lazily so non-GUI tests can run without native desktop
    bindings installed in the active Python environment.
    """

    try:
        import gi
    except ModuleNotFoundError:
        print(
            "Pinleaf requires PyGObject, GTK 4 and libadwaita to run the GUI.",
            file=sys.stderr,
        )
        return 1

    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    from gi.repository import Adw, Gdk, GLib, Gtk

    from pinleaf.ui.main_window import MainWindow
    from pinleaf.ui.note_window import NoteWindow
    from pinleaf.ui.tray import TrayController

    class PinleafApplication(Adw.Application):
        def __init__(self) -> None:
            super().__init__(application_id=APP_ID)
            self.store: NoteStore | None = None
            self.note_service: NoteService | None = None
            self.main_window: MainWindow | None = None
            self.note_windows: dict[str, NoteWindow] = {}
            self.startup_error: Exception | None = None
            self.tray: TrayController | None = None

        def do_startup(self) -> None:
            Adw.Application.do_startup(self)
            load_bundled_fonts()
            self._load_icons()
            self._load_css()
            try:
                config = load_config()
                ensure_data_dir(config.data_dir)
                self.store = NoteStore(config.database_path)
                self.note_service = NoteService(self.store)
                self.tray = TrayController(
                    lambda action: GLib.idle_add(self._handle_tray_action, action)
                )
                self.tray.start()
            except Exception as exc:
                self.startup_error = exc
                print(f"Pinleaf failed to initialize storage: {exc}", file=sys.stderr)

        def do_shutdown(self) -> None:
            if self.tray is not None:
                self.tray.stop()
            for window in list(self.note_windows.values()):
                window.flush_pending_changes()
                window.save_window_state()
            if self.store is not None:
                self.store.close()
            Adw.Application.do_shutdown(self)

        def do_activate(self) -> None:
            if self.startup_error is not None:
                self.quit()
                return
            try:
                service = self._service()
                if self.main_window is None:
                    self.main_window = MainWindow(
                        application=self,
                        note_service=service,
                        on_create_note=self.create_note,
                        on_open_note=self.open_note,
                        on_delete_note=self.delete_note,
                    )
                self.main_window.refresh()
                self.main_window.present()
                self._restore_open_notes()
            except Exception as exc:
                self.startup_error = exc
                print(f"Pinleaf failed to open the GUI: {exc}", file=sys.stderr)
                self.quit()

        def create_note(self) -> None:
            note = self._service().create_note()
            self.open_note(note.id)
            self.refresh_main_window()

        def open_note(self, note_id: str) -> None:
            existing = self.note_windows.get(note_id)
            if existing is not None:
                existing.present()
                return

            note = self._service().reopen_note(note_id)
            window = NoteWindow(
                application=self,
                note=note,
                note_service=self._service(),
                on_closed=self._on_note_window_closed,
                on_changed=self.refresh_main_window,
            )
            self.note_windows[note_id] = window
            window.present()
            self.refresh_main_window()

        def delete_note(self, note_id: str) -> None:
            window = self.note_windows.pop(note_id, None)
            if window is not None:
                window.close()
            self._service().delete_note(note_id)
            self.refresh_main_window()

        def refresh_main_window(self) -> None:
            if self.main_window is not None:
                self.main_window.refresh()

        def _handle_tray_action(self, action: str) -> bool:
            if action == "new-note":
                self.create_note()
            elif action == "show-main":
                self.do_activate()
            elif action == "quit":
                self.quit()
            return False

        def _on_note_window_closed(self, note_id: str) -> None:
            self.note_windows.pop(note_id, None)
            self.refresh_main_window()

        def _restore_open_notes(self) -> None:
            for note in self._service().list_notes():
                if note.is_open and note.id not in self.note_windows:
                    self.open_note(note.id)

        def _service(self) -> NoteService:
            if self.note_service is None:
                raise RuntimeError("Pinleaf application was activated before startup completed.")
            return self.note_service

        def _load_css(self) -> None:
            display = Gdk.Display.get_default()
            if display is None:
                return
            provider = Gtk.CssProvider()
            provider.load_from_path(str(resource_path("resources", "styles.css")))
            Gtk.StyleContext.add_provider_for_display(
                display,
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )

        def _load_icons(self) -> None:
            display = Gdk.Display.get_default()
            if display is None:
                return
            icon_theme = Gtk.IconTheme.get_for_display(display)
            icon_theme.add_search_path(str(icon_path().parent))
            Gtk.Window.set_default_icon_name("pinleaf")

    app = PinleafApplication()
    try:
        exit_code = app.run(list(argv or []))
        return 1 if app.startup_error is not None else exit_code
    except Exception as exc:
        print(f"Pinleaf failed to start: {exc}", file=sys.stderr)
        return 1
