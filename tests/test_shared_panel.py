from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, Gtk

from pinleaf.services.note_service import NoteService
from pinleaf.storage.sqlite_store import NoteStore
from pinleaf.ui.main_window import MainWindow
from pinleaf.ui.organization_dialogs import DeleteDialog
from test_shared_migration import schema_five


class SharedPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not Gtk.init_check() or Gdk.Display.get_default() is None:
            raise unittest.SkipTest("GTK display required for Shared panel tests")
        Adw.init()
        cls.application = Adw.Application(application_id="dev.pinleaf.SharedTests", flags=Gio.ApplicationFlags.NON_UNIQUE)
        cls.application.register(None)

    def setUp(self):
        locale = patch.dict("os.environ", {"LC_ALL": "en_US.UTF-8"})
        locale.start()
        self.addCleanup(locale.stop)
        self.store = NoteStore(":memory:")
        self.service = NoteService(self.store)
        self.org = self.service.organization
        self.shared = self.org.repository.shared(self.org.context.profile.id)
        self.open = Mock()
        self.window = self.panel(self.service)
        self.window.refresh()

    def panel(self, service):
        return MainWindow(application=self.application, note_service=service,
                          on_create_note=Mock(), on_open_note=self.open, on_delete_note=Mock())

    def tearDown(self):
        for window in list(self.application.get_windows()):
            window.destroy()
        self.store.close()

    def test_shared_first_plus_no_activate_or_menu_and_nullable_title(self):
        self.assertIs(self.window.list_box.get_first_child(), self.window.group_rows[self.shared.id])
        self.assertIn("shared-create:" + self.shared.id, self.window.focus_targets)
        self.assertNotIn("activate:" + self.shared.id, self.window.focus_targets)
        self.assertNotIn("group-menu:" + self.shared.id, self.window.focus_targets)
        self.assertEqual(self.window.group_label.get_text(), "Shared notes only")
        self.assertIn("Shown alongside", self.window.group_rows[self.shared.id].get_subtitle())
        self.assertNotIn("Active", self.window.group_rows[self.shared.id].get_subtitle())
        project = self.org.create_group("Kubernetes")
        self.window.refresh()
        self.window.focus_targets["shared-create:" + self.shared.id].emit("clicked")
        self.assertEqual(self.service.list_notes()[0].group_id, self.shared.id)
        self.assertEqual(self.org.context.group_id, project.id)

    def test_shared_row_opens_directly_with_project_active_and_hidden_styling(self):
        note = self.service.create_note()
        self.service.close_note(note.id, width=320, height=280)
        project = self.org.create_group("Kubernetes")
        self.window.refresh()
        row = self.window.focus_targets["note:" + note.id]
        with patch("pinleaf.ui.main_window.InspectNoteDialog") as inspect:
            row.get_parent().emit("row-activated", row)
            inspect.assert_not_called()
        self.open.assert_called_once_with(note.id)
        self.assertIn("Hidden note", row.get_tooltip_text())
        self.assertEqual(self.org.context.group_id, project.id)

    def test_foreign_shared_inspection_names_profile_switch(self):
        note = self.service.create_note()
        self.service.update_content(note.id, "AWS tags")
        foreign = self.org.create_profile("Freelancer")
        self.window.search_entry.set_text("aws")
        self.window.scope.set_selected(2)
        self.window.refresh()
        row = self.window.list_box.get_first_child()
        self.assertIn("Shared", row.get_tooltip_text())
        with patch("pinleaf.ui.main_window.InspectNoteDialog") as inspect, patch.object(self.window, "_present_dialog"):
            self.window._inspect_or_open(self.store.get(note.id))
            self.assertEqual(inspect.call_args.kwargs["open_label"], "Switch profile and open")
        self.assertEqual(self.org.context.identity, (foreign.id, None))

    def test_switching_between_null_profiles_clears_search_and_noop_keeps_it(self):
        initial = self.org.context.profile
        other = self.org.create_profile("Freelancer")
        self.window.search_entry.set_text("aws")
        self.window.execute(lambda: self.org.activate_profile(other.id))
        self.assertEqual(self.window.search_entry.get_text(), "aws")
        self.window.execute(lambda: self.org.activate_profile(initial.id))
        self.assertEqual(self.window.search_entry.get_text(), "")

    def test_portuguese_labels_and_current_context_scope(self):
        with patch.dict("os.environ", {"LC_ALL": "pt_BR.UTF-8"}):
            panel = self.panel(self.service)
            panel.refresh()
            self.assertEqual(panel.group_label.get_text(), "Somente notas compartilhadas")
            self.assertEqual(panel.group_rows[self.shared.id].get_title(), "Compartilhado")
            self.assertEqual(panel.scope.get_model().get_string(0), "Contexto atual")

    def test_delete_shared_only_profile_summary_restores_destination_ordinary(self):
        original = self.org.context.profile
        project = self.org.create_group("Kubernetes")
        source = self.org.create_profile("Freelancer")
        self.service.create_note()
        dialog = DeleteDialog(self.window, self.org, lambda action, **_: action(), self.org.preview_deletion("profile", source.id))
        self.assertTrue(dialog.picker.destination.is_shared)
        self.assertIn(f"{original.name} / {project.name}", dialog.context_label.get_text())
        dialog.confirm.emit("clicked")
        self.assertEqual(self.org.context.identity, (original.id, project.id))

    def test_conversion_notice_lists_renames_plainly_and_dismisses_durably(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notes.sqlite3"
            schema_five(path)
            store = NoteStore(path)
            panel = self.panel(NoteService(store))
            panel.refresh()
            notice = panel._build_migration_notice()
            label = notice.get_first_child()
            self.assertIn("General is now Shared", label.get_text())
            self.assertIn("Shared → Shared (3)", label.get_text())
            self.assertNotIn("完整文本", label.get_text())
            self.assertFalse(label.get_use_markup())
            label.get_next_sibling().emit("clicked")
            self.assertFalse(notice.get_visible())
            panel.destroy()
            store.close()
            store = NoteStore(path)
            self.assertIsNone(store.migration_notice())
            store.close()
