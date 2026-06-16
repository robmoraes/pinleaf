from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, tzinfo

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, Pango

from pinleaf.appearance import TextAppearance
from pinleaf.models import Note
from pinleaf.services.note_service import NoteService
from pinleaf.ui.about import show_about
from pinleaf.ui.dialogs import confirm_delete
from pinleaf.ui.text_appearance_window import TextAppearanceWindow


class MainWindow(Adw.ApplicationWindow):
    def __init__(
        self,
        *,
        application: Adw.Application,
        note_service: NoteService,
        on_create_note: Callable[[], None],
        on_open_note: Callable[[str], None],
        on_delete_note: Callable[[str], None],
    ) -> None:
        super().__init__(application=application)
        self.note_service = note_service
        self.on_create_note = on_create_note
        self.on_open_note = on_open_note
        self.on_delete_note = on_delete_note
        self.text_appearance_window: TextAppearanceWindow | None = None

        self.set_title("Pinleaf")
        self.set_default_size(460, 560)

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        toolbar.add_top_bar(header)

        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name("open-menu-symbolic")
        menu_button.set_tooltip_text("Main menu")
        menu_button.set_popover(self._build_menu())
        header.pack_end(menu_button)

        new_button = Gtk.Button(label="New")
        new_button.set_tooltip_text("Create note")
        new_button.connect("clicked", lambda _: self.on_create_note())
        header.pack_start(new_button)

        self.stack = Gtk.Stack()
        self.stack.set_vexpand(True)
        self.stack.set_hexpand(True)
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)

        self.empty = self._build_empty_state()
        self.list_box = Gtk.ListBox()
        self.list_box.add_css_class("boxed-list")
        self.list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.list_box.connect("row-activated", self._on_row_activated)

        scroller = Gtk.ScrolledWindow()
        scroller.set_vexpand(True)
        scroller.set_hexpand(True)
        scroller.set_child(self.list_box)
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content.set_vexpand(True)
        content.set_hexpand(True)
        content.set_margin_top(18)
        content.set_margin_bottom(18)
        content.set_margin_start(18)
        content.set_margin_end(18)
        content.append(self.stack)

        self.stack.add_named(self.empty, "empty")
        self.stack.add_named(scroller, "list")

        toolbar.set_content(content)
        self.set_content(toolbar)

    def _build_menu(self) -> Gtk.Popover:
        popover = Gtk.Popover()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(8)
        box.set_margin_end(8)

        text_appearance = Gtk.Button()
        text_appearance.add_css_class("flat")
        text_appearance.set_tooltip_text("Configure default text appearance for new notes")
        text_appearance.connect("clicked", lambda _: self._show_text_appearance_window())

        self.text_appearance_label = Gtk.Label()
        text_appearance.set_child(self.text_appearance_label)
        box.append(text_appearance)

        box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        about = Gtk.Button(label="About Pinleaf")
        about.add_css_class("flat")
        about.connect("clicked", lambda _: show_about(self))
        box.append(about)

        self._sync_text_appearance_label()
        popover.set_child(box)
        return popover

    def _show_text_appearance_window(self) -> None:
        if self.text_appearance_window is not None:
            self.text_appearance_window.present()
            return
        self.text_appearance_window = TextAppearanceWindow(
            parent=self,
            appearance=self.note_service.get_default_text_appearance(),
            on_save=self._save_default_text_appearance,
            error_heading="Could not save text settings",
            error_body="New notes may keep using the previous text settings.",
            on_saved=self._sync_text_appearance_label,
        )
        self.text_appearance_window.connect(
            "close-request",
            self._on_text_appearance_window_closed,
        )
        self.text_appearance_window.present()

    def _on_text_appearance_window_closed(self, _: Gtk.Window) -> bool:
        self.text_appearance_window = None
        return False

    def _sync_text_appearance_label(self) -> None:
        label = getattr(self, "text_appearance_label", None)
        if label is None:
            return
        label.set_text("Text Settings")

    def _save_default_text_appearance(self, appearance: TextAppearance) -> None:
        self.note_service.set_default_text_appearance(
            font_family=appearance.font_family,
            font_size=appearance.font_size,
            text_color=appearance.text_color,
        )

    def refresh(self) -> None:
        notes = self.note_service.list_notes()
        self._clear_list()
        for note in notes:
            self.list_box.append(self._build_row(note))
        self.stack.set_visible_child_name("list" if notes else "empty")

    def _build_empty_state(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_valign(Gtk.Align.CENTER)
        box.set_halign(Gtk.Align.CENTER)

        title = Gtk.Label(label="No notes yet")
        title.add_css_class("title-2")
        box.append(title)

        button = Gtk.Button(label="Create Note")
        button.add_css_class("suggested-action")
        button.connect("clicked", lambda _: self.on_create_note())
        box.append(button)
        return box

    def _build_row(self, note: Note) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow()
        row.set_selectable(True)
        row.set_activatable(True)
        row.add_css_class("note-list-row")
        row.note_id = note.id  # type: ignore[attr-defined]

        container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        container.add_css_class("note-list-row-content")
        container.set_vexpand(False)
        container.set_hexpand(True)
        container.set_margin_top(10)
        container.set_margin_bottom(10)
        container.set_margin_start(12)
        container.set_margin_end(12)

        color = Gtk.Box()
        color.add_css_class("note-color-dot")
        color.add_css_class(f"note-{note.color.value}")
        color.set_valign(Gtk.Align.CENTER)
        container.append(color)

        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        text.set_hexpand(True)

        preview = Gtk.Label(label=_preview(note))
        preview.set_xalign(0)
        preview.set_ellipsize(Pango.EllipsizeMode.END)
        text.append(preview)

        updated = Gtk.Label(label=f"Updated {_format_timestamp(note.updated_at)}")
        updated.add_css_class("dim-label")
        updated.set_xalign(0)
        updated.set_ellipsize(Pango.EllipsizeMode.END)
        text.append(updated)
        container.append(text)

        delete = Gtk.Button(label="Delete")
        delete.add_css_class("flat")
        delete.set_valign(Gtk.Align.CENTER)
        delete.set_tooltip_text("Delete note")
        delete.connect("clicked", lambda _: self._confirm_delete(note))
        container.append(delete)

        row.set_child(container)
        return row

    def _clear_list(self) -> None:
        child = self.list_box.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            self.list_box.remove(child)
            child = next_child

    def _on_row_activated(self, _: Gtk.ListBox, row: Gtk.ListBoxRow) -> None:
        note_id = getattr(row, "note_id", None)
        if note_id is not None:
            self.on_open_note(note_id)

    def _confirm_delete(self, note: Note) -> None:
        confirm_delete(self, note, lambda: self.on_delete_note(note.id))


def _preview(note: Note) -> str:
    text = " ".join(note.content.split())
    if not text:
        return "Empty note"
    return text if len(text) <= 100 else f"{text[:97]}..."


def _format_timestamp(value: str, local_tz: tzinfo | None = None) -> str:
    try:
        timestamp = datetime.fromisoformat(value)
    except ValueError:
        return value
    if timestamp.tzinfo is None:
        timestamp = timestamp.astimezone()
    local = timestamp.astimezone(local_tz)
    return local.strftime("%b %-d, %Y %-I:%M %p %Z")
