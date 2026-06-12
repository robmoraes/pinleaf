from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk

from pinleaf.models import Note, NoteColor
from pinleaf.services.autosave import Autosave, ScheduledCall
from pinleaf.services.note_service import NoteService
from pinleaf.ui.dialogs import show_error


class GLibScheduledCall:
    def __init__(self, source_id: int) -> None:
        self.source_id = source_id
        self.cancelled = False

    def cancel(self) -> None:
        if not self.cancelled:
            GLib.source_remove(self.source_id)
            self.cancelled = True


def schedule_on_main_loop(delay_seconds: float, callback: Callable[[], None]) -> ScheduledCall:
    def run() -> bool:
        callback()
        return False

    return GLibScheduledCall(GLib.timeout_add(int(delay_seconds * 1000), run))


class NoteWindow(Adw.ApplicationWindow):
    def __init__(
        self,
        *,
        application: Adw.Application,
        note: Note,
        note_service: NoteService,
        on_closed: Callable[[str], None],
        on_changed: Callable[[], None],
    ) -> None:
        super().__init__(application=application)
        self.note = note
        self.note_service = note_service
        self.on_closed = on_closed
        self.on_changed = on_changed
        self.autosave = Autosave(self._save_content, scheduler=schedule_on_main_loop)
        self._loading_buffer = False

        self.set_title("Pinleaf Note")
        self.set_default_size(note.width, note.height)
        self.add_css_class("note-window")
        self.add_css_class(f"note-{note.color.value}")

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        toolbar.add_top_bar(header)

        color_button = Gtk.MenuButton(label="Color")
        color_button.set_popover(self._build_color_popover())
        header.pack_end(color_button)

        self.text_view = Gtk.TextView()
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.text_view.set_vexpand(True)
        self.text_view.set_hexpand(True)
        self.text_view.add_css_class("note-editor")

        buffer = self.text_view.get_buffer()
        self._loading_buffer = True
        buffer.set_text(note.content)
        self._loading_buffer = False
        buffer.connect("changed", self._on_text_changed)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_child(self.text_view)
        toolbar.set_content(scroller)
        self.set_content(toolbar)

        self.connect("close-request", self._on_close_request)

    def flush_pending_changes(self) -> bool:
        saved = self.autosave.flush()
        if not saved:
            show_error(self, "Could not save note", "The latest change may not have been saved.")
        return saved

    def _build_color_popover(self) -> Gtk.Popover:
        popover = Gtk.Popover()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(8)
        box.set_margin_end(8)

        for color in NoteColor:
            button = Gtk.Button(label=color.value.title())
            button.connect("clicked", lambda _, selected=color: self._set_color(selected))
            box.append(button)

        popover.set_child(box)
        return popover

    def _set_color(self, color: NoteColor) -> None:
        previous = self.note.color
        if previous == color:
            return
        try:
            self.note = self.note_service.update_color(self.note.id, color)
        except Exception:
            show_error(self, "Could not save color", "The selected note color may not have been saved.")
            return

        self.remove_css_class(f"note-{previous.value}")
        self.add_css_class(f"note-{color.value}")
        self.on_changed()

    def _on_text_changed(self, buffer: Gtk.TextBuffer) -> None:
        if self._loading_buffer:
            return
        start, end = buffer.get_bounds()
        content = buffer.get_text(start, end, True)
        self.autosave.schedule(self.note.id, content)
        self.on_changed()

    def _save_content(self, note_id: str, content: str) -> None:
        self.note = self.note_service.update_content(note_id, content)
        self.on_changed()

    def _on_close_request(self, _: Gtk.Window) -> bool:
        self.flush_pending_changes()
        self.note_service.close_note(
            self.note.id,
            width=max(self.get_width(), 1),
            height=max(self.get_height(), 1),
            position_x=None,
            position_y=None,
        )
        self.on_closed(self.note.id)
        return False
