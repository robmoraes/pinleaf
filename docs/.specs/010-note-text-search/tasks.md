# Tasks: Note text search

## Source

- Spec: `docs/.specs/010-note-text-search/spec.md`
- Plan: `docs/.specs/010-note-text-search/plan.md`

## Implementation Tasks

1. Add normalized literal content filtering in the note service.
2. Add live search, Ctrl+F, clearing and no-results UI to the main panel.
3. Cover content matching, order, hidden/deleted notes and refreshed results.
4. Verify native GTK search controls, result states and existing row actions.
5. Update usage documentation and unreleased changes.
6. Run unittest, compileall and diff checks; inspect the panel layout.

## Progress

- Tasks 1-6: completed.
- Automated checks passed:
  - `/usr/bin/python3 -m unittest discover -s tests`: 99 tests passed with a
    display, including five GTK panel tests and eight service search tests.
  - Headless unittest discovery: 94 tests passed; the GTK search test class
    was skipped because no display was available.
  - `/usr/bin/python3 -m compileall pinleaf tests` passed.
  - `git diff --check` passed.
- GTK 4.14 / libadwaita 1.5 smoke check passed using an in-memory database and
  native X11 keyboard events: delayed search signal, accent-insensitive matching,
  hidden-note results, Ctrl+F selection, Escape clearing and the no-results clear
  button all behaved as expected.
- Layout inspected with the full list, filtered results and no matches.
  Captures are available locally at `/tmp/pinleaf-search-all.png`,
  `/tmp/pinleaf-search-filtered.png` and `/tmp/pinleaf-search-no-results.png`.
- Result row activation and query retention across saved edits and deletion are
  covered by GTK tests. Content filtering and state preservation are covered by
  service tests against SQLite.
- GNOME/Wayland-specific focus behavior has not been manually verified in this
  change; the desktop smoke check used X11.
