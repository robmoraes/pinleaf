from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from pinleaf.models import Note


def show_error(parent: Gtk.Window | None, heading: str, body: str) -> None:
    dialog = Adw.MessageDialog.new(parent, heading, body)
    dialog.add_response("ok", "OK")
    dialog.set_default_response("ok")
    dialog.present()


def confirm_delete(parent: Gtk.Window, note: Note, on_confirm: Callable[[], None]) -> None:
    if not note.content.strip():
        on_confirm()
        return

    preview = note.content.strip().splitlines()[0]
    if len(preview) > 80:
        preview = f"{preview[:77]}..."

    dialog = Adw.MessageDialog.new(
        parent,
        "Delete note?",
        f'This will remove "{preview}" from Pinleaf.',
    )
    dialog.add_response("cancel", "Cancel")
    dialog.add_response("delete", "Delete")
    dialog.set_default_response("cancel")
    dialog.set_close_response("cancel")
    dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)

    def on_response(_: Adw.MessageDialog, response: str) -> None:
        if response == "delete":
            on_confirm()

    dialog.connect("response", on_response)
    dialog.present()


def choose_note_action(
    parent: Gtk.Window,
    *,
    on_hide: Callable[[], None],
    on_delete: Callable[[], None],
    on_finished: Callable[[], None],
) -> Adw.MessageDialog:
    dialog = Adw.MessageDialog.new(
        parent,
        "What do you want to do with this note?",
        "You can hide it from the desktop or delete it permanently.",
    )
    dialog.add_response("cancel", "Cancel")
    dialog.add_response("hide", "Hide Note")
    dialog.add_response("delete", "Delete Note")
    dialog.set_default_response("cancel")
    dialog.set_close_response("cancel")
    dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)

    def on_response(_: Adw.MessageDialog, response: str) -> None:
        on_finished()
        if response == "hide":
            on_hide()
        elif response == "delete":
            on_delete()

    dialog.connect("response", on_response)
    dialog.present()
    return dialog
