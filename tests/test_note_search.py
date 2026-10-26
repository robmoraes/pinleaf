from __future__ import annotations

import unittest

from pinleaf.models import Note
from pinleaf.services.note_service import NoteService
from pinleaf.storage.sqlite_store import NoteStore


class NoteSearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = NoteStore(":memory:")
        self.service = NoteService(self.store)
        self.counter = 0

    def tearDown(self) -> None:
        self.store.close()

    def add_note(self, content: str) -> Note:
        self.counter += 1
        note = Note.new(
            f"note-{self.counter}",
            group_id=self.store.organization.shared(self.store.organization.context().profile.id).id,
            now=f"2026-06-12T{self.counter:02d}:00:00+00:00",
        )
        return self.store.create(note.with_content(content, now=note.created_at))

    def test_blank_query_returns_all_notes_in_creation_order(self) -> None:
        older = self.add_note("Comprar café")
        empty = self.add_note("")

        for query in ("", "   ", "\n\t"):
            with self.subTest(query=query):
                self.assertEqual(self.service.list_notes(query), [empty, older])
        self.assertEqual(self.service.list_notes(), [empty, older])

    def test_search_ignores_case_accents_and_unicode_composition(self) -> None:
        note = self.add_note("Comprar Café, AÇÃO e Straße")
        self.add_note("Comprar leite")

        for query in ("cafe", "CAFÉ", "cafe\u0301", "acao", "AÇÃo", "STRASSE"):
            with self.subTest(query=query):
                self.assertEqual(self.service.list_notes(query), [note])

    def test_search_matches_full_content_beyond_preview(self) -> None:
        note = self.add_note("Lembrete " * 30 + "dentista amanhã")

        self.assertEqual(self.service.list_notes("dentista"), [note])

    def test_search_normalizes_whitespace_and_matches_contiguous_phrases(self) -> None:
        note = self.add_note("Reunião\n\t amanhã    cedo")
        self.add_note("Reunião cancelada amanhã")

        self.assertEqual(self.service.list_notes("  REUNIAO amanhã  "), [note])
        self.assertEqual(self.service.list_notes("reunião\namanhã"), [note])
        self.assertEqual(self.service.list_notes("amanhã reunião"), [])

    def test_search_treats_punctuation_as_literal_text(self) -> None:
        percent = self.add_note("Desconto de 10%")
        underscore = self.add_note("arquivo_final.txt")
        brackets = self.add_note("[a-z].*")
        quote = self.add_note("D'água")
        self.add_note("Nota comum")

        cases = (("%", percent), ("_", underscore), ("[a-z].*", brackets), ("'", quote))
        for query, expected in cases:
            with self.subTest(query=query):
                self.assertEqual(self.service.list_notes(query), [expected])

    def test_search_includes_hidden_notes_and_excludes_deleted_notes(self) -> None:
        hidden = self.add_note("Café oculto")
        hidden = self.service.close_note(hidden.id, width=320, height=280)
        visible = self.add_note("Café aberto")
        deleted = self.add_note("Café excluído")
        self.service.delete_note(deleted.id)

        self.assertEqual(self.service.list_notes("cafe"), [visible, hidden])
        self.assertFalse(self.service.get_note(hidden.id).is_open)

    def test_search_keeps_creation_order_and_does_not_modify_notes(self) -> None:
        older = self.add_note("Café antigo")
        newer = self.add_note("Café novo")
        older = self.service.update_content(older.id, "Café antigo editado")
        before = self.service.list_notes()

        self.assertEqual(self.service.list_notes("cafe"), [newer, older])
        self.assertEqual(self.service.list_notes(), before)

    def test_search_reflects_saved_content_changes(self) -> None:
        note = self.add_note("Comprar café")
        self.assertEqual(self.service.list_notes("cafe"), [note])

        updated = self.service.update_content(note.id, "Comprar leite")

        self.assertEqual(self.service.list_notes("cafe"), [])
        self.assertEqual(self.service.list_notes("leite"), [updated])


if __name__ == "__main__":
    unittest.main()
