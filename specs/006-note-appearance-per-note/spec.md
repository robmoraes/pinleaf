# Feature: Per-note appearance settings

## Intent

Problem:
Pinleaf currently has global visual styling for note text. Different notes may
benefit from different font choices or text sizes, especially when notes serve
different purposes such as reminders, drafts or visual labels.

Users or stakeholders:
Maintainer and early users who want notes to feel more personal and easier to
scan.

Desired outcome:
Each note can store its own appearance settings, starting with font family, and
Pinleaf restores those settings whenever the note opens.

Non-goals:
- Rich text editing.
- Per-word or per-selection formatting.
- Markdown rendering.
- Remote font downloads.
- Theme editor for the whole application.

## Scope

In scope:
- Persist a per-note font family.
- Provide a compact UI to choose among bundled or available font families.
- Apply the selected font to the note editor.
- Preserve current global CSS defaults as fallback.
- Keep bundled font documentation current.

Out of scope:
- Arbitrary font file import from the UI.
- Per-note custom CSS.
- Font sync across machines.
- Text formatting toolbar.

Assumptions:
- Bundled fonts remain under `pinleaf/resources/fonts`.
- CSS continues to define default note styling.
- The first version may expose only curated font choices rather than every
  system font.

Dependencies:
- Existing bundled font loader.
- Existing note window controls.
- Existing storage model and migration mechanism.

## Behavior

1. Each note can store a selected font family.
2. New notes use the current global default font.
3. The note window exposes a native control to choose a font family.
4. Changing the font applies immediately to the note editor.
5. Changing the font saves the preference.
6. Reopening Pinleaf restores the selected font for each note.
7. If a stored font is unavailable, Pinleaf falls back to the global default.

## Acceptance Examples

Scenario: choose font for one note
Given a note is open
When the user selects a different font family
Then the note editor uses that font
And the setting is saved for that note.

Scenario: independent note appearance
Given two notes are open
When the user changes the font on one note
Then the other note keeps its own font.

Scenario: unavailable stored font
Given a note references a font that is no longer available
When the note opens
Then Pinleaf uses the default note font
And the note remains editable.

## Data and Contracts

Inputs:
- User font selection.
- Curated font family list.
- Existing note id.

Outputs:
- Persisted font family per note.

API/schema/event changes:
- SQLite schema may gain a nullable font family column.

Persistence changes:
- Existing notes migrate with no explicit font family.

## Quality Attributes

Security:
- No remote font loading.

Privacy:
- Appearance settings remain local.

Accessibility:
- Font selection should not make text unreadable by default.
- Future text size support should consider minimum readable sizes.

Reliability:
- Missing fonts must fall back cleanly.

Observability:
- None required.

## Rollout and Operations

Migration:
- Add schema migration for appearance settings.

Feature flag or configuration:
- None.

Rollback:
- Ignore per-note appearance fields and use global CSS defaults.

Monitoring:
- None.

