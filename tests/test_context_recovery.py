from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from pinleaf.services.note_service import NoteService
from pinleaf.storage.sqlite_store import NoteStore


class ContextRecoveryTests(unittest.TestCase):
    def test_shared_active_reference_and_missing_profile_recover_without_selecting_unrelated_group(self) -> None:
        for corruption in ("shared", "missing-profile"):
            with self.subTest(corruption=corruption), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "notes.sqlite3"
                store = NoteStore(path)
                service = NoteService(store)
                org = service.organization
                first = org.context.profile
                note = service.create_note()
                group = org.create_group("Kubernetes")
                other = org.create_profile("Freelancer")
                org.activate_profile(first.id)
                shared = org.repository.shared(first.id)
                expected_profile = min(first.id, other.id)
                expected_group = group.id if expected_profile == first.id else None
                store.close()
                with sqlite3.connect(path) as connection:
                    before = tuple(connection.execute("SELECT * FROM notes").fetchone())
                    if corruption == "shared":
                        connection.execute("UPDATE active_context SET group_id=?", (shared.id,))
                    else:
                        connection.execute("UPDATE active_context SET profile_id='missing',group_id=NULL")
                store = NoteStore(path)
                self.assertTrue(store.context_recovered)
                expected = (first.id, None) if corruption == "shared" else (expected_profile, expected_group)
                self.assertEqual(store.organization.context().identity, expected)
                self.assertEqual(tuple(store.connection.execute("SELECT * FROM notes").fetchone()), before)
                self.assertEqual(len(store.organization.list_groups()), 3)
                store.close()

    def test_restart_restores_active_and_per_profile_last_groups_without_reseeding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notes.sqlite3"
            store = NoteStore(path)
            org = NoteService(store).organization
            initial = org.context
            first = org.create_group("LGPD")
            org.create_profile("Freelancer")
            last = org.create_group("DevOps")
            store.close()
            store = NoteStore(path)
            org = NoteService(store).organization
            self.assertEqual(org.context.group.id, last.id)
            org.activate_profile(initial.profile.id)
            self.assertEqual(org.context.group.id, first.id)
            self.assertFalse(store.context_recovered)
            self.assertEqual(len(org.list_profiles()), 2)
            store.close()

    def test_invalid_active_metadata_recovers_owners_shared_only_and_preserves_notes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notes.sqlite3"
            store = NoteStore(path)
            service = NoteService(store)
            shared = service.organization.repository.shared(service.organization.context.profile.id)
            group = service.organization.create_group("LGPD")
            note = service.create_note()
            service.delete_note(note.id)
            service.organization.delete_container(service.organization.preview_deletion("group", group.id))
            # Simulate stale metadata from an interrupted external writer.
            store.connection.execute("UPDATE active_context SET group_id=?", (group.id,))
            store.connection.execute("UPDATE profile_context SET last_group_id=?", (group.id,))
            store.connection.commit()
            before = tuple(store.connection.execute("SELECT * FROM notes").fetchone())
            store.close()
            store = NoteStore(path)
            self.assertTrue(store.context_recovered)
            self.assertIsNone(store.organization.context().group)
            self.assertEqual(tuple(store.connection.execute("SELECT * FROM notes").fetchone()), before)
            store.close()

    def test_broken_membership_or_missing_shared_fails_without_recreating_library(self) -> None:
        for corruption in ("membership", "general"):
            with self.subTest(corruption=corruption), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "notes.sqlite3"
                store = NoteStore(path)
                service = NoteService(store)
                service.create_note()
                store.close()
                with sqlite3.connect(path) as connection:
                    if corruption == "membership":
                        connection.execute("UPDATE notes SET group_id='missing'")
                    else:
                        connection.execute("UPDATE groups SET is_shared=0")
                with self.assertRaises(RuntimeError):
                    NoteStore(path)
                with sqlite3.connect(path) as connection:
                    self.assertEqual(connection.execute("SELECT COUNT(*) FROM profiles").fetchone()[0], 1)
                    self.assertEqual(connection.execute("SELECT COUNT(*) FROM notes").fetchone()[0], 1)
