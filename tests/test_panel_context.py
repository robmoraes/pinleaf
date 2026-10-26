from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk

from pinleaf.services.context_controller import ContextController, TransitionError
from pinleaf.services.note_service import NoteService
from pinleaf.storage.sqlite_store import NoteStore
from pinleaf.ui.main_window import MainWindow
from pinleaf.ui.note_window import NoteWindow


class PanelContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not Gtk.init_check() or Gdk.Display.get_default() is None:
            raise unittest.SkipTest("GTK display required for panel context tests")
        Adw.init()
        cls.application = Adw.Application(application_id="dev.pinleaf.PanelTests", flags=Gio.ApplicationFlags.NON_UNIQUE)
        cls.application.register(None)

    def setUp(self) -> None:
        self.store = NoteStore(":memory:")
        self.service = NoteService(self.store)
        self.org = self.service.organization
        self.org.create_group("General")
        self.original = self.org.context
        self.open = Mock()
        self.window = MainWindow(application=self.application, note_service=self.service,
                                 on_create_note=Mock(), on_open_note=self.open, on_delete_note=Mock())
        self.window.refresh()
        self.windows = {}

    def tearDown(self) -> None:
        for editor in self.windows.values():
            editor.dispose_for_context()
        for window in list(self.application.get_windows()):
            window.destroy()
        self.store.close()

    def search(self, text: str, scope: int = 0) -> None:
        self.window.search_entry.set_text(text)
        self.window.scope.set_selected(scope)
        self.window.search_entry.emit("search-changed")

    def test_browsing_groups_never_activates_and_expansion_survives_search(self) -> None:
        other = self.org.create_group("Agenda")
        note = self.service.create_note()
        self.service.update_content(note.id, "café")
        self.org.activate_group(self.original.group.id)
        self.window.refresh()
        self.window.group_rows[other.id].set_expanded(True)
        self.window.group_rows[self.original.group.id].set_expanded(False)
        self.assertEqual(self.org.context, self.original)
        self.search("cafe", 1)
        self.assertEqual(set(self.window.group_rows), {other.id})
        self.assertTrue(self.window.group_rows[other.id].get_expanded())
        self.search("")
        self.assertTrue(self.window.group_rows[other.id].get_expanded())
        self.assertFalse(self.window.group_rows[self.original.group.id].get_expanded())

    def test_nested_row_open_and_inactive_inspection_are_distinct(self) -> None:
        note = self.service.create_note()
        self.window.refresh()
        row = self.window.focus_targets[f"note:{note.id}"]
        self.assertIsInstance(row.get_parent(), Gtk.ListBox)
        row.get_parent().emit("row-activated", row)
        self.open.assert_called_once_with(note.id)
        self.org.create_group("Agenda")
        self.window.refresh()
        row = self.window.focus_targets[f"note:{note.id}"]
        with patch("pinleaf.ui.main_window.InspectNoteDialog") as inspection:
            row.get_parent().emit("row-activated", row)
            inspection.assert_called_once()
        self.open.assert_called_once_with(note.id)

    def test_global_search_breadcrumbs_and_actual_context_reset(self) -> None:
        note = self.service.create_note()
        self.service.update_content(note.id, "café")
        other = self.org.create_profile("Freelancer")
        self.window.context_changed()
        self.search("cafe", 2)
        row = self.window.list_box.get_first_child()
        self.assertEqual(row.note_id, note.id)
        self.assertIn(self.original.profile.name, row.get_tooltip_text())
        self.window.execute(lambda: self.org.activate_profile(other.id))
        self.assertEqual(self.window.search_entry.get_text(), "cafe")
        self.window.execute(lambda: self.org.activate_group(self.original.group.id))
        self.assertEqual(self.window.search_entry.get_text(), "")
        self.assertEqual(self.window.scope.get_selected(), 0)

    def test_rename_and_failed_switch_preserve_search(self) -> None:
        self.search("cafe", 2)
        self.window.execute(lambda: self.org.rename("profile", self.original.profile.id, "Pessoal"), affected_ids=set())
        self.assertEqual(self.window.search_entry.get_text(), "cafe")
        self.window.on_execute = Mock(side_effect=TransitionError("save failed"))
        with self.assertRaises(TransitionError):
            self.window.execute(lambda: self.org.create_group("Agenda"))
        self.assertEqual(self.window.search_entry.get_text(), "cafe")
        self.assertEqual(self.org.context.group.id, self.original.group.id)

    def controller(self) -> ContextController:
        def prepare(note):
            return NoteWindow(application=self.application, note=note, note_service=self.service,
                              on_closed=Mock(), on_changed=self.window.refresh)
        return ContextController(self.service, self.windows, prepare,
                                 on_context_changed=self.window.context_changed, on_refresh=self.window.refresh)

    def test_real_editor_pending_text_hidden_state_and_context_disposal(self) -> None:
        note = self.service.create_note()
        hidden = self.service.create_note()
        self.service.close_note(hidden.id, width=300, height=220)
        controller = self.controller()
        controller.restore()
        self.assertEqual(set(self.windows), {note.id})
        self.windows[note.id].text_view.get_buffer().set_text("pending text")
        other = controller.execute(lambda: self.org.create_group("Agenda"))
        self.assertEqual(self.windows, {})
        self.assertEqual(self.store.get(note.id).content, "pending text")
        self.assertTrue(self.store.get(note.id).is_open)
        controller.execute(lambda: self.org.activate_group(self.original.group.id))
        self.assertEqual(set(self.windows), {note.id})
        self.assertFalse(self.store.get(hidden.id).is_open)
        before = self.store.get(note.id).updated_at
        controller.execute(lambda: self.org.activate_group(other.id))
        self.assertEqual(self.store.get(note.id).updated_at, before)

    def test_real_editor_failed_autosave_retains_buffer_then_retries(self) -> None:
        note = self.service.create_note()
        controller = self.controller()
        controller.restore()
        editor = self.windows[note.id]
        editor.text_view.get_buffer().set_text("unsaved text")
        with patch.object(self.service, "update_content", side_effect=OSError("unavailable")):
            with self.assertRaises(TransitionError):
                controller.execute(lambda: self.org.create_group("Agenda"))
        self.assertIs(self.windows[note.id], editor)
        self.assertTrue(editor.autosave.has_pending_changes)
        self.assertEqual(self.org.context, self.original)
        controller.execute(lambda: self.org.create_group("Agenda"))
        self.assertEqual(self.store.get(note.id).content, "unsaved text")

    def test_editor_refresh_retains_note_action_focus_and_hidden_panel_reopens(self) -> None:
        note = self.service.create_note()
        self.window.refresh()
        self.window.present()
        while GLib.MainContext.default().pending():
            GLib.MainContext.default().iteration(False)
        menu = self.window.focus_targets[f"note-menu:{note.id}"]
        menu.grab_focus()
        self.service.update_content(note.id, "Changed by autosave")
        self.window.refresh()
        focused = self.window.get_focus()
        while focused is not None and not hasattr(focused, "focus_key"):
            focused = focused.get_parent()
        self.assertIs(focused, self.window.focus_targets[f"note-menu:{note.id}"])
        self.window.close()
        self.assertFalse(self.window.get_visible())
        self.assertFalse(self.window._disposed)
        self.window.present()
        self.assertTrue(self.window.get_visible())

    def test_editor_styles_are_local_and_menus_are_created_on_demand(self) -> None:
        from pinleaf.appearance import normalize_text_appearance
        first = self.service.create_note()
        second = self.service.create_note()
        controller = self.controller()
        controller.restore()
        one, two = self.windows[first.id], self.windows[second.id]
        one._set_text_appearance(normalize_text_appearance(font_family=None, font_size=20, text_color="#FF0000"))
        two._set_text_appearance(normalize_text_appearance(font_family=None, font_size=16, text_color="#0000FF"))
        while GLib.MainContext.default().pending():
            GLib.MainContext.default().iteration(False)
        self.assertEqual(one.text_view.get_style_context().get_color().to_string(), "rgb(255,0,0)")
        self.assertEqual(two.text_view.get_style_context().get_color().to_string(), "rgb(0,0,255)")
        self.window.refresh()
        menu = self.window.focus_targets[f"note-menu:{first.id}"]
        self.assertIsNone(menu.get_popover())
        self.window.present()
        menu.popup()
        self.assertIsNotNone(menu.get_popover())
        color_menu = one.color_dot.get_parent()
        while color_menu is not None and not isinstance(color_menu, Gtk.MenuButton):
            color_menu = color_menu.get_parent()
        self.assertIsNotNone(color_menu)
        self.assertIsNone(color_menu.get_popover())
        color_menu.popup()
        colors = color_menu.get_popover().get_child()
        green = colors.get_first_child().get_next_sibling()
        green.emit("clicked")
        self.assertEqual(self.store.get(first.id).color.value, "green")

    def test_activating_group_restores_focus_inside_its_header(self) -> None:
        other = self.org.create_group("Agenda")
        self.org.activate_group(self.original.group.id)
        self.window.refresh()
        self.window.present()
        while GLib.MainContext.default().pending():
            GLib.MainContext.default().iteration(False)
        self.assertTrue(self.window.focus_targets[f"activate:{other.id}"].grab_focus())
        self.window.execute(lambda: self.org.activate_group(other.id))
        focus = self.window.get_focus()
        while focus is not None and focus is not self.window.group_rows[other.id]:
            focus = focus.get_parent()
        self.assertIs(focus, self.window.group_rows[other.id])

    def test_delete_all_disposes_real_editor_without_late_storage_writes(self) -> None:
        group = self.org.create_group("Projeto")
        note = self.service.create_note()
        controller = self.controller()
        controller.restore()
        editor = self.windows[note.id]
        editor.text_view.get_buffer().set_text("pending before deletion")
        preview = self.org.preview_deletion("group", group.id)
        controller.execute(lambda: self.org.delete_container(preview, delete_notes=True), affected_ids={note.id})
        self.assertFalse(self.windows)
        before = tuple(self.store.connection.execute("SELECT * FROM notes WHERE id=?", (note.id,)).fetchone())
        while GLib.MainContext.default().pending():
            GLib.MainContext.default().iteration(False)
        after = tuple(self.store.connection.execute("SELECT * FROM notes WHERE id=?", (note.id,)).fetchone())
        self.assertEqual(before, after)
        self.assertEqual(after[1], "pending before deletion")
        self.assertIsNone(self.store.get(note.id))

    def test_global_breadcrumb_updates_after_inactive_profile_rename(self) -> None:
        note = self.service.create_note()
        self.service.update_content(note.id, "cafe")
        self.org.create_profile("Freelancer")
        self.search("cafe", 2)
        self.window.execute(lambda: self.org.rename("profile", self.original.profile.id, "Pessoal"), affected_ids=set())
        self.assertIn("Pessoal /", self.window.list_box.get_first_child().get_tooltip_text())

    def test_moving_real_editors_in_and_out_preserves_context_and_hidden_state(self) -> None:
        first = self.service.create_note()
        other_group = self.org.create_group("Other")
        second = self.service.create_note()
        hidden = self.service.create_note()
        self.service.close_note(hidden.id, width=300, height=220)
        self.org.activate_group(self.original.group.id)
        controller = self.controller()
        controller.restore()
        self.windows[first.id].text_view.get_buffer().set_text("moving draft")
        controller.execute(lambda: self.org.move_note(first.id, other_group.id), affected_ids={first.id})
        self.assertFalse(self.windows)
        self.assertEqual(self.store.get(first.id).content, "moving draft")
        self.assertTrue(self.store.get(first.id).is_open)
        controller.execute(lambda: self.org.move_note(second.id, self.original.group.id), affected_ids={second.id})
        controller.execute(lambda: self.org.move_note(hidden.id, self.original.group.id), affected_ids={hidden.id})
        self.assertEqual(set(self.windows), {second.id})
        self.assertEqual(self.org.context, self.original)
        self.assertFalse(self.store.get(hidden.id).is_open)
