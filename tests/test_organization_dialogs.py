from __future__ import annotations

import unittest
from unittest.mock import Mock

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, Gtk

from pinleaf.services.note_service import NoteService
from pinleaf.storage.sqlite_store import NoteStore
from pinleaf.ui.organization_dialogs import DeleteDialog, ManageProfilesDialog, MoveDialog, NameDialog


class OrganizationDialogsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not Gtk.init_check() or Gdk.Display.get_default() is None:
            raise unittest.SkipTest("GTK display required for organization dialogs")
        Adw.init()
        cls.application = Adw.Application(application_id="dev.pinleaf.DialogTests", flags=Gio.ApplicationFlags.NON_UNIQUE)
        cls.application.register(None)

    def setUp(self) -> None:
        self.store = NoteStore(":memory:")
        self.service = NoteService(self.store)
        self.org = self.service.organization
        self.org.create_group("General")
        self.original = self.org.context
        self.parent = Adw.ApplicationWindow(application=self.application)
        self.dialogs = []

    def tearDown(self) -> None:
        for dialog in self.dialogs:
            dialog.destroy()
        self.parent.destroy()
        self.store.close()

    def execute(self, action, **_kwargs):
        return action()

    def keep(self, dialog):
        self.dialogs.append(dialog)
        return dialog

    def test_create_validation_and_create_and_activate(self) -> None:
        dialog = self.keep(NameDialog(self.parent, self.org, self.execute, "group"))
        self.assertEqual(dialog.confirm.get_label(), "Create and activate")
        dialog.entry.set_text("Compartilhado")
        dialog.confirm.emit("clicked")
        self.assertTrue(dialog.error.get_visible())
        self.assertEqual(self.org.context, self.original)
        dialog.entry.set_text("Financeiro")
        dialog.confirm.emit("clicked")
        self.assertEqual(self.org.context.group.name, "Financeiro")

    def test_cancel_makes_no_writes_and_rename_keeps_context(self) -> None:
        dialog = self.keep(NameDialog(self.parent, self.org, self.execute, "profile"))
        before = self.store.connection.total_changes
        dialog.entry.set_text("Freelancer")
        dialog.cancel.emit("clicked")
        self.assertEqual(self.store.connection.total_changes, before)
        rename = self.keep(NameDialog(self.parent, self.org, self.execute, "profile",
                                     container_id=self.original.profile.id, name="Personal"))
        rename.entry.set_text("Pessoal")
        rename.confirm.emit("clicked")
        self.assertEqual(self.org.context.group.id, self.original.group.id)
        self.assertEqual(self.org.context.profile.name, "Pessoal")

    def test_move_requires_different_destination_and_preserves_hidden(self) -> None:
        note = self.service.create_note()
        self.service.close_note(note.id, width=320, height=240)
        group = self.org.create_group("Financeiro")
        self.org.activate_group(self.original.group.id)
        dialog = self.keep(MoveDialog(self.parent, self.org, self.execute, note.id))
        self.assertFalse(dialog.confirm.get_sensitive())
        index = next(index for index, item in enumerate(dialog.picker.groups) if item.id == group.id)
        dialog.picker.group.set_selected(index)
        self.assertTrue(dialog.confirm.get_sensitive())
        self.assertIn("Financeiro", dialog.picker.path.get_text())
        dialog.confirm.emit("clicked")
        self.assertEqual(self.store.get(note.id).group_id, group.id)
        self.assertFalse(self.store.get(note.id).is_open)
        self.assertEqual(self.org.context, self.original)

    def test_delete_defaults_counts_destinations_and_fallback(self) -> None:
        group = self.org.create_group("Projeto")
        note = self.service.create_note()
        self.service.close_note(note.id, width=320, height=240)
        dialog = self.keep(DeleteDialog(self.parent, self.org, self.execute, self.org.preview_deletion("group", group.id)))
        self.assertTrue(dialog.move.get_active())
        self.assertIs(dialog.get_default_widget(), dialog.cancel)
        self.assertIn("1 note, including hidden", dialog.summary.get_text())
        self.assertNotIn(group.id, [item.id for item in dialog.picker.groups])
        self.assertEqual(dialog.confirm.get_label(), "Delete group and move notes")
        self.assertFalse(dialog.confirm.has_css_class("destructive-action"))
        dialog.confirm.emit("clicked")
        self.assertIsNone(self.org.context.group)
        self.assertEqual(self.store.get(note.id).group_id, self.org.repository.shared(self.original.profile.id).id)
        self.assertFalse(self.store.get(note.id).is_open)

    def test_stale_deletion_requires_new_confirmation_and_destination_review(self) -> None:
        group = self.org.create_group("Projeto")
        self.service.create_note()
        dialog = self.keep(DeleteDialog(self.parent, self.org, self.execute, self.org.preview_deletion("group", group.id)))
        self.service.create_note()
        dialog.confirm.emit("clicked")
        self.assertTrue(dialog.error.get_visible())
        self.assertEqual(dialog.preview.note_count, 2)
        self.assertEqual(len(self.store.list_notes(group_id=group.id)), 2)
        dialog.confirm.emit("clicked")
        self.assertEqual(len(self.store.list_notes(group_id=self.org.repository.shared(self.original.profile.id).id)), 2)

    def test_delete_active_profile_requires_replacement_and_destructive_action(self) -> None:
        self.org.create_profile("Freelancer")
        note = self.service.create_note()
        dialog = self.keep(DeleteDialog(self.parent, self.org, self.execute,
                                       self.org.preview_deletion("profile", self.org.context.profile.id)))
        dialog.remove.set_active(True)
        self.assertTrue(dialog.replacement.get_visible())
        self.assertTrue(dialog.confirm.has_css_class("destructive-action"))
        self.assertEqual(dialog.confirm.get_label(), "Delete profile and 1 note")
        dialog.confirm.emit("clicked")
        self.assertIsNone(self.store.get(note.id))
        self.assertEqual(self.org.context, self.original)

    def test_empty_container_needs_no_destination_and_last_profile_is_protected(self) -> None:
        manager = self.keep(ManageProfilesDialog(self.parent, self.org, self.execute))
        # Protection is also enforced in the service, regardless of UI state.
        from pinleaf.organization import ProtectedContainerError
        with self.assertRaises(ProtectedContainerError):
            self.org.preview_deletion("profile", self.original.profile.id)
        group = self.org.create_group("Vazio")
        dialog = self.keep(DeleteDialog(self.parent, self.org, self.execute, self.org.preview_deletion("group", group.id)))
        self.assertFalse(dialog.picker.get_visible())
        self.assertEqual(dialog.confirm.get_label(), "Delete group")
        dialog.confirm.emit("clicked")
        self.assertEqual(self.org.context.profile, self.original.profile)
        self.assertIsNone(self.org.context.group)

    def test_failed_command_keeps_dialog_available_for_retry(self) -> None:
        execute = Mock(side_effect=OSError("unavailable"))
        dialog = self.keep(NameDialog(self.parent, self.org, execute, "profile"))
        dialog.entry.set_text("Freelancer")
        dialog.confirm.emit("clicked")
        self.assertTrue(dialog.error.get_visible())
        self.assertEqual(self.org.context, self.original)
        execute.side_effect = lambda action, **kwargs: action()
        dialog.confirm.emit("clicked")
        self.assertEqual(self.org.context.profile.name, "Freelancer")
