from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gtk

from pinleaf.appearance import (
    MAX_FONT_SIZE,
    MIN_FONT_SIZE,
    TextAppearance,
    font_option_for,
    font_options,
    normalize_text_color,
)
from pinleaf.services.note_service import NoteService
from pinleaf.ui.dialogs import show_error


class TextAppearanceWindow(Adw.Window):
    def __init__(
        self,
        *,
        parent: Gtk.Window,
        note_service: NoteService,
        on_saved: Callable[[], None],
    ) -> None:
        super().__init__()
        self.note_service = note_service
        self.on_saved = on_saved
        self._font_options = font_options()

        self.set_title("Text Appearance")
        self.set_default_size(380, 280)
        self.set_transient_for(parent)
        self.set_modal(True)

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        toolbar.add_top_bar(header)

        appearance = note_service.get_default_text_appearance()
        toolbar.set_content(self._build_content(appearance))
        self.set_content(toolbar)

    def _build_content(self, appearance: TextAppearance) -> Gtk.Widget:
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content.set_margin_top(18)
        content.set_margin_bottom(18)
        content.set_margin_start(18)
        content.set_margin_end(18)

        form = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        form.append(self._build_font_row(appearance))
        form.append(self._build_size_row(appearance))
        form.append(self._build_color_row(appearance))
        content.append(form)

        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        actions.set_halign(Gtk.Align.END)

        cancel = Gtk.Button(label="Cancel")
        cancel.connect("clicked", lambda _: self.close())
        actions.append(cancel)

        save = Gtk.Button(label="Save")
        save.add_css_class("suggested-action")
        save.connect("clicked", lambda _: self._save())
        actions.append(save)
        content.append(actions)

        return content

    def _build_font_row(self, appearance: TextAppearance) -> Gtk.Widget:
        self.font_combo = Gtk.ComboBoxText()
        selected_index = 0
        selected = font_option_for(appearance.font_family).value
        for index, option in enumerate(self._font_options):
            self.font_combo.append(str(index), option.label)
            if option.value == selected:
                selected_index = index
        self.font_combo.set_active(selected_index)
        return _form_row("Font family", self.font_combo)

    def _build_size_row(self, appearance: TextAppearance) -> Gtk.Widget:
        adjustment = Gtk.Adjustment(
            value=appearance.font_size,
            lower=MIN_FONT_SIZE,
            upper=MAX_FONT_SIZE,
            step_increment=1,
            page_increment=4,
            page_size=0,
        )
        self.size_spin = Gtk.SpinButton.new(adjustment, 1, 0)
        self.size_spin.set_numeric(True)
        return _form_row("Font size", self.size_spin)

    def _build_color_row(self, appearance: TextAppearance) -> Gtk.Widget:
        rgba = Gdk.RGBA()
        rgba.parse(normalize_text_color(appearance.text_color))
        self.color_button = Gtk.ColorButton.new_with_rgba(rgba)
        return _form_row("Text color", self.color_button)

    def _save(self) -> None:
        active_id = self.font_combo.get_active_id()
        selected_index = int(active_id) if active_id is not None else 0
        font_family = self._font_options[selected_index].value
        try:
            self.note_service.set_default_text_appearance(
                font_family=font_family,
                font_size=self.size_spin.get_value_as_int(),
                text_color=_rgba_to_hex(self.color_button.get_rgba()),
            )
        except Exception:
            show_error(
                self,
                "Could not save text appearance",
                "New notes may keep using the previous text appearance.",
            )
            return
        self.on_saved()
        self.close()


def _form_row(label_text: str, control: Gtk.Widget) -> Gtk.Widget:
    row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    row.set_hexpand(True)

    label = Gtk.Label(label=label_text)
    label.set_xalign(0.0)
    label.set_hexpand(True)
    row.append(label)

    control.set_hexpand(False)
    row.append(control)
    return row


def _rgba_to_hex(rgba: Gdk.RGBA) -> str:
    red = round(rgba.red * 255)
    green = round(rgba.green * 255)
    blue = round(rgba.blue * 255)
    return f"#{red:02X}{green:02X}{blue:02X}"
