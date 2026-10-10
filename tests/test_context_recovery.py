from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from pinleaf.services.note_service import NoteService
from pinleaf.storage.sqlite_store import NoteStore


class ContextRecoveryTests(unittest.TestCase):
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

    def test_invalid_active_metadata_recovers_owners_general_and_preserves_notes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notes.sqlite3"
            store = NoteStore(path)
            service = NoteService(store)
            general = service.organization.context.group
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
            self.assertEqual(store.organization.context().group.id, general.id)
            self.assertEqual(tuple(store.connection.execute("SELECT * FROM notes").fetchone()), before)
            store.close()

    def test_broken_membership_or_missing_general_fails_without_recreating_library(self) -> None:
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
                        connection.execute("UPDATE groups SET is_general=0")
                with self.assertRaises(RuntimeError):
                    NoteStore(path)
                with sqlite3.connect(path) as connection:
                    self.assertEqual(connection.execute("SELECT COUNT(*) FROM profiles").fetchone()[0], 1)
                    self.assertEqual(connection.execute("SELECT COUNT(*) FROM notes").fetchone()[0], 1)
