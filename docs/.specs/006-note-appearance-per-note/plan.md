# Plan: Per-note appearance settings

## Spec Link

- Source spec: `docs/.specs/006-note-appearance-per-note/spec.md`

## Approach

Add a per-note font family preference, limited to a curated set of bundled fonts
for the first implementation.

Use the existing global `.note-editor` CSS as the default fallback. Notes with no
explicit `font_family` continue to render exactly as they do today.

The implementation should avoid arbitrary font names from user input. Persist a
known font id or family value, validate it through a small appearance/font
catalog, and fall back cleanly when an old value is missing or unsupported.

## Font Catalog

Create a small code-level catalog for fonts exposed by the UI.

Initial candidates:

- Default: use current CSS default.
- `Dancing Script`
- `Cedarville Cursive`
- `League Script`
- `Tangerine`
- `Updock`

The catalog should provide:

- stable value for persistence;
- display label for UI;
- CSS/font family value to apply to the note editor.

## Data Model

Expected schema change:

- Increment SQLite schema version.
- Add nullable `font_family TEXT` to `notes`.
- Existing notes migrate with `NULL`, meaning "use default".

Expected model/service changes:

- Add `font_family: str | None` to `Note`.
- Include the field in SQLite insert/read conversion.
- Add store/service method to update note font family.
- Validate stored values against the font catalog before applying them.

## UI

Add a compact control to the note window header.

Recommended first implementation:

- Use a `Gtk.MenuButton` or `Gtk.DropDown` near the color control.
- Include a default option.
- Apply selected font immediately to the `Gtk.TextView`.
- Persist the selection immediately.
- Keep the existing color control behavior unchanged.

The control should be understandable without turning the header into a toolbar.

## Styling

Prefer applying a per-note CSS class to the editor rather than writing inline CSS
strings dynamically.

Example direction:

```text
note-font-dancing-script
note-font-cedarville-cursive
```

Only one font class should be active on a note editor at a time. The default
case should remove explicit font classes and let `.note-editor` handle fallback.

## Files

Expected code areas:

- `pinleaf/models.py`: add optional font family field.
- `pinleaf/fonts.py` or new `pinleaf/appearance.py`: expose curated font
  choices and validation helpers.
- `pinleaf/storage/migrations.py`: add migration path for schema version 2.
- `pinleaf/storage/sqlite_store.py`: persist and load the field.
- `pinleaf/services/note_service.py`: expose update method.
- `pinleaf/ui/note_window.py`: add font selector and apply classes.
- `pinleaf/resources/styles.css`: add font classes.
- `tests/`: cover catalog validation, migration, store and service behavior.

Expected documentation areas:

- `pinleaf/resources/fonts/README.md`: update only if the exposed font list or
  font instructions change.
- `docs/.specs/006-note-appearance-per-note/tasks.md`: record manual UI
  validation.

## Validation

Automated:

- run unit tests;
- run Python compile checks;
- test schema migration from version 1 to version 2;
- test new notes default to no explicit font;
- test font update persists and reloads;
- test invalid/unavailable font values fall back to default behavior.

Manual:

- open two notes;
- select different fonts for each note;
- verify each note changes immediately;
- restart Pinleaf;
- verify each note restores its own font;
- verify default option returns a note to global CSS default.

## Risks

- Some font family names may differ from file names; validate actual rendered
  names through manual GTK testing.
- Too many header controls can make the note top bar feel crowded.
- CSS class names and persisted values must remain stable once released.

