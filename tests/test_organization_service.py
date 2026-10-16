from __future__ import annotations

import sqlite3
import unittest
from dataclasses import replace

from pinleaf.models import SearchScope
from pinleaf.organization import OrganizationError, ProtectedContainerError, StalePreviewError
from pinleaf.services.note_service import NoteService
from pinleaf.storage.sqlite_store import NoteStore


class OrganizationServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = NoteStore(':memory:')
        self.notes = NoteService(self.store)
        self.org = self.notes.organization
        self.initial = self.org.context
        self.shared = self.org.repository.shared(self.initial.profile.id)

    def tearDown(self) -> None:
        self.store.close()

    def test_create_rename_and_resume_last_group(self) -> None:
        group = self.org.create_group('LGPD')
        profile = self.org.create_profile('Freelancer')
        self.assertIsNone(self.org.context.group)
        self.org.activate_profile(self.initial.profile.id)
        self.assertEqual(self.org.context.group.id, group.id)
        self.org.rename('profile', profile.id, 'Trabalho')
        self.org.rename('group', group.id, 'Agenda')
        self.assertEqual(self.org.context.group.name, 'Agenda')

    def test_uniqueness_and_protection_are_service_rules(self) -> None:
        self.org.create_group('Café')
        for name in ('CAFE\u0301', 'Shared', 'compartilhado', ' ', 'G' * 81):
            with self.subTest(name=name), self.assertRaises(OrganizationError):
                self.org.create_group(name)
        with self.assertRaises(ProtectedContainerError):
            self.org.rename('group', self.shared.id, 'Other')
        with self.assertRaises(ProtectedContainerError):
            self.org.preview_deletion('group', self.shared.id)
        with self.assertRaises(ProtectedContainerError):
            self.org.preview_deletion('profile', self.initial.profile.id)

    def test_creation_and_scoped_search_do_not_mix_contexts(self) -> None:
        first = self.notes.create_note()
        self.notes.update_content(first.id, 'Café geral')
        group = self.org.create_group('LGPD')
        second = self.notes.create_note()
        self.notes.update_content(second.id, 'Café projeto')
        self.notes.close_note(second.id, width=320, height=280)
        self.assertEqual(second.group_id, group.id)
        self.assertEqual({n.id for n in self.notes.list_notes('cafe')}, {first.id, second.id})
        self.assertEqual({n.id for n in self.notes.list_notes('cafe', scope=SearchScope.CURRENT_PROFILE)}, {first.id, second.id})
        self.org.create_profile('Freelancer')
        self.assertEqual(self.notes.list_notes('cafe'), [])
        self.assertEqual(len(self.notes.list_notes('cafe', scope=SearchScope.ALL_PROFILES)), 2)

    def test_move_preserves_metadata_and_context(self) -> None:
        note = self.notes.create_note()
        destination = self.org.create_group('Destination')
        active = self.org.context
        before = self.store.get(note.id)
        self.org.move_note(note.id, destination.id)
        self.assertEqual(self.store.get(note.id), replace(before, group_id=destination.id))
        self.assertEqual(self.org.context, active)

    def test_group_transfer_includes_hidden_and_deleted_notes(self) -> None:
        source = self.org.create_group('Source')
        first = self.notes.create_note()
        hidden = self.notes.create_note()
        self.notes.close_note(hidden.id, width=320, height=280)
        deleted = self.notes.create_note()
        self.notes.delete_note(deleted.id)
        original = [tuple(row) for row in self.store.connection.execute('SELECT * FROM notes ORDER BY id')]
        preview = self.org.preview_deletion('group', source.id)
        self.assertEqual(preview.note_count, 2)
        self.org.delete_container(preview, destination_group_id=self.shared.id)
        self.assertIsNone(self.org.context.group)
        self.assertFalse(self.store.get(hidden.id).is_open)
        self.assertIsNone(self.store.get(deleted.id))
        after = [tuple(row) for row in self.store.connection.execute('SELECT * FROM notes ORDER BY id')]
        self.assertEqual([row[:-1] for row in original], [row[:-1] for row in after])
        self.assertEqual({row[-1] for row in after}, {self.shared.id})
        self.assertTrue(self.store.get(first.id).is_open)

    def test_profile_delete_all_repairs_context_and_preserves_other_notes(self) -> None:
        first = self.notes.create_note()
        self.org.create_group('LGPD')
        hidden = self.notes.create_note()
        self.notes.close_note(hidden.id, width=320, height=280)
        replacement = self.org.create_profile('Freelancer')
        other = self.notes.create_note()
        destination = self.org.create_group('DevOps')
        self.org.activate_profile(self.initial.profile.id)
        preview = self.org.preview_deletion('profile', self.initial.profile.id)
        self.org.delete_container(preview, delete_notes=True, replacement_profile_id=replacement.id)
        self.assertEqual(self.org.context.group.id, destination.id)
        self.assertEqual(self.org.list_profiles(), [replacement])
        self.assertIsNone(self.store.get(first.id))
        self.assertIsNone(self.store.get(hidden.id))
        self.assertEqual(self.store.get(other.id), other)

    def test_stale_preview_rejects_scope_changes_but_not_saved_text(self) -> None:
        group = self.org.create_group('LGPD')
        note = self.notes.create_note()
        preview = self.org.preview_deletion('group', group.id)
        self.notes.update_content(note.id, 'Edited after review')
        self.assertEqual(preview, self.org.preview_deletion('group', group.id))
        self.notes.create_note()
        with self.assertRaises(StalePreviewError):
            self.org.delete_container(preview, delete_notes=True)
        self.assertEqual(self.org.context.group.id, group.id)

    def test_internal_destination_and_failed_sql_leave_organization_intact(self) -> None:
        source = self.org.create_group('LGPD')
        note = self.notes.create_note()
        preview = self.org.preview_deletion('group', source.id)
        with self.assertRaises(OrganizationError):
            self.org.delete_container(preview, destination_group_id=source.id)
        self.store.connection.execute("""CREATE TEMP TRIGGER refuse_disposal BEFORE UPDATE OF deleted_at ON groups
            BEGIN SELECT RAISE(ABORT,'injected failure'); END""")
        with self.assertRaises(sqlite3.IntegrityError):
            self.org.delete_container(preview, destination_group_id=self.shared.id)
        self.assertEqual(self.store.get(note.id), note)
        self.assertEqual(self.org.context.group.id, source.id)

    def test_only_deleted_empty_container_needs_no_destination(self) -> None:
        source = self.org.create_group('LGPD')
        note = self.notes.create_note()
        self.notes.delete_note(note.id)
        preview = self.org.preview_deletion('group', source.id)
        self.org.delete_container(preview)
        row = self.store.connection.execute('SELECT group_id,deleted_at FROM notes WHERE id=?', (note.id,)).fetchone()
        self.assertEqual(row[0], source.id)
        self.assertIsNotNone(row[1])

    def test_outer_transaction_controls_all_nested_service_changes(self) -> None:
        before = self.org.context
        with self.assertRaises(RuntimeError):
            with self.store.transaction():
                self.org.create_group('Transient')
                self.notes.create_note()
                raise RuntimeError('abort')
        self.assertEqual(self.org.context, before)
        self.assertEqual(len(self.org.list_groups()), 1)
        self.assertEqual(self.store.list_notes(), [])

    def test_profile_transfer_flattens_groups_and_retained_tombstones(self) -> None:
        first = self.notes.create_note()
        removed_group = self.org.create_group('Old project')
        deleted = self.notes.create_note()
        self.notes.delete_note(deleted.id)
        self.org.delete_container(self.org.preview_deletion('group', removed_group.id))
        self.org.create_group('Current project')
        hidden = self.notes.create_note()
        self.notes.close_note(hidden.id, width=300, height=220)
        self.org.create_profile('Freelancer')
        destination = self.org.repository.shared(self.org.context.profile.id)
        before = [tuple(row)[:-1] for row in self.store.connection.execute('SELECT * FROM notes ORDER BY id')]
        preview = self.org.preview_deletion('profile', self.initial.profile.id)
        self.assertEqual(preview.note_count, 2)
        self.org.delete_container(preview, destination_group_id=destination.id)
        self.assertEqual([tuple(row)[:-1] for row in self.store.connection.execute('SELECT * FROM notes ORDER BY id')], before)
        self.assertEqual({row[0] for row in self.store.connection.execute('SELECT group_id FROM notes')}, {destination.id})
        self.assertIsNone(self.store.get(deleted.id))
        self.assertFalse(self.store.get(hidden.id).is_open)
        self.assertTrue(self.store.get(first.id).is_open)

    def test_same_context_is_a_noop_and_renamed_destination_requires_review(self) -> None:
        before = self.store.connection.total_changes
        self.org.activate_profile(self.initial.profile.id)
        self.assertEqual(self.store.connection.total_changes, before)
        destination = self.org.create_group('Destination')
        source = self.org.create_group('Source')
        self.notes.create_note()
        preview = self.org.preview_deletion('group', source.id)
        identity = (destination.profile_id, self.initial.profile.name, destination.id, destination.name)
        self.org.rename('group', destination.id, 'Changed destination')
        with self.assertRaises(StalePreviewError):
            self.org.delete_container(preview, destination_group_id=destination.id, destination_identity=identity)
        self.assertEqual(self.org.context.group.id, source.id)

    def test_successful_composite_operation_has_one_durable_commit(self) -> None:
        statements = []
        self.store.connection.set_trace_callback(statements.append)
        with self.store.transaction():
            self.org.create_profile('Freelancer')
            self.org.create_group('DevOps')
            self.notes.create_note()
        self.store.connection.set_trace_callback(None)
        self.assertEqual(sum(statement == 'COMMIT' for statement in statements), 1)
        self.assertEqual(self.org.context.group.name, 'DevOps')
