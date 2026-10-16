# Feature: Note text search

## Intent

Let users find existing sticky notes by their text from the main panel.

## Scope

- A visible search field above the note list, filtering as the user types.
- Literal substring matching against the full content of all non-deleted notes,
  including hidden notes and text beyond the list preview.
- Ignore case and accents; treat consecutive whitespace and line breaks as a
  single space and trim leading/trailing query whitespace.
- Keep the existing creation-time ordering and row actions.
- Keep the query active when autosave, note visibility or deletion refreshes the
  panel. Searching does not open, hide or modify notes.
- Ctrl+F focuses and selects the search text. Escape in the search field, its
  clear icon and a no-results clear button reset the filter.
- Show a dedicated no-results state for a nonblank query with no matches.
- An empty query restores the normal list or existing empty-library state.

Out of scope: regular expressions, relevance ranking, in-note navigation or
highlighting, persisted search history, network services and schema changes.

## Acceptance Examples

1. Searching `cafe` finds an open note containing `Comprar Café` and a hidden
   note containing `CAFÉ`, including when the match is beyond the preview.
2. Searching `reunião amanhã` finds `Reunião\namanhã` as a contiguous phrase.
3. Searching `%` or `_` matches those literal characters only.
4. A deleted note never appears in results.
5. Editing a matching note so it no longer matches removes it after autosave;
   the search field retains its text.
6. A query with no matches shows `No matching notes`; clearing it restores all
   notes. An empty library with an empty query shows `No notes yet`.
7. Activating a matching row opens that note through the existing action.

## Data and Contracts

`NoteService.list_notes(query: str = "")` preserves its existing no-argument
behavior. Matching uses a normalized copy of query/content without changing
stored text, metadata, window state or the SQLite schema.

## Quality Attributes

The search uses native GTK controls and remains keyboard accessible. Filtering
runs locally over the notes already loaded for the panel, using GTK's search
signal delay to avoid rebuilding the list for every keystroke.

## Rollout

Prepared for version 0.8.0, with release notes and site documentation updated.
Available from source until the release is published.
