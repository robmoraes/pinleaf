from __future__ import annotations

import unittest
from datetime import timedelta, timezone
from unittest.mock import Mock

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, Gtk

from pinleaf.models import Note
from pinleaf.services.note_service import NoteService
from pinleaf.storage.sqlite_store import NoteStore
from pinleaf.ui.main_window import MainWindow, _format_timestamp, _preview


class MainWindowPreviewTests(unittest.TestCase):
    def test_preview_ignores_layout_whitespace(self) -> None:
        note = Note.new("note-1", group_id="fixture-group", now="2026-06-12T00:00:00+00:00").with_content(
            "\n\n        Comprar cafe\n        e leite\n\n",
            now="2026-06-12T01:00:00+00:00",
        )

        self.assertEqual(_preview(note), "Comprar cafe e leite")

    def test_preview_handles_empty_note(self) -> None:
        note = Note.new("note-1", group_id="fixture-group", now="2026-06-12T00:00:00+00:00").with_content(
            "\n    \n",
            now="2026-06-12T01:00:00+00:00",
        )

        self.assertEqual(_preview(note), "Empty note")

    def test_format_timestamp_converts_utc_to_local_timezone(self) -> None:
        local_tz = timezone(timedelta(hours=-3))

        self.assertEqual(
            _format_timestamp("2026-06-12T12:30:00+00:00", local_tz=local_tz),
            "Jun 12, 2026 9:30 AM UTC-03:00",
        )

    def test_format_timestamp_returns_invalid_value_unchanged(self) -> None:
        self.assertEqual(_format_timestamp("not-a-timestamp"), "not-a-timestamp")


class MainWindowSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not Gtk.init_check() or Gdk.Display.get_default() is None:
            raise unittest.SkipTest("GTK display required for panel search tests")
        Adw.init()
        cls.application = Adw.Application(
            application_id="dev.pinleaf.SearchTests",
            flags=Gio.ApplicationFlags.NON_UNIQUE,
        )
        cls.application.register(None)

    def setUp(self) -> None:
        self.store = NoteStore(":memory:")
        self.service = NoteService(self.store)
        self.on_open = Mock()
        self.window = MainWindow(
            application=self.application,
            note_service=self.service,
            on_create_note=Mock(),
            on_open_note=self.on_open,
            on_delete_note=Mock(),
        )
        self.window.refresh()

    def tearDown(self) -> None:
        self.window.search_entry.set_text("")
        self.window.destroy()
        self.store.close()

    def search(self, query: str) -> None:
        self.window.search_entry.set_text(query)
        self.window.search_entry.emit("search-changed")

    def test_search_signal_filters_rows_and_keeps_open_action(self) -> None:
        match = self.service.create_note()
        self.service.update_content(match.id, "Comprar café")
        other = self.service.create_note()
        self.service.update_content(other.id, "Comprar leite")

        self.search("CAFE")

        row = self.window.list_box.get_first_child()
        self.assertEqual(row.note_id, match.id)
        self.assertIsNone(row.get_next_sibling())
        self.assertEqual(self.window.stack.get_visible_child_name(), "list")
        self.window.list_box.emit("row-activated", row)
        self.on_open.assert_called_once_with(match.id)

    def test_refresh_preserves_query_and_updates_results_after_edit_and_delete(self) -> None:
        note = self.service.create_note()
        self.service.update_content(note.id, "Café")
        self.search("cafe")

        self.service.update_content(note.id, "Leite")
        self.window.refresh()
        self.assertEqual(self.window.search_entry.get_text(), "cafe")
        self.assertEqual(self.window.stack.get_visible_child_name(), "no-results")

        self.service.update_content(note.id, "Café novamente")
        self.window.refresh()
        self.assertEqual(self.window.stack.get_visible_child_name(), "list")

        self.service.delete_note(note.id)
        self.window.refresh()
        self.assertIsNone(self.window.list_box.get_first_child())
        self.assertEqual(self.window.stack.get_visible_child_name(), "no-results")

    def test_no_results_clear_button_restores_list(self) -> None:
        self.service.create_note()
        self.search("missing")
        self.assertEqual(self.window.stack.get_visible_child_name(), "no-results")

        status = self.window.stack.get_child_by_name("no-results")
        status.get_child().emit("clicked")
        self.window.search_entry.emit("search-changed")

        self.assertEqual(self.window.search_entry.get_text(), "")
        self.assertEqual(self.window.stack.get_visible_child_name(), "list")

    def test_stop_search_restores_empty_general_group(self) -> None:
        self.assertEqual(self.window.stack.get_visible_child_name(), "list")
        self.search("missing")
        self.assertEqual(self.window.stack.get_visible_child_name(), "no-results")

        self.window.search_entry.emit("stop-search")
        self.window.search_entry.emit("search-changed")

        self.assertEqual(self.window.search_entry.get_text(), "")
        self.assertEqual(self.window.stack.get_visible_child_name(), "list")
        self.assertTrue(self.window.group_rows[self.service.organization.context.group.id].get_expanded())

    def test_ctrl_f_selects_query_without_consuming_other_keys(self) -> None:
        self.search("cafe")
        controllers = self.window.observe_controllers()
        controller = next(
            controllers.get_item(index)
            for index in range(controllers.get_n_items())
            if isinstance(controllers.get_item(index), Gtk.EventControllerKey)
        )

        handled = controller.emit("key-pressed", Gdk.KEY_f, 0, Gdk.ModifierType.CONTROL_MASK)

        self.assertTrue(handled)
        self.assertEqual(self.window.search_entry.get_selection_bounds(), (0, 4))
        self.assertFalse(controller.emit("key-pressed", Gdk.KEY_f, 0, Gdk.ModifierType(0)))


if __name__ == "__main__":
    unittest.main()
