from __future__ import annotations

import sqlite3
import unittest
from unittest.mock import Mock, patch

from pinleaf.services.context_controller import ContextController, TransitionError
from pinleaf.services.note_service import NoteService
from pinleaf.storage.sqlite_store import NoteStore


class FakeEditor:
    def __init__(self, note, service):
        self.note = note
        self.service = service
        self.pending = None
        self.fail_save = False
        self.disposed = False
        self.presented = False
        self.shown = False

    def flush_for_transition(self):
        if self.fail_save:
            return False
        if self.pending is not None:
            self.note = self.service.update_content(self.note.id, self.pending)
            self.pending = None
        return True

    def capture_state(self):
        return dict(width=self.note.width, height=self.note.height,
                    position_x=self.note.position_x, position_y=self.note.position_y)

    def dispose_for_context(self):
        self.disposed = True

    def sync_note(self, note):
        self.note = note

    def present(self):
        self.presented = True

    def show_for_context(self):
        self.shown = True


class ContextControllerTests(unittest.TestCase):
    def setUp(self):
        self.store = NoteStore(':memory:')
        self.service = NoteService(self.store)
        self.org = self.service.organization
        self.source = self.org.context.group
        self.first = self.service.create_note()
        self.target = self.org.create_group('LGPD')
        self.second = self.service.create_note()
        hidden = self.service.create_note()
        self.hidden = self.service.close_note(hidden.id, width=320, height=280)
        self.org.activate_group(self.source.id)
        self.editor = FakeEditor(self.first, self.service)
        self.windows = {self.first.id: self.editor}
        self.changed = Mock()
        self.controller = ContextController(self.service, self.windows, lambda note: FakeEditor(note, self.service),
                                            on_context_changed=self.changed)

    def tearDown(self):
        self.store.close()

    def test_cycle_preserves_open_hidden_state_and_timestamps(self):
        before = self.store.get(self.first.id)
        self.controller.execute(lambda: self.org.activate_group(self.target.id))
        self.assertEqual(set(self.windows), {self.second.id})
        self.assertTrue(self.editor.disposed)
        self.assertEqual(self.store.get(self.first.id), before)
        self.assertFalse(self.store.get(self.hidden.id).is_open)
        self.controller.execute(lambda: self.org.activate_group(self.source.id))
        self.assertEqual(set(self.windows), {self.first.id})

    def test_failed_flush_retains_pending_buffer_and_context(self):
        self.editor.pending = 'Pending draft'
        self.editor.fail_save = True
        with self.assertRaises(TransitionError):
            self.controller.execute(lambda: self.org.activate_group(self.target.id))
        self.assertEqual(self.editor.pending, 'Pending draft')
        self.assertEqual(self.org.context.group.id, self.source.id)
        self.assertFalse(self.editor.disposed)
        self.assertFalse(self.controller.busy)

    def test_failed_prepare_rolls_back_and_keeps_original_editor(self):
        with patch.object(self.controller, 'prepare', side_effect=RuntimeError('prepare failed')):
            with self.assertRaises(RuntimeError):
                self.controller.execute(lambda: self.org.activate_group(self.target.id))
        self.assertEqual(self.org.context.group.id, self.source.id)
        self.assertEqual(self.windows, {self.first.id: self.editor})
        self.assertFalse(self.editor.disposed)

    def test_commit_failure_discards_staged_editors_and_rolls_back(self):
        prepared = []
        def prepare(note):
            editor = FakeEditor(note, self.service)
            prepared.append(editor)
            return editor
        self.controller.prepare = prepare
        def command():
            self.org.activate_group(self.target.id)
            self.store.connection.execute('PRAGMA defer_foreign_keys=ON')
            self.store.connection.execute("UPDATE notes SET group_id='missing' WHERE id=?", (self.first.id,))
        with self.assertRaises(sqlite3.IntegrityError):
            self.controller.execute(command)
        self.assertTrue(prepared and all(editor.disposed for editor in prepared))
        self.assertEqual(self.org.context.group.id, self.source.id)
        self.assertEqual(self.store.get(self.first.id), self.first)
        self.assertFalse(self.editor.disposed)

    def test_geometry_failure_and_same_context_noop(self):
        with patch.object(self.store, 'save_context_geometry', side_effect=OSError('disk failure')):
            with self.assertRaises(OSError):
                self.controller.execute(lambda: self.org.activate_group(self.target.id))
        self.assertEqual(self.org.context.group.id, self.source.id)
        self.controller.execute(lambda: self.org.activate_group(self.source.id))
        self.changed.assert_not_called()

    def test_move_removes_window_without_hiding_note(self):
        self.controller.execute(lambda: self.org.move_note(self.first.id, self.target.id), affected_ids={self.first.id})
        self.assertEqual(self.windows, {})
        self.assertTrue(self.store.get(self.first.id).is_open)
        self.assertEqual(self.org.context.group.id, self.source.id)

    def test_postcommit_presentation_failure_keeps_committed_context(self):
        errors = Mock()
        self.controller.on_presentation_error = errors
        def prepare(note):
            editor = FakeEditor(note, self.service)
            editor.present = Mock(side_effect=RuntimeError('presentation failed'))
            return editor
        self.controller.prepare = prepare
        self.controller.execute(lambda: self.org.activate_group(self.target.id))
        self.assertEqual(self.org.context.group.id, self.target.id)
        self.assertIn(self.second.id, self.windows)
        errors.assert_called_once()

    def test_restoring_multiple_notes_shows_all_and_requests_focus_once(self):
        self.org.activate_group(self.target.id)
        third = self.service.create_note()
        self.org.activate_group(self.source.id)
        self.controller.execute(lambda: self.org.activate_group(self.target.id))
        self.assertEqual(set(self.windows), {self.second.id, third.id})
        self.assertTrue(all(editor.shown or editor.presented for editor in self.windows.values()))
        self.assertEqual(sum(editor.presented for editor in self.windows.values()), 1)
        self.assertFalse(self.store.get(self.hidden.id).is_open)

    def test_batch_mapping_failure_keeps_context_and_continues_presentation(self):
        self.org.activate_group(self.target.id)
        third = self.service.create_note()
        self.org.activate_group(self.source.id)
        errors = Mock()
        self.controller.on_presentation_error = errors
        def prepare(note):
            editor = FakeEditor(note, self.service)
            editor.show_for_context = Mock(side_effect=RuntimeError('mapping failed'))
            return editor
        self.controller.prepare = prepare
        self.controller.execute(lambda: self.org.activate_group(self.target.id))
        self.assertEqual(self.org.context.group.id, self.target.id)
        self.assertEqual(set(self.windows), {self.second.id, third.id})
        self.assertEqual(sum(editor.presented for editor in self.windows.values()), 1)
        errors.assert_called_once()
