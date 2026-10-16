from __future__ import annotations

import sys
from pathlib import Path
from collections.abc import Callable, Sequence

from pinleaf.config import ensure_data_dir, icon_path, load_config, resource_path
from pinleaf.fonts import load_bundled_fonts
from pinleaf.metadata import APP_ID
from pinleaf.models import Note
from pinleaf.services.note_service import NoteService
from pinleaf.services.context_controller import ContextController, TransitionError
from pinleaf.organization import OrganizationError
from pinleaf.storage.sqlite_store import NoteStore
from pinleaf.storage.restore_recovery import PreparedRestore, RestoreRecovery
from pinleaf.services.backup_service import BackupService
from pinleaf.backup_format import BackupError, library_digest
from pinleaf.storage.library_backup import read_library


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
    from pinleaf.ui.dialogs import show_error
    from pinleaf.ui.tray import TrayController
    from pinleaf.ui.backup_window import BackupWindow

    class PinleafApplication(Adw.Application):
        def __init__(self) -> None:
            super().__init__(application_id=APP_ID)
            self.store: NoteStore | None = None
            self.note_service: NoteService | None = None
            self.main_window: MainWindow | None = None
            self.note_windows: dict[str, NoteWindow] = {}
            self.startup_error: Exception | None = None
            self.tray: TrayController | None = None
            self.context_controller: ContextController | None = None
            self.error_window: Gtk.Window | None = None
            self.backup_window: BackupWindow | None = None
            self.backup_service: BackupService | None = None
            self.config = None
            self.library_generation = 0
            self.restore_busy = False
            self.restore_notice: str | None = None

        def do_startup(self) -> None:
            Adw.Application.do_startup(self)
            load_bundled_fonts()
            self._load_icons()
            self._load_css()
            try:
                config = load_config()
                self.config = config
                ensure_data_dir(config.data_dir)
                self.backup_service = BackupService(config.database_path, GLib.idle_add)
                recovered = RestoreRecovery(config.database_path).reconcile()
                if recovered:
                    self.restore_notice = ("An interrupted restore was completed." if recovered == "restored"
                                           else "An interrupted restore did not commit. Your previous library was retained.")
                self._open_store()
                self.tray = TrayController(
                    self._queue_tray_action
                )
                self.tray.start()
            except Exception as exc:
                self.startup_error = exc
                print(f"Pinleaf failed to initialize storage ({type(exc).__name__}).", file=sys.stderr)

        def do_shutdown(self) -> None:
            if self.backup_service is not None:
                self.backup_service.close()
            if self.tray is not None:
                self.tray.stop()
            for window in list(self.note_windows.values()):
                window.flush_pending_changes()
                window.save_window_state()
            if self.main_window is not None:
                self.main_window.destroy()
            if self.store is not None:
                self.store.close()
            Adw.Application.do_shutdown(self)

        def do_activate(self) -> None:
            if self.restore_busy:
                if self.backup_window is not None:
                    self.backup_window.present()
                return
            if self.startup_error is not None:
                self._show_startup_error()
                return
            try:
                service = self._service()
                if self.main_window is None:
                    self.main_window = MainWindow(
                        application=self,
                        note_service=service,
                        on_create_note=self._generation_callback(self.create_note),
                        on_create_shared_note=self._generation_callback(lambda: self.create_note(shared=True)),
                        on_open_note=self._generation_callback(self.open_note),
                        on_delete_note=self._generation_callback(self.delete_note),
                        on_execute=self._generation_callback(self.execute_command),
                        on_hide_note=self._generation_callback(self.hide_note),
                        on_backup=self._generation_callback(self.show_backup),
                    )
                self.main_window.refresh()
                self.main_window.present()
                self._restore_open_notes()
                if self.restore_notice:
                    show_error(self.main_window, "Restore recovery", self.restore_notice)
                    self.restore_notice = None
                if self.store.context_recovered:
                    show_error(self.main_window, "Working context recovered",
                               "The previous context was unavailable. Pinleaf restored an available profile with shared notes; your notes were preserved.")
                    self.store.context_recovered = False
            except Exception as exc:
                self.startup_error = exc
                print(f"Pinleaf failed to open the GUI ({type(exc).__name__}).", file=sys.stderr)
                self._show_startup_error()

        def create_note(self, *, shared: bool = False) -> None:
            self._perform(lambda: self._service().create_note(shared=shared), affected_ids=set())

        def open_note(self, note_id: str) -> None:
            existing = self.note_windows.get(note_id)
            if existing is not None:
                existing.present()
                return

            self._perform(lambda: self._service().organization.activate_and_open(note_id), focus_note_id=note_id)

        def _prepare_note_window(self, note: Note) -> NoteWindow:
            before = set(self.get_windows())
            try:
                return NoteWindow(
                    application=self,
                    note=note,
                    note_service=self._service(),
                    on_closed=self._on_note_window_closed,
                    on_changed=self.refresh_main_window,
                )
            except Exception:
                for window in set(self.get_windows()) - before:
                    window.destroy()
                raise

        def execute_command(self, action: Callable[[], object], *, affected_ids: set[str] | None = None,
                            focus_note_id: str | None = None) -> object:
            if self.restore_busy:
                raise TransitionError("Restore is in progress. Wait for it to finish.")
            if self.context_controller is None:
                raise RuntimeError("Context controller is unavailable.")
            return self.context_controller.execute(action, affected_ids=affected_ids, focus_note_id=focus_note_id)

        def _perform(self, action: Callable[[], object], *, affected_ids: set[str] | None = None,
                     focus_note_id: str | None = None) -> None:
            try:
                self.execute_command(action, affected_ids=affected_ids, focus_note_id=focus_note_id)
            except (OrganizationError, TransitionError) as exc:
                show_error(self.main_window, "Could not complete this change", str(exc))
            except Exception:
                show_error(self.main_window, "Could not save this change",
                           "Your current context is preserved. Retry after checking storage availability.")

        def delete_note(self, note_id: str) -> None:
            self._perform(lambda: self._service().delete_note(note_id), affected_ids={note_id})

        def hide_note(self, note_id: str) -> None:
            def action() -> None:
                note = self._service().get_note(note_id)
                if note is not None:
                    self._service().close_note(note_id, width=note.width, height=note.height,
                        position_x=note.position_x, position_y=note.position_y)
            self._perform(action, affected_ids={note_id})

        def refresh_main_window(self) -> None:
            if self.main_window is not None and not (self.context_controller and self.context_controller.busy):
                self.main_window.refresh()

        def _handle_tray_action(self, action: str) -> bool:
            if self.restore_busy:
                return False
            if action == "new-note":
                self.create_note()
            elif action == "show-main":
                self.do_activate()
            elif action == "quit":
                self.quit()
            return False

        def _queue_tray_action(self, action: str) -> None:
            generation = self.library_generation
            def dispatch() -> bool:
                if generation == self.library_generation:
                    self._handle_tray_action(action)
                return False
            GLib.idle_add(dispatch)

        def _generation_callback(self, callback: Callable) -> Callable:
            generation = self.library_generation
            def guarded(*args, **kwargs):
                if generation != self.library_generation or self.restore_busy:
                    raise TransitionError("The library changed or is being restored. Reopen the panel.")
                return callback(*args, **kwargs)
            return guarded

        def _open_store(self) -> None:
            self.note_service = None
            self.context_controller = None
            self.store = NoteStore(self.config.database_path)
            self.note_service = NoteService(self.store)
            self.context_controller = ContextController(
                self.note_service, self.note_windows, self._prepare_note_window,
                on_context_changed=self._on_context_changed, on_refresh=self.refresh_main_window,
                on_presentation_error=lambda: show_error(self.main_window, "Could not display a note",
                    "The context was saved. Reopen the panel to retry displaying its notes."))

        def _capture_library(self) -> dict:
            if self.context_controller is None:
                raise TransitionError("The current library could not be opened.")
            return self.context_controller.capture_library()

        def show_backup(self, *, startup_only: bool = False) -> None:
            if self.backup_window is not None:
                self.backup_window.capture = self._capture_library if self.context_controller is not None else None
                self.backup_window.present()
                return
            parent = self.error_window if startup_only else self.main_window
            focused = parent.get_focus()
            def closed() -> None:
                self.backup_window = None
                destination = self.main_window or self.error_window
                if destination is not None:
                    destination.present()
                    if focused is not None and focused.get_root() is destination and focused.get_mapped():
                        focused.grab_focus()
                    elif self.main_window is not None:
                        self.main_window.profile_button.grab_focus()
            self.backup_window = BackupWindow(parent=parent, service=self.backup_service,
                capture=self._capture_library if self.context_controller is not None else None,
                gate=self._gate_restore, apply=self._apply_restore, startup_only=startup_only,
                on_closed=closed)
            self.backup_window.present()

        def _gate_restore(self, active: bool) -> None:
            self.restore_busy = active
            if self.context_controller is not None:
                self.context_controller.busy = active
            for window in Gtk.Window.list_toplevels():
                if window is not self.backup_window:
                    window.set_sensitive(not active)

        def _dispose_library_ui(self) -> None:
            self.library_generation += 1
            for window in list(self.note_windows.values()):
                window.dispose_for_context()
            self.note_windows.clear()
            for window in Gtk.Window.list_toplevels():
                if window is not self.backup_window:
                    window.destroy()
            self.main_window = None
            self.error_window = None

        def _apply_restore(self, prepared: PreparedRestore) -> Path:
            recovery = self.backup_service.recovery
            disposed = False
            def dispose() -> None:
                nonlocal disposed
                self._dispose_library_ui()
                disposed = True
            try:
                if prepared.old_digest is not None:
                    location = recovery.apply(self.store, prepared, before_replace=dispose)
                else:
                    location = recovery.apply_unreadable(prepared)
                    dispose()
            except Exception:
                if not disposed:
                    raise
                if self.store is not None:
                    self.store.close()
                    self.store = None
                try:
                    outcome = recovery.reconcile()
                    self._open_store()
                    self.startup_error = None
                    self._gate_restore(False)
                    self.do_activate()
                    self.backup_window.set_transient_for(self.main_window)
                    if outcome == "restored" or library_digest(read_library(self.store.connection)) == library_digest(prepared.preview.backup.payload["library"]):
                        return prepared.preview.recovery
                except Exception as exc:
                    self.startup_error = exc
                    self._gate_restore(False)
                    self._show_startup_error()
                raise
            if self.store is not None:
                self.store.close()
                self.store = None
            try:
                self._open_store()
                self.startup_error = None
                self._gate_restore(False)
                self.do_activate()
                if self.startup_error is not None:
                    raise BackupError("Data restored, but the notes could not be displayed. Close and reopen Pinleaf.")
                self.backup_window.set_transient_for(self.main_window)
                self.backup_window.present()
                if self.tray is None:
                    self.tray = TrayController(self._queue_tray_action)
                    self.tray.start()
            except Exception as exc:
                self.startup_error = exc
                self._gate_restore(False)
                self._show_startup_error()
                raise BackupError("Data restored, but the notes could not be displayed. Close and reopen Pinleaf.") from exc
            return location

        def _on_note_window_closed(self, note_id: str) -> None:
            self.note_windows.pop(note_id, None)
            self.refresh_main_window()

        def _restore_open_notes(self) -> None:
            self.context_controller.restore()

        def _on_context_changed(self) -> None:
            if self.main_window is not None:
                self.main_window.context_changed()

        def _show_startup_error(self) -> None:
            if self.context_controller is None and self.store is not None:
                self.store.close()
                self.store = None
            if self.error_window is not None:
                self.error_window.present()
                return
            self.error_window = Adw.ApplicationWindow(application=self, title="Pinleaf")
            self.error_window.set_default_size(480, 320)
            status = Adw.StatusPage(title="Could not open your notes", icon_name="dialog-error-symbolic",
                description="Pinleaf could not validate or upgrade its database. Check available disk space and permissions. "
                            "If this database belongs to a newer Pinleaf version, use that version. "
                            "Your database was kept; do not replace it with an empty file. "
                            "Pre-upgrade snapshots, when available, are in the backups folder beside the database.")
            close = Gtk.Button(label="Close", halign=Gtk.Align.CENTER)
            close.connect("clicked", lambda _: self.quit())
            actions = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, halign=Gtk.Align.CENTER)
            if self.backup_service is not None:
                restore = Gtk.Button(label="Restore Backup…")
                restore.connect("clicked", lambda _: self.show_backup(startup_only=True))
                actions.append(restore)
            actions.append(close)
            status.set_child(actions)
            self.error_window.set_content(status)
            self.error_window.present()

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
