from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock, patch

from pinleaf.models import SearchScope
from pinleaf.organization import OrganizationError
from pinleaf.services.context_controller import ContextController, TransitionError
from pinleaf.services.note_service import NoteService
from pinleaf.storage.sqlite_store import NoteStore
from test_context_controller import FakeEditor


class SharedBehaviorTests(unittest.TestCase):
    def setUp(self):
        self.store = NoteStore(":memory:")
        self.notes = NoteService(self.store)
        self.org = self.notes.organization
        self.initial = self.org.context
        self.shared = self.org.repository.shared(self.initial.profile.id)

    def tearDown(self):
        self.store.close()

    def test_fresh_profile_creation_fallback_and_shared_protection(self):
        self.assertIsNone(self.initial.group)
        self.assertEqual(self.org.list_groups(), [self.shared])
        self.assertEqual(self.notes.create_note().group_id, self.shared.id)
        for command in (lambda: self.org.activate_group(self.shared.id),
                        lambda: self.org.rename("group", self.shared.id, "Other"),
                        lambda: self.org.preview_deletion("group", self.shared.id)):
            with self.assertRaises(OrganizationError):
                command()
        for name in ("Shared", " COMPARTILHADO "):
            with self.assertRaises(OrganizationError):
                self.org.create_group(name)
        self.org.create_group("General")
        self.org.create_group("Geral")
        profile = self.org.create_profile("Freelancer")
        self.assertIsNone(self.org.context.group)
        self.assertEqual(self.notes.create_note().group_id, self.org.repository.shared(profile.id).id)

    def test_direct_shared_creation_and_opening_preserve_ordinary_context(self):
        project = self.org.create_group("Kubernetes")
        shared = self.notes.create_note(shared=True)
        ordinary = self.notes.create_note()
        self.assertEqual(shared.group_id, self.shared.id)
        self.assertEqual(ordinary.group_id, project.id)
        self.notes.close_note(shared.id, width=300, height=200)
        self.org.activate_and_open(shared.id)
        self.assertEqual(self.org.context.group, project)
        self.assertTrue(self.store.get(shared.id).is_open)

    def test_context_search_union_hidden_deleted_and_other_groups(self):
        shared = self.notes.create_note()
        self.notes.update_content(shared.id, "Café AWS tags")
        hidden = self.notes.create_note()
        self.notes.update_content(hidden.id, "café hidden")
        self.notes.close_note(hidden.id, width=300, height=200)
        deleted = self.notes.create_note()
        self.notes.update_content(deleted.id, "café deleted")
        self.notes.delete_note(deleted.id)
        project = self.org.create_group("Kubernetes")
        note = self.notes.create_note()
        self.notes.update_content(note.id, "CAFÉ course")
        self.org.create_group("Docker Swarm")
        other = self.notes.create_note()
        self.notes.update_content(other.id, "café channel")
        self.org.activate_group(project.id)
        self.assertEqual({n.id for n in self.notes.list_notes("cafe")}, {shared.id, hidden.id, note.id})
        self.assertEqual(len(self.notes.list_notes("cafe", scope=SearchScope.CURRENT_PROFILE)), 4)
        self.org.create_profile("Freelancer")
        self.assertEqual(self.notes.list_notes("cafe"), [])
        self.assertEqual(len(self.notes.list_notes("cafe", scope=SearchScope.ALL_PROFILES)), 4)

    def test_foreign_shared_open_restores_owners_last_ordinary_or_null(self):
        shared = self.notes.create_note()
        project = self.org.create_group("Kubernetes")
        foreign = self.org.create_profile("Freelancer")
        foreign_shared = self.notes.create_note()
        self.org.activate_and_open(shared.id)
        self.assertEqual(self.org.context.identity, (self.initial.profile.id, project.id))
        self.org.activate_and_open(foreign_shared.id)
        self.assertEqual(self.org.context.identity, (foreign.id, None))

    def test_delete_active_group_keeps_shared_and_does_not_select_other_project(self):
        shared = self.notes.create_note()
        self.org.create_group("Unrelated")
        project = self.org.create_group("Kubernetes")
        note = self.notes.create_note()
        self.org.delete_container(self.org.preview_deletion("group", project.id), destination_group_id=self.shared.id)
        self.assertEqual(self.org.context.identity, self.initial.identity)
        self.assertEqual({n.id for n in self.notes.list_notes()}, {shared.id, note.id})

    def test_delete_active_shared_only_profile_transfers_and_restores_destination_context(self):
        project = self.org.create_group("Kubernetes")
        source = self.org.create_profile("Freelancer")
        note = self.notes.create_note()
        self.org.delete_container(self.org.preview_deletion("profile", source.id), destination_group_id=self.shared.id)
        self.assertEqual(self.org.context.identity, (self.initial.profile.id, project.id))
        self.assertEqual(self.store.get(note.id).group_id, self.shared.id)

    def test_delete_shared_only_profile_all_and_empty_require_replacement(self):
        for populated in (False, True):
            source = self.org.create_profile("Freelancer")
            if populated:
                self.notes.create_note()
            preview = self.org.preview_deletion("profile", source.id)
            with self.assertRaises(OrganizationError):
                self.org.delete_container(preview, delete_notes=True)
            self.org.delete_container(preview, delete_notes=True, replacement_profile_id=self.initial.profile.id,
                                      replacement_identity=(self.initial.profile.id, self.initial.profile.name, None, None))
            self.assertEqual(self.org.context.identity, self.initial.identity)

    def test_nullable_context_persists_without_reseed_and_rejects_foreign_membership(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notes.sqlite3"
            store = NoteStore(path)
            org = NoteService(store).organization
            first = org.context.profile
            group = org.create_group("Kubernetes")
            other = org.create_profile("Freelancer")
            with self.assertRaises(OrganizationError):
                org.repository.set_context(other.id, group.id)
            before = store.connection.total_changes
            org.activate_profile(other.id)
            self.assertEqual(store.connection.total_changes, before)
            store.close()
            store = NoteStore(path)
            self.assertEqual(store.organization.context().identity, (other.id, None))
            self.assertFalse(store.context_recovered)
            self.assertEqual(store.organization.last_group(first.id).id, group.id)
            self.assertEqual(len(store.organization.list_groups(other.id)), 1)
            store.close()


class SharedDesktopTests(unittest.TestCase):
    def setUp(self):
        self.store = NoteStore(":memory:")
        self.notes = NoteService(self.store)
        self.org = self.notes.organization
        self.initial = self.org.context
        self.shared = self.org.repository.shared(self.initial.profile.id)
        self.addCleanup(self.store.close)
        self.shared_note = self.notes.create_note()
        self.first = self.org.create_group("Kubernetes")
        self.first_note = self.notes.create_note()
        self.second = self.org.create_group("Docker Swarm")
        self.second_note = self.notes.create_note()
        self.hidden = self.notes.create_note(shared=True)
        self.notes.close_note(self.hidden.id, width=300, height=200)
        self.org.activate_group(self.first.id)
        self.windows = {}
        self.changed = Mock()
        self.controller = ContextController(self.notes, self.windows, lambda n: FakeEditor(n, self.notes),
                                            on_context_changed=self.changed)
        self.controller.restore()

    def test_shared_editor_survives_group_switch_without_focus_or_disposal(self):
        editor = self.windows[self.shared_note.id]
        editor.presented = editor.shown = False
        before = self.store.get(self.shared_note.id)
        self.controller.execute(lambda: self.org.activate_group(self.second.id))
        self.assertIs(self.windows[self.shared_note.id], editor)
        self.assertFalse(editor.presented or editor.shown or editor.disposed)
        self.assertEqual(set(self.windows), {self.shared_note.id, self.second_note.id})
        self.assertEqual(self.store.get(self.shared_note.id), before)
        self.assertFalse(self.store.get(self.hidden.id).is_open)

    def test_profile_switch_disposes_shared_without_hiding_and_null_profiles_trigger_change(self):
        editor = self.windows[self.shared_note.id]
        foreign = self.controller.execute(lambda: self.org.create_profile("Freelancer"))
        self.assertTrue(editor.disposed)
        self.assertTrue(self.store.get(self.shared_note.id).is_open)
        self.assertEqual(self.windows, {})
        self.changed.reset_mock()
        self.controller.execute(lambda: self.org.create_profile("Another"))
        self.changed.assert_called_once()
        self.controller.execute(lambda: self.org.activate_profile(self.initial.profile.id))
        self.assertEqual(set(self.windows), {self.shared_note.id, self.first_note.id})

    def test_move_into_shared_reuses_window_and_moving_out_reconciles_visibility(self):
        editor = self.windows[self.first_note.id]
        before = self.store.get(self.first_note.id)
        self.controller.execute(lambda: self.org.move_note(self.first_note.id, self.shared.id), affected_ids={self.first_note.id})
        self.assertIs(self.windows[self.first_note.id], editor)
        self.assertEqual(self.store.get(self.first_note.id), replace(before, group_id=self.shared.id))
        self.controller.execute(lambda: self.org.move_note(self.first_note.id, self.second.id), affected_ids={self.first_note.id})
        self.assertNotIn(self.first_note.id, self.windows)
        self.assertTrue(editor.disposed)
        self.assertTrue(self.store.get(self.first_note.id).is_open)
        self.controller.execute(lambda: self.org.move_note(self.second_note.id, self.shared.id), affected_ids=set())
        self.assertIn(self.second_note.id, self.windows)

    def test_failed_save_retains_shared_draft_and_context(self):
        editor = self.windows[self.shared_note.id]
        editor.pending, editor.fail_save = "unsaved shared draft", True
        with self.assertRaises(TransitionError):
            self.controller.execute(lambda: self.org.activate_group(self.second.id))
        self.assertIs(self.windows[self.shared_note.id], editor)
        self.assertEqual(editor.pending, "unsaved shared draft")
        self.assertEqual(self.org.context.group_id, self.first.id)
        editor.fail_save = False
        self.controller.execute(lambda: self.org.activate_group(self.second.id))
        self.assertEqual(self.store.get(self.shared_note.id).content, "unsaved shared draft")

    def test_deleting_active_group_preserves_shared_editor_and_null_context(self):
        editor = self.windows[self.shared_note.id]
        preview = self.org.preview_deletion("group", self.first.id)
        self.controller.execute(lambda: self.org.delete_container(preview, delete_notes=True), affected_ids={self.first_note.id})
        self.assertIs(self.windows[self.shared_note.id], editor)
        self.assertEqual(set(self.windows), {self.shared_note.id})
        self.assertIsNone(self.org.context.group)

    def test_failed_prepare_rolls_back_with_shared_editor_untouched(self):
        shared_editor = self.windows[self.shared_note.id]
        previous = dict(self.windows)
        with patch.object(self.controller, "prepare", side_effect=RuntimeError("prepare failed")):
            with self.assertRaises(RuntimeError):
                self.controller.execute(lambda: self.org.activate_group(self.second.id))
        self.assertEqual(self.windows, previous)
        self.assertIs(self.windows[self.shared_note.id], shared_editor)
        self.assertFalse(shared_editor.disposed)
        self.assertEqual(self.org.context.group_id, self.first.id)

    def test_explicit_foreign_shared_open_focuses_requested_note_after_batch_restore(self):
        self.controller.execute(lambda: self.org.create_profile("Freelancer"))
        self.assertEqual(self.windows, {})
        self.controller.execute(lambda: self.org.activate_and_open(self.shared_note.id), focus_note_id=self.shared_note.id)
        self.assertTrue(self.windows[self.shared_note.id].presented)
        self.assertTrue(self.windows[self.first_note.id].shown)
        self.assertFalse(self.windows[self.first_note.id].presented)
