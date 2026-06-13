from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk

from pinleaf.appearance import font_css_classes, font_option_for, font_options
from pinleaf.models import Note, NoteColor
from pinleaf.services.autosave import Autosave, ScheduledCall
from pinleaf.services.note_service import NoteService
from pinleaf.ui.dialogs import show_error
from pinleaf.ui.geometry import (
    WindowGeometry,
    apply_window_geometry,
    capture_window_geometry,
    normalize_geometry,
)


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
        apply_window_geometry(
            self,
            normalize_geometry(note.width, note.height, note.position_x, note.position_y),
        )
        self.add_css_class("note-window")
        self.add_css_class(f"note-{note.color.value}")

        toolbar = Adw.ToolbarView()
        self.header = Adw.HeaderBar()
        toolbar.add_top_bar(self.header)
        self.header_controls: list[Gtk.Widget] = []

        color_button = Gtk.MenuButton(label="Color")
        color_button.set_popover(self._build_color_popover())
        self.header.pack_end(color_button)
        self.header_controls.append(color_button)

        font_button = Gtk.MenuButton(label="Font")
        font_button.set_popover(self._build_font_popover())
        self.header.pack_end(font_button)
        self.header_controls.append(font_button)

        self.text_view = Gtk.TextView()
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.text_view.set_vexpand(True)
        self.text_view.set_hexpand(True)
        self.text_view.add_css_class("note-editor")
        self._apply_font_class(note.font_family)

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
        self.connect("notify::is-active", self._on_active_changed)

    def flush_pending_changes(self) -> bool:
        saved = self.autosave.flush()
        if not saved:
            show_error(self, "Could not save note", "The latest change may not have been saved.")
        return saved

    def save_window_state(self) -> None:
        geometry = self._capture_geometry()
        self.note = self.note_service.save_open_note_window(
            self.note.id,
            width=geometry.width,
            height=geometry.height,
            position_x=geometry.position_x,
            position_y=geometry.position_y,
        )

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

    def _build_font_popover(self) -> Gtk.Popover:
        popover = Gtk.Popover()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(8)
        box.set_margin_end(8)

        for option in font_options():
            button = Gtk.Button(label=option.label)
            button.connect("clicked", lambda _, selected=option.value: self._set_font_family(selected))
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

    def _set_font_family(self, font_family: str | None) -> None:
        selected = font_option_for(font_family).value
        if self.note.font_family == selected:
            return
        try:
            self.note = self.note_service.update_font_family(self.note.id, selected)
        except Exception:
            show_error(self, "Could not save font", "The selected note font may not have been saved.")
            return

        self._apply_font_class(self.note.font_family)
        self.on_changed()

    def _apply_font_class(self, font_family: str | None) -> None:
        for css_class in font_css_classes():
            self.text_view.remove_css_class(css_class)
        option = font_option_for(font_family)
        if option.css_class is not None:
            self.text_view.add_css_class(option.css_class)

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

    def _on_active_changed(self, *_: object) -> None:
        self._sync_header_visibility()

    def _sync_header_visibility(self) -> None:
        is_active = self.is_active()
        self.header.set_show_title(is_active)
        self.header.set_show_start_title_buttons(is_active)
        self.header.set_show_end_title_buttons(is_active)
        for control in self.header_controls:
            control.set_visible(is_active)

    def _on_close_request(self, _: Gtk.Window) -> bool:
        self.flush_pending_changes()
        geometry = self._capture_geometry()
        self.note = self.note_service.close_note(
            self.note.id,
            width=geometry.width,
            height=geometry.height,
            position_x=geometry.position_x,
            position_y=geometry.position_y,
        )
        self.on_closed(self.note.id)
        return False

    def _capture_geometry(self) -> WindowGeometry:
        return capture_window_geometry(
            self,
            fallback_position_x=self.note.position_x,
            fallback_position_y=self.note.position_y,
        )
