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
    font_css_classes,
    font_option_for,
    font_options,
    normalize_text_appearance,
    normalize_text_color,
    system_font_option_count,
)
from pinleaf.ui.dialogs import show_error


class TextAppearanceWindow(Adw.Window):
    def __init__(
        self,
        *,
        parent: Gtk.Window,
        appearance: TextAppearance,
        on_save: Callable[[TextAppearance], None],
        error_heading: str,
        error_body: str,
        on_saved: Callable[[], None] | None = None,
    ) -> None:
        super().__init__()
        self.on_save = on_save
        self.on_saved = on_saved
        self.error_heading = error_heading
        self.error_body = error_body
        self._font_options = font_options()

        self.set_title("Text Appearance")
        self.set_default_size(380, 280)
        self.set_transient_for(parent)
        self.set_modal(True)

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        toolbar.add_top_bar(header)

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
        self.selected_font_family = font_option_for(appearance.font_family).value
        self.font_button = Gtk.MenuButton()
        self.font_button.set_popover(self._build_font_popover())

        self.font_choice_label = Gtk.Label()
        self.font_choice_label.add_css_class("note-font-sample")
        self.font_choice_label.set_xalign(0.0)
        self.font_button.set_child(self.font_choice_label)
        self._sync_font_choice_label()
        return _form_row("Font family", self.font_button)

    def _build_font_popover(self) -> Gtk.Popover:
        popover = Gtk.Popover()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(8)
        box.set_margin_end(8)

        for index, option in enumerate(self._font_options):
            label = Gtk.Label(label=option.label)
            label.add_css_class("note-font-sample")
            label.set_xalign(0.0)
            if option.css_class is not None:
                label.add_css_class(option.css_class)

            button = Gtk.Button()
            button.add_css_class("note-font-choice-button")
            button.set_tooltip_text(option.label)
            button.set_child(label)
            button.connect(
                "clicked",
                lambda _, selected=option.value: self._select_font_family(selected),
            )
            box.append(button)
            if index + 1 == system_font_option_count():
                box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        popover.set_child(box)
        return popover

    def _select_font_family(self, font_family: str | None) -> None:
        self.selected_font_family = font_option_for(font_family).value
        self._sync_font_choice_label()
        popover = self.font_button.get_popover()
        if popover is not None:
            popover.popdown()

    def _sync_font_choice_label(self) -> None:
        option = font_option_for(self.selected_font_family)
        for css_class in font_css_classes():
            self.font_choice_label.remove_css_class(css_class)
        if option.css_class is not None:
            self.font_choice_label.add_css_class(option.css_class)
        self.font_choice_label.set_text(option.label)

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
        appearance = normalize_text_appearance(
            font_family=self.selected_font_family,
            font_size=self.size_spin.get_value_as_int(),
            text_color=_rgba_to_hex(self.color_button.get_rgba()),
        )
        try:
            self.on_save(appearance)
        except Exception:
            show_error(
                self,
                self.error_heading,
                self.error_body,
            )
            return
        if self.on_saved is not None:
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
