# Plan: Note text search

## Spec Link

- `specs/010-note-text-search/spec.md`

## Approach

Add an optional query to the service's existing list operation. Filter in Python
with Unicode case folding, NFD accent removal and whitespace normalization;
SQLite's built-in case-insensitive matching does not cover these Unicode needs.
Keep storage's non-deleted selection and creation-time ordering.

Place a `Gtk.SearchEntry` above the main panel stack. Its `search-changed` signal
refreshes the list using the current query, so normal application refreshes
retain the filter. Add an `Adw.StatusPage` for no matches with a clear button,
and a window key controller for Ctrl+F. Use native stop-search for Escape.

## Files

- `pinleaf/services/note_service.py`: optional normalized content filtering.
- `pinleaf/ui/main_window.py`: field, shortcuts and result states.
- `tests/test_note_search.py`: content and lifecycle behavior with SQLite.
- `tests/test_main_window.py`: GTK search field, states, shortcuts and actions.
- `README.md` and `CHANGELOG.md`: usage and unreleased change.

## Validation

Run focused search tests, the full unittest suite, compileall and diff checks.
Exercise actual GTK widgets when a display is available; skip these GUI tests
on headless CI. Check layout with sample notes, filtered results and no results.
Record desktop-only verification still needed in tasks.md.

## Tradeoffs

Filtering is linear in the size of stored note text, matching the existing panel
strategy of loading all notes. Large libraries may eventually need indexing.
The current preview stays unchanged even when a match occurs later in a note.
