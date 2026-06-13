# Feature: Note header auto-hide

## Intent

Problem:
Pinleaf note windows currently show their top control bar all the time. This
makes notes feel more like regular app windows and less like desktop post-its.

Users or stakeholders:
Maintainer and early users who want notes to be visually quieter when they are
not being edited.

Desired outcome:
Each note hides its top control content when the note window is not focused, and
shows it again when the note regains focus. The header area keeps its height so
note text does not jump when focus changes.

Non-goals:
- Removing note controls permanently.
- Custom window decorations.
- Hover-triggered controls.
- Changing main panel behavior.

## Scope

In scope:
- Hide note header controls when the note window loses focus.
- Hide native note title and title buttons when the note window loses focus.
- Show note header controls when the note window gains focus.
- Preserve header height while controls are hidden.
- Preserve existing color and font controls.
- Preserve existing note editing and persistence behavior.

Out of scope:
- User preference for this behavior.
- Animation.
- Header reveal on pointer hover.
- Full custom titlebar/window controls.

## Behavior

1. A focused note shows its header controls.
2. An unfocused note hides its header controls while preserving header height.
3. Clicking/focusing the note shows the controls again.
4. Existing content, color, font and geometry behavior remains unchanged.
5. Unsupported or unusual focus behavior must not crash the app.

## Acceptance Examples

Scenario: note loses focus
Given a note is focused
When the user focuses another window
Then the note header is hidden.

Scenario: note gains focus
Given a note header is hidden because the note is unfocused
When the user focuses that note
Then the note header is shown again.

## Data and Contracts

Inputs:
- GTK window focus/active state notifications.

Outputs:
- Header visibility state.

Persistence changes:
- None.

## Quality Attributes

Accessibility:
- Controls remain available when the note is focused.

Reliability:
- Focus changes must not affect autosave or note state.

## Rollout and Operations

Migration:
- None.

Rollback:
- Keep note header always visible.
