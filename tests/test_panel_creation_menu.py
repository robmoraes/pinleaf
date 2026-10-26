from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk

from pinleaf.services.note_service import NoteService
from pinleaf.storage.sqlite_store import NoteStore
from pinleaf.ui.main_window import MainWindow
from pinleaf.ui.organization_dialogs import NameDialog


class PanelCreationMenuTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not Gtk.init_check() or Gdk.Display.get_default() is None:
            raise unittest.SkipTest("GTK display required for creation menu tests")
        Adw.init()
        cls.application = Adw.Application(application_id="dev.pinleaf.CreationTests",
                                          flags=Gio.ApplicationFlags.NON_UNIQUE)
        cls.application.register(None)

    def setUp(self) -> None:
        self.store = NoteStore(":memory:")
        self.service = NoteService(self.store)
        self.org = self.service.organization
        self.window = MainWindow(application=self.application, note_service=self.service,
                                 on_create_note=lambda: self.window.execute(self.service.create_note, affected_ids=set()),
                                 on_open_note=Mock(), on_delete_note=Mock())
        self.dialogs = []
        self.window.refresh()
        self.window.present()
        self.drain_events()

    def tearDown(self) -> None:
        for dialog in self.dialogs:
            dialog.destroy()
        self.window.destroy()
        self.store.close()

    def drain_events(self) -> None:
        while GLib.MainContext.default().pending():
            GLib.MainContext.default().iteration(False)

    def actions(self) -> dict[str, Gtk.Button]:
        self.window.new_button.popup()
        self.drain_events()
        actions = {}
        child = self.window.new_button.get_popover().get_child().get_first_child()
        while child is not None:
            actions[child.get_child().get_text()] = child
            child = child.get_next_sibling()
        return actions

    def group_dialog(self) -> NameDialog:
        with patch.object(self.window, "_present_dialog", wraps=self.window._present_dialog) as present:
            self.actions()["New Group…"].emit("clicked")
            dialog = present.call_args.args[0]
        self.dialogs.append(dialog)
        self.drain_events()
        self.assertIsInstance(dialog, NameDialog)
        self.assertFalse(self.window.new_button.get_popover().get_visible())
        return dialog

    def test_menu_dismissal_writes_nothing_and_new_note_obeys_current_context(self) -> None:
        context = self.org.context
        changes = self.store.connection.total_changes
        self.assertEqual(set(self.actions()), {"New Note", "New Group…"})
        self.window.new_button.popdown()
        self.drain_events()
        self.assertEqual(self.store.connection.total_changes, changes)
        self.assertEqual(self.org.context, context)
        self.actions()["New Note"].emit("clicked")
        shared_note = self.service.list_notes()[0]
        self.assertEqual(shared_note.group_id, self.org.repository.shared(context.profile.id).id)
        self.assertEqual(self.org.context, context)
        self.assertFalse(self.window.new_button.get_popover().get_visible())
        project = self.org.create_group("Kubernetes")
        self.window.context_changed()
        self.window.refresh()
        self.actions()["New Note"].emit("clicked")
        self.assertEqual(len(self.store.list_notes(group_id=project.id)), 1)
        self.assertEqual(self.org.context.group_id, project.id)

    def test_group_menu_preserves_cancel_validation_and_create_and_activate(self) -> None:
        project = self.org.create_group("Project A")
        self.window.refresh()
        context = self.org.context
        dialog = self.group_dialog()
        changes = self.store.connection.total_changes
        dialog.entry.set_text("Cancelled project")
        dialog.cancel.emit("clicked")
        self.assertEqual(self.store.connection.total_changes, changes)
        self.assertEqual(self.org.context, context)
        dialog = self.group_dialog()
        self.assertEqual(dialog.confirm.get_label(), "Create and activate")
        for name in ("Shared", project.name):
            dialog.entry.set_text(name)
            dialog.confirm.emit("clicked")
            self.assertTrue(dialog.error.get_visible())
            self.assertTrue(dialog.get_visible())
            self.assertEqual(self.org.context, context)
        dialog.entry.set_text("Project B")
        dialog.confirm.emit("clicked")
        self.assertEqual(self.org.context.profile, context.profile)
        self.assertEqual(self.org.context.group.name, "Project B")
        self.assertEqual(self.window.new_button.get_label(), "New")
        self.actions()["New Note"].emit("clicked")
        self.assertEqual(len(self.store.list_notes(group_id=self.org.context.group_id)), 1)
